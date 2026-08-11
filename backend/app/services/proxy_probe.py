from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlsplit


@dataclass(frozen=True, slots=True)
class ProxyProbeResult:
    ok: bool
    youtube_ok: bool
    youtube_latency_ms: float | None
    download_mbps: float | None
    bytes_received: int
    error: str | None = None


def probe_proxy(source_uri: str, *, timeout_s: float = 8.0,
                test_url: str = "https://www.youtube.com/generate_204",
                connectivity_url: str = "https://www.gstatic.com/generate_204",
                speed_url: str = "https://speed.cloudflare.com/__down?bytes=1000000") -> ProxyProbeResult:
    binary = os.environ.get("SING_BOX_BIN", "sing-box")
    try:
        config = _build_config(source_uri)
    except ValueError as exc:
        return ProxyProbeResult(False, False, None, None, 0, str(exc))

    local_port = _free_port()
    config["inbounds"][0]["listen_port"] = local_port

    with tempfile.TemporaryDirectory(prefix="nodepilot-probe-") as tmp:
        config_path = os.path.join(tmp, "config.json")
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, ensure_ascii=False)
        try:
            check = subprocess.run([binary, "check", "-c", config_path], capture_output=True,
                                   text=True, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            return ProxyProbeResult(False, False, None, None, 0, f"sing_box_check_failed:{exc}")
        if check.returncode != 0:
            return ProxyProbeResult(False, False, None, None, 0,
                                    f"invalid_sing_box_config:{check.stderr.strip()[:300]}")
        try:
            process = subprocess.Popen([binary, "run", "-c", config_path], stdout=subprocess.DEVNULL,
                                       stderr=subprocess.PIPE, text=True)
        except OSError as exc:
            return ProxyProbeResult(False, False, None, None, 0, f"sing_box_start_failed:{exc}")
        try:
            if not _wait_for_port(local_port, process, min(timeout_s, 3.0)):
                return ProxyProbeResult(False, False, None, None, 0,
                                        f"local_proxy_start_failed:{_process_error(process)}")
            started = time.perf_counter()
            connectivity = _curl_request(local_port, connectivity_url, timeout_s=timeout_s,
                                          output_path=os.path.join(tmp, "connectivity.bin"), compressed=False)
            connectivity_latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if not connectivity[0].startswith(("2", "3")):
                return ProxyProbeResult(False, False, connectivity_latency_ms, None, 0,
                                        f"connectivity_http_status:{connectivity[0]}")
            youtube_ok = False
            youtube_latency_ms: float | None = None
            youtube_error: str | None = None
            try:
                started = time.perf_counter()
                youtube = _curl_request(local_port, test_url, timeout_s=timeout_s,
                                         output_path=os.path.join(tmp, "youtube.bin"), compressed=True)
                youtube_latency_ms = round((time.perf_counter() - started) * 1000, 2)
                youtube_ok = youtube[0].startswith(("2", "3"))
                if not youtube_ok:
                    youtube_error = f"youtube_http_status:{youtube[0]}"
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                youtube_error = str(exc)
            started = time.perf_counter()
            speed = _curl_request(local_port, speed_url, timeout_s=timeout_s,
                                  output_path=os.path.join(tmp, "speed.bin"), compressed=False)
            elapsed_s = time.perf_counter() - started
            if not speed[0].startswith(("2", "3")):
                return ProxyProbeResult(False, youtube_ok, youtube_latency_ms, None, 0,
                                        f"speed_http_status:{speed[0]}")
            size = int(float(speed[1]))
            if size <= 0 or elapsed_s <= 0:
                return ProxyProbeResult(False, youtube_ok, youtube_latency_ms, None, 0, "empty_speed_sample")
            return ProxyProbeResult(True, youtube_ok,
                                    youtube_latency_ms if youtube_latency_ms is not None else connectivity_latency_ms,
                                    round(size * 8 / elapsed_s / 1_000_000, 3), size,
                                    None if youtube_ok else f"youtube_unverified:{youtube_error or 'request_failed'}")
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            return ProxyProbeResult(False, False, None, None, 0, str(exc))
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


def _curl_request(local_port: int, url: str, *, timeout_s: float, output_path: str,
                  compressed: bool) -> tuple[str, str]:
    command = ["curl", "--silent", "--show-error", "--location", "--proxy", f"http://127.0.0.1:{local_port}",
               "--connect-timeout", str(max(1, int(timeout_s))), "--max-time", str(max(1, int(timeout_s))),
               "--output", output_path, "--write-out", "%{http_code} %{size_download}"]
    if compressed:
        command.append("--compressed")
    command.append(url)
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_s + 2, check=False)
    if completed.returncode != 0:
        raise subprocess.SubprocessError(completed.stderr.strip() or "proxy_request_failed")
    parts = completed.stdout.strip().split()
    if len(parts) != 2:
        raise ValueError("invalid_curl_result")
    return parts[0], parts[1]


