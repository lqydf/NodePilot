from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

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


def run_live_pipeline(
    urls: list[str],
    *,
    region: str | None = None,
    region_by_url: dict[str, str] | None = None,
    limit: int = 10,
    timeout: float = 3.0,
    max_candidates: int = 1000,
    workers: int = 32,
) -> LiveRun:
    """Collect, probe and rank nodes.

    Set NODEPILOT_REAL_PROXY_TEST=1 to require a real proxied HTTPS request
    through each candidate. The normal local mode retains TCP-only probing so
    development does not require an external sing-box binary.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if max_candidates < 1:
        raise ValueError("max_candidates must be at least 1")
    if workers < 1:
        raise ValueError("workers must be at least 1")

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
    measured: list[tuple[Node, Measurement]] = []
    real_proxy_test = os.environ.get("NODEPILOT_REAL_PROXY_TEST") == "1"

    def measure(node: Node) -> tuple[Node, Measurement] | None:
        if real_proxy_test:
            if not node.source_uri:
                return None
            result = probe_proxy(node.source_uri, timeout_s=max(timeout, 8.0))
            if not result.ok or result.latency_ms is None:
                return None
            elapsed_s = result.latency_ms / 1000
            speed_mbps = (result.bytes_received * 8 / elapsed_s / 1_000_000) if elapsed_s > 0 else 0.0
            return node, Measurement(
                latency_ms=result.latency_ms,
                download_mbps=round(speed_mbps, 3),
                packet_loss_pct=0.0,
                availability_pct=100.0,
            )

        host, port = _endpoint(node)
        if host is None or port is None:
            return None
        result = tcp_probe(host, port, timeout_s=timeout)
        if not result.connected or result.latency_ms is None:
            return None
        return node, Measurement(
            latency_ms=result.latency_ms,
            download_mbps=0.0,
            packet_loss_pct=0.0,
            availability_pct=100.0,
        )

    with ThreadPoolExecutor(max_workers=min(workers, len(candidates) or 1)) as pool:
        futures = [pool.submit(measure, node) for node in candidates]
        for future in as_completed(futures):
            item = future.result()
            if item is not None:
                measured.append(item)

    measured.sort(key=lambda item: (item[1].latency_ms, item[0].node_id))
    reachable_ranked = [
        ReachableNode(node=node, measurement=measurement, rank=index)
        for index, (node, measurement) in enumerate(measured[:limit], start=1)
    ]

    return LiveRun(
        sources=source_runs,
        candidates=len(candidates),
        reachable=len(measured),
        ranked=rank_nodes(measured, limit=limit),
        reachable_ranked=reachable_ranked,
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
