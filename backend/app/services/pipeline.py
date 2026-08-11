from __future__ import annotations

from dataclasses import dataclass

from app.models.node import Node
from app.services.collector import collect_from_text
from app.services.measurement import Measurement
from app.services.ranker import RankedNode, rank_nodes
from app.services.source_fetcher import fetch_text_source


@dataclass(frozen=True, slots=True)
class SourceResult:
    url: str
    nodes_found: int
    error: str | None = None


def collect_sources(urls: list[str], *, timeout: float = 10.0) -> tuple[list[Node], list[SourceResult]]:
    """Fetch public text sources and normalize their node records."""
    all_nodes: list[Node] = []
    results: list[SourceResult] = []
    for url in urls:
        try:
            text = fetch_text_source(url, timeout=timeout)
            nodes = collect_from_text(text)
            all_nodes.extend(nodes)
            results.append(SourceResult(url=url, nodes_found=len(nodes)))
        except Exception as exc:  # source failures must not stop other sources
            results.append(SourceResult(url=url, nodes_found=0, error=str(exc)))
    return _dedupe_nodes(all_nodes), results


def build_top10(nodes: list[Node], measurements: dict[str, Measurement]) -> list[RankedNode]:
    """Rank nodes for which a measurement exists."""
    candidates = [(node, measurements[node.node_id]) for node in nodes if node.node_id in measurements]
    return rank_nodes(candidates, limit=10)


def _dedupe_nodes(nodes: list[Node]) -> list[Node]:
    seen: set[str] = set()
    result: list[Node] = []
    for node in nodes:
        if node.node_id not in seen:
            seen.add(node.node_id)
            result.append(node)
    return result
