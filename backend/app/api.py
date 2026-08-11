from __future__ import annotations

from dataclasses import asdict

from app.models.node import Node
from app.services.measurement import Measurement
from app.services.ranker import rank_nodes


def top_nodes_response(
    candidates: list[tuple[Node, Measurement]], *, limit: int = 10
) -> dict[str, object]:
    """Build a JSON-serializable response for the frontend TOP list."""
    ranked = rank_nodes(candidates, limit=limit)
    items = []
    for item in ranked:
        items.append(
            {
                "rank": item.rank,
                "node_id": item.node.node_id,
                "protocol": item.node.protocol,
                "region": item.node.region,
                "score": item.quality.score,
                "latency_ms": item.measurement.latency_ms,
                "download_mbps": item.measurement.download_mbps,
                "packet_loss_pct": item.measurement.packet_loss_pct,
                "availability_pct": item.measurement.availability_pct,
            }
        )
    return {"count": len(items), "items": items}
