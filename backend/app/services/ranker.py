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
    provisional: bool = False


def rank_nodes(
    candidates: list[tuple[Node, Measurement]],
    *,
    limit: int = 10,
) -> list[RankedNode]:
    """Rank nodes that have passed the full V1 quality gate."""
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


def rank_verified_nodes(
    candidates: list[tuple[Node, Measurement, bool]],
    *,
    limit: int = 10,
) -> list[RankedNode]:
    """Rank nodes after real proxy verification.

    Fully measured nodes use the normal V1 quality gate. A proxy that genuinely
    forwarded traffic but has no completed speed test is retained as a
    provisional fallback, ranked by measured proxy latency only. This prevents
    a failed enrichment test from being mistaken for a failed proxy.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")

    full: list[tuple[Node, Measurement, QualityResult, bool]] = []
    provisional: list[tuple[Node, Measurement, QualityResult, bool]] = []
    for node, measurement, speed_tested in candidates:
        quality = quality_score(measurement)
        if quality.eligible:
            full.append((node, measurement, quality, False))
        elif not speed_tested and measurement.latency_ms <= 300:
            fallback_score = round(max(0.0, 1.0 - measurement.latency_ms / 300.0) * 100.0, 2)
            provisional.append(
                (node, measurement, QualityResult(fallback_score, True, "proxy_verified_speed_unmeasured"), True)
            )

    full.sort(key=lambda item: (-item[2].score, item[1].latency_ms, -item[1].download_mbps, node_key(item[0])))
    provisional.sort(key=lambda item: (-item[2].score, item[1].latency_ms, node_key(item[0])))
    ordered = (full + provisional)[:limit]
    return [
        RankedNode(node=node, measurement=measurement, quality=quality, rank=index, provisional=is_provisional)
        for index, (node, measurement, quality, is_provisional) in enumerate(ordered, start=1)
    ]


def node_key(node: Node) -> str:
    return node.node_id
