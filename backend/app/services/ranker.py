from __future__ import annotations

from dataclasses import dataclass

from app.models.node import Node
from app.services.measurement import Measurement
from app.services.quality import QualityResult, quality_score


@dataclass(frozen=True, slots=True)
class RankedNode:
    node: Node
    measurement: Measurement
    quality: QualityResult
    rank: int


def rank_nodes(
    candidates: list[tuple[Node, Measurement]],
    *,
    limit: int = 10,
) -> list[RankedNode]:
    """Filter and rank measured nodes for the Asia-focused TOP list.

    Only eligible measurements are ranked. Ties are resolved deterministically
    by score, latency, download speed, and node_id so repeated runs are stable.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")

    scored: list[tuple[Node, Measurement, QualityResult]] = []
    for node, measurement in candidates:
        quality = quality_score(measurement)
        if quality.eligible:
            scored.append((node, measurement, quality))

    scored.sort(
        key=lambda item: (
            -item[2].score,
            item[1].latency_ms,
            -item[1].download_mbps,
            node_key(item[0]),
        )
    )

    return [
        RankedNode(node=node, measurement=measurement, quality=quality, rank=index)
        for index, (node, measurement, quality) in enumerate(scored[:limit], start=1)
    ]


def node_key(node: Node) -> str:
    return node.node_id
