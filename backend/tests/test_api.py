from app.api import top_nodes_response
from app.models.node import Node
from app.services.measurement import Measurement


def node(node_id: str, region: str = "JP") -> Node:
    return Node(node_id=node_id, protocol="vless", region=region)


def measurement(latency: float, speed: float) -> Measurement:
    return Measurement(
        latency_ms=latency,
        download_mbps=speed,
        packet_loss_pct=1.0,
        availability_pct=99.0,
    )


def test_top_nodes_response_is_frontend_ready():
    result = top_nodes_response(
        [
            (node("a"), measurement(80, 60)),
            (node("b", "SG"), measurement(50, 40)),
        ]
    )

    assert result["count"] == 2
    assert result["items"][0]["rank"] == 1
    assert result["items"][0]["node_id"] == "a"
    assert result["items"][0]["protocol"] == "vless"
    assert result["items"][0]["region"] == "JP"
    assert "score" in result["items"][0]
    assert "latency_ms" in result["items"][0]
    assert "download_mbps" in result["items"][0]


def test_top_nodes_response_respects_limit_and_filters_bad_nodes():
    candidates = [
        (node("good-1"), measurement(60, 80)),
        (node("good-2"), measurement(70, 70)),
        (node("bad"), Measurement(301, 100, 1, 99)),
    ]
    result = top_nodes_response(candidates, limit=1)
    assert result["count"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["node_id"] == "good-1"
