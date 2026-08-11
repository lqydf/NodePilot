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
    """Run one real collection/probe cycle and return public-safe summary data.

    ``subscription_uris`` is an internal-only field consumed by the snapshot
    writer. It must never be serialized into frontend/data/live.json.
    """
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
        node = item.node
        return {
            "rank": item.rank,
            "node_id": node.node_id,
            "region": node.region,
            "protocol": node.protocol,
            "score": item.quality.score,
            "latency_ms": item.measurement.latency_ms,
            "download_mbps": item.measurement.download_mbps,
            "speed_tested": item.measurement.download_mbps > 0,
            "provisional": item.provisional,
            "youtube_status": "通过" if node.node_id in result.youtube_verified else "未验证",
            "verification": "proxy_verified",
        }

    return {
        "sources": [asdict(source) for source in result.sources],
        "candidates": result.candidates,
        "reachable": result.reachable,
        "proxy_verified": result.proxy_verified,
        "youtube_verified": len(result.youtube_verified),
        "proxy_errors": result.proxy_errors,
        "ranked": [ranked_item(item) for item in result.ranked],
        "reachable_ranked": [
            {
                "rank": item.rank,
                "node_id": item.node.node_id,
                "region": item.node.region,
                "protocol": item.node.protocol,
                "latency_ms": item.measurement.latency_ms,
                "verification": "proxy_verified",
            }
            for item in result.reachable_ranked
        ],
        "subscription_uris": [item.node.source_uri for item in result.ranked if item.node.source_uri],
    }
