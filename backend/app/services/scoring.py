from __future__ import annotations

from dataclasses import dataclass

from app.models.node import Node


@dataclass(frozen=True, slots=True)
class Score:
    total: float
    speed: float
    stability: float
    latency: float
    packet_loss: float


def _speed_score(mbps: float) -> float:
    # 100 Mbps or above receives the full 40 points.
    return min(max(mbps, 0.0) / 100.0, 1.0) * 40.0


def _stability_score(availability_pct: float) -> float:
    return min(max(availability_pct, 0.0) / 100.0, 1.0) * 30.0


def _latency_score(latency_ms: float) -> float:
    # 0 ms -> 20 points, 300 ms -> 0 points.
    return max(0.0, 1.0 - latency_ms / 300.0) * 20.0


def _packet_loss_score(packet_loss_pct: float) -> float:
    # 0% loss -> 10 points, 5% -> 0 points.
    return max(0.0, 1.0 - packet_loss_pct / 5.0) * 10.0


def score_node(node: Node) -> Score | None:
    """Return the V1 score, or None when hard filters reject the node."""
    if not node.is_candidate:
        return None

    speed = _speed_score(node.download_mbps or 0.0)
    stability = _stability_score(node.availability_pct or 0.0)
    latency = _latency_score(node.latency_ms or 300.0)
    packet_loss = _packet_loss_score(node.packet_loss_pct or 0.0)

    return Score(
        total=round(speed + stability + latency + packet_loss, 2),
        speed=round(speed, 2),
        stability=round(stability, 2),
        latency=round(latency, 2),
        packet_loss=round(packet_loss, 2),
    )
