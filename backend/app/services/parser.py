from __future__ import annotations

import base64
import binascii
import html
import json
from urllib.parse import urlsplit

from app.models.node import Node

SUPPORTED_SCHEMES = {"vmess", "vless", "trojan", "ss"}


def _decode_b64(value: str) -> bytes | None:
    value = value.strip().replace("-", "+").replace("_", "/")
    value += "=" * (-len(value) % 4)
    try:
        return base64.b64decode(value, validate=False)
    except (ValueError, binascii.Error):
        return None


def _parse_vmess(value: str, region: str | None) -> Node | None:
    payload = value[len("vmess://") :].strip()
    decoded = _decode_b64(payload)
    if not decoded:
        return None
    try:
        data = json.loads(decoded.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    host = str(data.get("add") or "").strip()
    try:
        port = int(data.get("port"))
    except (TypeError, ValueError):
        return None
    identity = str(data.get("id") or "").strip()
    if not host or not identity or not 1 <= port <= 65535:
        return None
    return Node(
        node_id=f"vmess:{identity}@{host}:{port}".lower(),
        protocol="vmess",
        region=region,
        source_uri=value,
    )


def parse_node_uri(uri: str, *, region: str | None = None) -> Node | None:
    """Parse VLESS/Trojan/SS URIs and standard base64 VMess links."""
    value = html.unescape(uri).strip()
    if not value or "://" not in value:
        return None
    if value.lower().startswith("vmess://"):
        return _parse_vmess(value, region)

    parsed = urlsplit(value)
    protocol = parsed.scheme.lower()
    if protocol not in SUPPORTED_SCHEMES or not parsed.hostname:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    if port is None or not 1 <= port <= 65535:
        return None
    identity = parsed.username or ""
    endpoint = f"{parsed.hostname}:{port}".lower()
    node_id = f"{protocol}:{identity}@{endpoint}" if identity else f"{protocol}:{endpoint}"
    return Node(node_id=node_id, protocol=protocol, region=region, source_uri=value)


def parse_text(text: str, *, region: str | None = None) -> list[Node]:
    """Parse one URI per line, ignoring blank and unsupported lines."""
    nodes: list[Node] = []
    for line in text.splitlines():
        node = parse_node_uri(line, region=region)
        if node is not None:
            nodes.append(node)
    return nodes
