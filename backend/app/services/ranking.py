from __future__ import annotations

from collections import defaultdict

from app.models.node import Node
from app.services.scoring import score_node


def top_nodes(nodes: list[Node], limit: int = 10) -> list[tuple[Node, float]]:
    """Return the highest-scoring candidates with simple region diversity.

    At most 3 results are selected from the same region in this V1 foundation.
    This prevents a single server cluster/region from dominating the list.
    """
    scored = []
    for node in nodes:
        score = score_node(node)
        if score is not None:
            scored.append((node, score.total))

    scored.sort(key=lambda item: item[1], reverse=True)

    result: list[tuple[Node, float]] = []
    region_counts: dict[str, int] = defaultdict(int)

    for node, total in scored:
        region = node.region or "unknown"
        if region_counts[region] >= 3:
            continue
        result.append((node, total))
        region_counts[region] += 1
        if len(result) >= limit:
            break

    return result
