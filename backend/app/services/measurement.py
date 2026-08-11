from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Measurement:
    """A normalized result produced by an authorized measurement adapter."""

    latency_ms: float
    download_mbps: float
    packet_loss_pct: float
    availability_pct: float

    def __post_init__(self) -> None:
        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")
        if self.download_mbps < 0:
            raise ValueError("download_mbps cannot be negative")
        if not 0 <= self.packet_loss_pct <= 100:
            raise ValueError("packet_loss_pct must be between 0 and 100")
        if not 0 <= self.availability_pct <= 100:
            raise ValueError("availability_pct must be between 0 and 100")


def merge_measurements(values: list[Measurement]) -> Measurement:
    """Aggregate repeated measurements using robust medians.

    The median reduces the effect of one unusually slow or fast sample.
    An empty series is rejected rather than inventing a measurement.
    """
    if not values:
        raise ValueError("at least one measurement is required")

    def median(items: list[float]) -> float:
        ordered = sorted(items)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[middle]
        return (ordered[middle - 1] + ordered[middle]) / 2

    return Measurement(
        latency_ms=median([v.latency_ms for v in values]),
        download_mbps=median([v.download_mbps for v in values]),
        packet_loss_pct=median([v.packet_loss_pct for v in values]),
        availability_pct=median([v.availability_pct for v in values]),
    )
