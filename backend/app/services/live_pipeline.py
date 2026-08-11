from __future__ import annotations

from dataclasses import dataclass

from app.models.node import Node
from app.services.measurement import Measurement
from app.services.probe import probe
from app.services.ranker import RankedNode, rank_nodes
from app.services.source_fetcher import fetch_source
from app.services.collector import collect_from_text


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
        result = fetch_source(url, timeout=timeout)
        if not result.ok:
            source_runs.append(SourceRun(url, False, 0, result.error))
            continue
        parsed = collect_from_text(result.text, region=region)
        nodes.extend(parsed)
        source_runs.append(SourceRun(url, True, len(parsed)))

    unique: dict[str, Node] = {node.node_id: node for node in nodes}
    candidates = list(unique.values())
    measured: list[tuple[Node, Measurement]] = []
    reachable = 0

    for node in candidates:
        host_port = node.node_id.split("@", 1)[-1]
        host, _, port_text = host_port.rpartition(":")
        if not host or not port_text.isdigit():
            continue
        result = probe(host, int(port_text), timeout=timeout)
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
