from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from app.models.node import Node
from app.services.collector import collect_from_text
from app.services.measurement import Measurement
from app.services.probe import tcp_probe
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
    limit: int = 10,
    timeout: float = 3.0,
    max_candidates: int = 1000,
    workers: int = 32,
) -> LiveRun:
    """Fetch public text sources, probe a bounded candidate set, and rank results.

    The current MVP measures TCP reachability only. It does not relay traffic
    or authenticate to proxy services. Candidate probing is bounded and
    concurrent so one stale source cannot create an unbounded scan.
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
        parsed = collect_from_text(text, region=region)
        nodes.extend(parsed)
        source_runs.append(SourceRun(url, True, len(parsed)))

    unique: dict[str, Node] = {node.node_id: node for node in nodes}
    candidates = list(unique.values())[:max_candidates]
    measured: list[tuple[Node, Measurement]] = []

    def measure(node: Node) -> tuple[Node, Measurement] | None:
        host, port = _endpoint(node)
        if host is None or port is None:
            return None
        result = tcp_probe(host, port, timeout_s=timeout)
        if not result.connected or result.latency_ms is None:
            return None
        return (
            node,
            Measurement(
                latency_ms=result.latency_ms,
                download_mbps=0.0,
                packet_loss_pct=0.0,
                availability_pct=100.0,
            ),
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
    """Extract the endpoint from the canonical node id without probing arbitrary text."""
    endpoint = node.node_id.rsplit("@", 1)[-1]
    host, separator, port_text = endpoint.rpartition(":")
    if not separator or not host or not port_text.isdigit():
        return None, None
    port = int(port_text)
    if not 1 <= port <= 65535:
        return None, None
    return host.strip("[]"), port
