from __future__ import annotations

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
class LiveRun:
    sources: list[SourceRun]
    candidates: int
    reachable: int
    ranked: list[RankedNode]


def run_live_pipeline(
    urls: list[str], *, region: str | None = None, limit: int = 10, timeout: float = 3.0
) -> LiveRun:
    """Fetch public text sources, parse nodes, probe endpoints, and rank them.

    This MVP intentionally measures TCP reachability only. It does not relay
    traffic or attempt to authenticate to a proxy service.
    """
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
    candidates = list(unique.values())
    measured: list[tuple[Node, Measurement]] = []
    reachable = 0

    for node in candidates:
        host, port = _endpoint(node)
        if host is None or port is None:
            continue
        result = tcp_probe(host, port, timeout_s=timeout)
        if not result.connected or result.latency_ms is None:
            continue
        reachable += 1
        measured.append(
            (
                node,
                Measurement(
                    latency_ms=result.latency_ms,
                    download_mbps=0.0,
                    packet_loss_pct=0.0,
                    availability_pct=100.0,
                ),
            )
        )

    return LiveRun(
        sources=source_runs,
        candidates=len(candidates),
        reachable=reachable,
        ranked=rank_nodes(measured, limit=limit),
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
