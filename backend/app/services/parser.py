from __future__ import annotations

from urllib.parse import urlsplit

from app.models.node import Node

SUPPORTED_SCHEMES = {"vmess", "vless", "trojan", "ss"}


def parse_node_uri(uri: str, *, region: str | None = None) -> Node | None:
    """Parse a URI into a safe normalized record while preserving its source URI."""
    value = uri.strip()
    if not value or "://" not in value:
        return None

    parsed = urlsplit(value)
    protocol = parsed.scheme.lower()
    if protocol not in SUPPORTED_SCHEMES or not parsed.hostname:
        return None

    try:
        port = parsed.port
    except ValueError:
        return None
    endpoint = f"{parsed.hostname}:{port or ''}".lower()
    identity = parsed.username or ""
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
