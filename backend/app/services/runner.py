from __future__ import annotations

from dataclasses import asdict

from app.services.live_pipeline import LiveRun, run_live_pipeline


def run_once(
    urls: list[str],
    *,
    region: str | None = None,
    region_by_url: dict[str, str] | None = None,
    limit: int = 10,
    timeout: float = 3.0,
    max_candidates: int = 1000,
    workers: int = 32,
) -> dict[str, object]:
    """Run one real collection/probe cycle and return JSON-friendly summary data."""
    result: LiveRun = run_live_pipeline(
        urls,
        region=region,
        region_by_url=region_by_url,
        limit=limit,
        timeout=timeout,
        max_candidates=max_candidates,
        workers=workers,
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
                "source_uri": item.node.source_uri,
            }
            for item in result.ranked
        ],
        "reachable_ranked": [
            {
                "rank": item.rank,
                "node_id": item.node.node_id,
                "protocol": item.node.protocol,
                "region": item.node.region,
                "latency_ms": item.measurement.latency_ms,
                "source_uri": item.node.source_uri,
            }
            for item in result.reachable_ranked
        ],
    }
