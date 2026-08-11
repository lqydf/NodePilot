from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Node:
    """Normalized node measurement used by the V1 ranking engine."""

    node_id: str
    protocol: str
    region: Optional[str] = None
    latency_ms: Optional[float] = None
    download_mbps: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    availability_pct: Optional[float] = None

    @property
    def is_candidate(self) -> bool:
        """Apply the initial hard filters agreed for NodePilot V1."""
        if self.latency_ms is None or self.download_mbps is None:
            return False
        if self.packet_loss_pct is None or self.availability_pct is None:
            return False
        return (
            self.latency_ms <= 300
            and self.download_mbps >= 5
            and self.packet_loss_pct <= 5
            and self.availability_pct >= 80
        )
