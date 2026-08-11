from unittest.mock import patch

from app.models.node import Node
from app.services.measurement import Measurement
from app.services.pipeline import build_top10, collect_sources


def test_collect_sources_merges_and_deduplicates():
    text = "\n".join([
        "vless://user@example.com:443#one",
        "vless://user@example.com:443#duplicate",
        "vless://other@example.com:443#two",
    ])
    with patch("app.services.pipeline.fetch_text_source", return_value=text):
        nodes, results = collect_sources(["https://source.example/a"])
    assert len(nodes) == 2
    assert results[0].nodes_found == 2
    assert results[0].error is None


def test_collect_sources_keeps_working_when_one_source_fails():
    def fake_fetch(url: str, *, timeout: float):
        if url.endswith("bad"):
            raise RuntimeError("temporary failure")
        return "vless://user@example.com:443"

    with patch("app.services.pipeline.fetch_text_source", side_effect=fake_fetch):
        nodes, results = collect_sources([
            "https://source.example/good",
            "https://source.example/bad",
        ])
    assert len(nodes) == 1
    assert results[0].error is None
    assert results[1].error == "temporary failure"


def test_build_top10_uses_only_measured_nodes():
    nodes = [
        Node(node_id="vless:a@example.com:443", protocol="vless", region="JP"),
        Node(node_id="vless:b@example.com:443", protocol="vless", region="SG"),
    ]
    measurements = {
        nodes[0].node_id: Measurement(70, 60, 1, 99),
    }
    ranked = build_top10(nodes, measurements)
    assert len(ranked) == 1
    assert ranked[0].node.node_id == nodes[0].node_id
