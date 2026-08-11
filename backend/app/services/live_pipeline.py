from __future__ import annotations

import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from app.models.node import Node
from app.services.collector import collect_from_text
from app.services.measurement import Measurement
from app.services.probe import tcp_probe
from app.services.proxy_probe import probe_proxy
from app.services.ranker import RankedNode, rank_nodes
from app.services.source_fetcher import SourceFetchError, fetch_text_source


@dataclass(frozen=True, slots=True)
class SourceRun:
    url: str
    fetched: bool
    node_count: int
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ReachableNode:
    node: Node
    measurement: Measurement
    rank: int


@dataclass(frozen=True, slots=True)
class LiveRun:
    sources: list[SourceRun]
    candidates: int
    reachable: int
    ranked: list[RankedNode]
    reachable_ranked: list[ReachableNode]
    proxy_verified: int
    proxy_errors: dict[str, int] = field(default_factory=dict)


def run_live_pipeline(
    urls: list[str],
    *,
    region: str | None = None,
    region_by_url: dict[str, str] | None = None,
    limit: int = 10,
    timeout: float = 3.0,
    max_candidates: int = 1000,
    workers: int = 32,
    real_proxy_limit: int = 60,
) -> LiveRun:
    """Collect globally, TCP-filter, then verify actual proxy usability."""
    if min(limit, max_candidates, workers, real_proxy_limit) < 1:
        raise ValueError("limits and workers must be at least 1")

    nodes: list[Node] = []
    source_runs: list[SourceRun] = []
    for url in urls:
        try:
            text = fetch_text_source(url, timeout=timeout)
        except SourceFetchError as exc:
            source_runs.append(SourceRun(url, False, 0, str(exc)))
            continue
        source_region = (region_by_url or {}).get(url, region)
        parsed = collect_from_text(text, region=source_region)
        nodes.extend(parsed)
        source_runs.append(SourceRun(url, True, len(parsed)))

    unique: dict[str, Node] = {node.node_id: node for node in nodes}
    candidates = list(unique.values())[:max_candidates]

    def tcp_measure(node: Node) -> tuple[Node, Measurement] | None:
        host, port = _endpoint(node)
        if host is None or port is None:
            return None
        tcp = tcp_probe(host, port, timeout_s=timeout)
        if not tcp.connected or tcp.latency_ms is None:
            return None
        return node, Measurement(
            latency_ms=tcp.latency_ms,
            download_mbps=0.0,
            packet_loss_pct=0.0,
            availability_pct=100.0,
        )

    tcp_reachable: list[tuple[Node, Measurement]] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(candidates) or 1)) as pool:
        futures = [pool.submit(tcp_measure, node) for node in candidates]
        for future in as_completed(futures):
            item = future.result()
            if item is not None:
                tcp_reachable.append(item)
    tcp_reachable.sort(key=lambda item: (item[1].latency_ms, item[0].node_id))

    measured: list[tuple[Node, Measurement]] = []
    proxy_errors: Counter[str] = Counter()
    real_proxy_test = os.environ.get("NODEPILOT_REAL_PROXY_TEST") == "1"
    if real_proxy_test:
        proxy_candidates = tcp_reachable[:real_proxy_limit]

        def proxy_measure(item: tuple[Node, Measurement]) -> tuple[Node, Measurement] | tuple[None, str]:
            node, _tcp = item
            if not node.source_uri:
                return None, "missing_source_uri"
            result = probe_proxy(node.source_uri, timeout_s=max(timeout, 5.0))
            if not result.ok or result.youtube_latency_ms is None or result.download_mbps is None:
                return None, result.error or "proxy_verification_failed"
            return node, Measurement(
                latency_ms=result.youtube_latency_ms,
                download_mbps=result.download_mbps,
                packet_loss_pct=0.0,
                availability_pct=100.0,
            )

        with ThreadPoolExecutor(max_workers=min(workers, len(proxy_candidates) or 1)) as pool:
            futures = [pool.submit(proxy_measure, item) for item in proxy_candidates]
            for future in as_completed(futures):
                item = future.result()
                if item[0] is not None:
                    measured.append(item)  # type: ignore[arg-type]
                else:
                    proxy_errors[item[1]] += 1
        measured.sort(key=lambda item: (item[1].latency_ms, item[0].node_id))

    ranked = rank_nodes(measured, limit=limit)
    reachable_source = measured if real_proxy_test else tcp_reachable
    reachable_ranked = [
        ReachableNode(node=node, measurement=measurement, rank=index)
        for index, (node, measurement) in enumerate(reachable_source[:limit], start=1)
    ]

    return LiveRun(
        sources=source_runs,
        candidates=len(candidates),
        reachable=len(tcp_reachable),
        ranked=ranked,
        reachable_ranked=reachable_ranked,
        proxy_verified=len(measured),
        proxy_errors=dict(proxy_errors),
    )


def _endpoint(node: Node) -> tuple[str, int] | tuple[None, None]:
    endpoint = node.node_id.rsplit("@", 1)[-1]
    host, separator, port_text = endpoint.rpartition(":")
    if not separator or not host or not port_text.isdigit():
        return None, None
    port = int(port_text)
    if not 1 <= port <= 65535:
        return None, None
    return host.strip("[]"), port
