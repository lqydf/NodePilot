from __future__ import annotations

from dataclasses import dataclass

from app.services.measurement import Measurement


@dataclass(frozen=True, slots=True)
class QualityResult:
    score: float
    eligible: bool
    reason: str | None = None


def quality_score(measurement: Measurement) -> QualityResult:
    """Score a normalized measurement for the Asia-focused V1 ranking.

    Hard filters are intentionally conservative: a node must have <=300 ms
    median latency, >=5 Mbps median download, <=5% median loss, and >=80%
    availability. The weighted score then uses speed 40%, stability 30%,
    latency 20%, and packet loss 10%.
    """
    if measurement.latency_ms > 300:
        return QualityResult(0.0, False, "latency_above_300ms")
    if measurement.download_mbps < 5:
        return QualityResult(0.0, False, "download_below_5mbps")
    if measurement.packet_loss_pct > 5:
        return QualityResult(0.0, False, "packet_loss_above_5pct")
    if measurement.availability_pct < 80:
        return QualityResult(0.0, False, "availability_below_80pct")

    speed = min(measurement.download_mbps / 100, 1) * 40
    stability = measurement.availability_pct / 100 * 30
    latency = max(0, 1 - measurement.latency_ms / 300) * 20
    loss = max(0, 1 - measurement.packet_loss_pct / 5) * 10

    return QualityResult(round(speed + stability + latency + loss, 2), True)
