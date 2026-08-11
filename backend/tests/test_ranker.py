from app.models.source import Node
from app.services.measurement import Measurement
from app.services.ranker import rank_nodes


def node(node_id: str) -> Node:
    return Node(
        node_id=node_id,
        protocol="vless",
        region="JP",
        latency_ms=None,
        download_mbps=None,
        packet_loss_pct=None,
        availability_pct=None,
    )


def measurement(latency: float, speed: float, loss: float = 1.0, availability: float = 99.0) -> Measurement:
    return Measurement(
        latency_ms=latency,
        download_mbps=speed,
        packet_loss_pct=loss,
        availability_pct=availability,
    )


def test_ranker_prefers_quality_over_latency_alone():
    candidates = [
        (node("slow-fast"), measurement(90, 80)),
        (node("fast-slow"), measurement(40, 8)),
    ]
    ranked = rank_nodes(candidates)
    assert ranked[0].node.node_id == "slow-fast"
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2


def test_ranker_filters_ineligible_nodes():
    candidates = [
        (node("good"), measurement(70, 60)),
        (node("bad-latency"), measurement(301, 100)),
        (node("bad-speed"), measurement(50, 4.9)),
    ]
    ranked = rank_nodes(candidates)
    assert [item.node.node_id for item in ranked] == ["good"]


def test_ranker_limit_and_deterministic_tie_break():
    candidates = [
        (node("b"), measurement(50, 50)),
        (node("a"), measurement(50, 50)),
        (node("c"), measurement(50, 50)),
    ]
    ranked = rank_nodes(candidates, limit=2)
    assert [item.node.node_id for item in ranked] == ["a", "b"]
    assert [item.rank for item in ranked] == [1, 2]
