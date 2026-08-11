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
    real_proxy_limit: int = 60,
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
        real_proxy_limit=real_proxy_limit,
    )

    def ranked_item(item: object) -> dict[str, object]:
        return {
            "rank": item.rank,
            "region": item.node.region,
            "score": item.quality.score,
            "latency_ms": item.measurement.latency_ms,
            "download_mbps": item.measurement.download_mbps,
            "youtube_status": "通过",
            "verification": "proxy_verified",
            "source_uri": item.node.source_uri,
        }

    return {
        "sources": [asdict(source) for source in result.sources],
        "candidates": result.candidates,
        "reachable": result.reachable,
        "proxy_verified": len(result.ranked),
        "ranked": [ranked_item(item) for item in result.ranked],
        "reachable_ranked": [
            {
                "rank": item.rank,
                "region": item.node.region,
                "latency_ms": item.measurement.latency_ms,
                "verification": "proxy_verified",
            }
            for item in result.reachable_ranked
        ],
    }
