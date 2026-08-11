from __future__ import annotations

from dataclasses import asdict

from app.services.live_pipeline import LiveRun, run_live_pipeline


def run_once(urls: list[str], *, region: str | None = None, limit: int = 10, timeout: float = 3.0) -> dict[str, object]:
    """Run one real collection/probe cycle and return JSON-friendly summary data."""
    result: LiveRun = run_live_pipeline(
        urls, region=region, limit=limit, timeout=timeout
    )
    return {
        "sources": [asdict(source) for source in result.sources],
        "candidates": result.candidates,
        "reachable": result.reachable,
        "ranked": [
            {
                "rank": item.rank,
                "node_id": item.node.node_id,
                "protocol": item.node.protocol,
                "region": item.node.region,
                "score": item.quality.score,
                "latency_ms": item.measurement.latency_ms,
            }
            for item in result.ranked
        ],
    }