def _build_config(source_uri: str) -> dict[str, object]:
    value = source_uri.strip()
    parsed = urlsplit(value)
    protocol = parsed.scheme.lower()
    if protocol == "vmess":
        return _build_vmess_config(value)
    if protocol == "ss":
        return _build_ss_config(value)
    if protocol not in {"vless", "trojan"} or not parsed.hostname or not parsed.port:
        raise ValueError("unsupported_or_invalid_uri")
    query = {k: unquote(v[-1]) for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
    if protocol == "vless":
        if not parsed.username:
            raise ValueError("missing_vless_uuid")
        outbound: dict[str, object] = {"type": "vless", "tag": "node", "server": parsed.hostname,
                                       "server_port": parsed.port, "uuid": unquote(parsed.username)}
        if query.get("flow"):
            flow = query["flow"]
            outbound["flow"] = "xtls-rprx-vision" if flow == "xtls-rprx-vision-udp443" else flow
    else:
        if parsed.username is None:
            raise ValueError("missing_trojan_password")
        outbound = {"type": "trojan", "tag": "node", "server": parsed.hostname,
                    "server_port": parsed.port, "password": unquote(parsed.username),
                    "tls": {"enabled": True}}
    _apply_transport_and_tls(outbound, query, force_tls=(protocol == "trojan"))
    return _base_config(outbound)


def _build_ss_config(source_uri: str) -> dict[str, object]:
    payload = source_uri.split("://", 1)[1].split("#", 1)[0]
    if "@" in payload:
        userinfo, hostport = payload.rsplit("@", 1)
        userinfo += "=" * (-len(userinfo) % 4)
        try:
            decoded = base64.urlsafe_b64decode(userinfo).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid_shadowsocks_credentials") from exc
        if ":" not in decoded or ":" not in hostport:
            raise ValueError("invalid_shadowsocks_uri")
        method, password = decoded.split(":", 1)
        host, port_text = hostport.rsplit(":", 1)
    else:
        encoded = payload + "=" * (-len(payload) % 4)
        try:
            decoded = base64.urlsafe_b64decode(encoded).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid_shadowsocks_payload") from exc
        if "@" not in decoded or ":" not in decoded.split("@", 1)[0]:
            raise ValueError("invalid_shadowsocks_payload")
        credentials, hostport = decoded.rsplit("@", 1)
        method, password = credentials.split(":", 1)
        host, port_text = hostport.rsplit(":", 1)
    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError("invalid_shadowsocks_port") from exc
    if not host or not method or not password or not 1 <= port <= 65535:
        raise ValueError("invalid_shadowsocks_credentials")
    return _base_config({"type": "shadowsocks", "tag": "node", "server": host,
                         "server_port": port, "method": unquote(method), "password": unquote(password)})


def _build_vmess_config(source_uri: str) -> dict[str, object]:
    encoded = source_uri.split("://", 1)[1].split("#", 1)[0]
    encoded += "=" * (-len(encoded) % 4)
    try:
        data = json.loads(base64.b64decode(encoded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_vmess_payload") from exc
    server, port, uuid = str(data.get("add", "")), int(data.get("port", 0) or 0), str(data.get("id", ""))
    if not server or not port or not uuid:
        raise ValueError("missing_vmess_credentials")
    outbound: dict[str, object] = {"type": "vmess", "tag": "node", "server": server,
                                   "server_port": port, "uuid": uuid, "security": str(data.get("scy") or "auto")}
    if int(data.get("aid", 0) or 0) > 0:
        outbound["alter_id"] = int(data["aid"])
    query = {"security": "tls" if str(data.get("tls", "")).lower() == "tls" else "",
             "sni": str(data.get("sni") or data.get("host") or ""),
             "type": str(data.get("net") or "tcp").lower(), "host": str(data.get("host") or ""),
             "path": str(data.get("path") or "/"), "serviceName": str(data.get("path") or "")}
    _apply_transport_and_tls(outbound, query)
    return _base_config(outbound)


def _apply_transport_and_tls(outbound: dict[str, object], query: dict[str, str], *, force_tls: bool = False) -> None:
    security = query.get("security", "")
    if force_tls:
        security = "tls"
    if security in {"tls", "reality"}:
        tls: dict[str, object] = {"enabled": True}
        if query.get("sni"):
            tls["server_name"] = query["sni"]
        if query.get("allowInsecure") == "1" or query.get("insecure") == "1":
            tls["insecure"] = True
        if query.get("alpn"):
            tls["alpn"] = [p for p in query["alpn"].split(",") if p]
        if security == "reality":
            public_key = query.get("pbk")
            if not public_key:
                raise ValueError("missing_reality_public_key")
            tls["reality"] = {"enabled": True, "public_key": public_key, "short_id": query.get("sid", "")}
            tls["utls"] = {"enabled": True, "fingerprint": query.get("fp") or "chrome"}
        elif query.get("fp"):
            tls["utls"] = {"enabled": True, "fingerprint": query["fp"]}
        outbound["tls"] = tls
    transport = query.get("type", "tcp")
    if transport == "ws":
        ws: dict[str, object] = {"type": "ws", "path": query.get("path", "/")}
        if query.get("host"):
            ws["headers"] = {"Host": query["host"]}
        outbound["transport"] = ws
    elif transport == "grpc":
        outbound["transport"] = {"type": "grpc", "service_name": query.get("serviceName", ""), "idle_timeout": "30s"}


def _base_config(outbound: dict[str, object]) -> dict[str, object]:
    return {"log": {"level": "error"},
            "inbounds": [{"type": "mixed", "tag": "mixed", "listen": "127.0.0.1", "listen_port": 0}],
            "outbounds": [outbound], "route": {"final": "node"}}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int, process: subprocess.Popen[str], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def _process_error(process: subprocess.Popen[str]) -> str:
    if process.stderr is None:
        return "process_exited"
    try:
        output = process.stderr.read(1000).strip()
    except OSError:
        return "process_exited"
    return output.replace("\n", " ")[:500] or "process_exited"
