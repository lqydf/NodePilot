from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True, slots=True)
class ProxyProbeResult:
    ok: bool
    latency_ms: float | None
    bytes_received: int
    error: str | None = None


def probe_proxy(source_uri: str, *, timeout_s: float = 8.0, test_url: str = "https://www.youtube.com/") -> ProxyProbeResult:
    """Perform a real proxied HTTPS request through a VLESS/Trojan/SS node."""
    binary = os.environ.get("SING_BOX_BIN", "sing-box")
    try:
        config = _build_config(source_uri)
    except ValueError as exc:
        return ProxyProbeResult(False, None, 0, str(exc))

    local_port = _free_port()
    config["inbounds"][0]["listen_port"] = local_port

    with tempfile.TemporaryDirectory(prefix="nodepilot-probe-") as tmp:
        config_path = os.path.join(tmp, "config.json")
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, ensure_ascii=False)

        process = subprocess.Popen(
            [binary, "run", "-c", config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            if not _wait_for_port(local_port, process, timeout_s=min(timeout_s, 3.0)):
                return ProxyProbeResult(False, None, 0, "local_proxy_start_failed")

            started = time.perf_counter()
            command = [
                "curl", "--silent", "--show-error", "--location",
                "--proxy", f"http://127.0.0.1:{local_port}",
                "--connect-timeout", str(max(1, int(timeout_s))),
                "--max-time", str(max(1, int(timeout_s))),
                "--output", os.path.join(tmp, "response.bin"),
                "--write-out", "%{http_code} %{size_download}",
                test_url,
            ]
            completed = subprocess.run(
                command, capture_output=True, text=True,
                timeout=timeout_s + 2, check=False,
            )
            elapsed = (time.perf_counter() - started) * 1000
            if completed.returncode != 0:
                return ProxyProbeResult(False, None, 0, completed.stderr.strip() or "proxy_request_failed")

            parts = completed.stdout.strip().split()
            if len(parts) != 2 or parts[0] not in {"200", "204", "206"}:
                return ProxyProbeResult(False, None, 0, f"unexpected_http_status:{parts[0] if parts else 'unknown'}")
            size = int(float(parts[1]))
            return ProxyProbeResult(True, round(elapsed, 2), size)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            return ProxyProbeResult(False, None, 0, str(exc))
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


def _build_config(source_uri: str) -> dict[str, object]:
    parsed = urlsplit(source_uri.strip())
    protocol = parsed.scheme.lower()
    if protocol not in {"vless", "trojan", "ss"} or not parsed.hostname or not parsed.port:
        raise ValueError("unsupported_or_invalid_uri")
    query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}

    if protocol == "vless":
        if not parsed.username:
            raise ValueError("missing_vless_uuid")
        outbound: dict[str, object] = {"type": "vless", "tag": "node", "server": parsed.hostname, "server_port": parsed.port, "uuid": parsed.username}
        if query.get("flow"):
            outbound["flow"] = query["flow"]
    elif protocol == "trojan":
        if parsed.username is None:
            raise ValueError("missing_trojan_password")
        outbound = {"type": "trojan", "tag": "node", "server": parsed.hostname, "server_port": parsed.port, "password": parsed.username}
    else:
        method = parsed.username or query.get("method")
        password = parsed.password or query.get("password")
        if not method or not password:
            raise ValueError("missing_shadowsocks_credentials")
        outbound = {"type": "shadowsocks", "tag": "node", "server": parsed.hostname, "server_port": parsed.port, "method": method, "password": password}

    security = query.get("security", "")
    if protocol in {"vless", "trojan"} and security in {"tls", "reality"}:
        tls: dict[str, object] = {"enabled": True}
        if query.get("sni"):
            tls["server_name"] = query["sni"]
        if security == "reality":
            public_key = query.get("pbk")
            if not public_key:
                raise ValueError("missing_reality_public_key")
            tls["reality"] = {"enabled": True, "public_key": public_key, "short_id": query.get("sid", "")}
        if query.get("fp"):
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

    return {
        "log": {"level": "error"},
        "inbounds": [{"type": "mixed", "tag": "mixed", "listen": "127.0.0.1", "listen_port": 0}],
        "outbounds": [outbound],
        "route": {"final": "node"},
    }


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
