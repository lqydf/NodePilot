from __future__ import annotations

from app.models.node import Node


def deduplicate(nodes: list[Node]) -> list[Node]:
    """Keep the first occurrence of each normalized endpoint."""
    seen: set[str] = set()
    result: list[Node] = []
    for node in nodes:
        if node.node_id in seen:
            continue
        seen.add(node.node_id)
        result.append(node)
    return result
