from app.models.node import Node
from app.services.ranking import top_nodes
from app.services.scoring import score_node


def test_fast_stable_node_scores_high():
    node = Node(
        node_id="fast-1",
        protocol="test",
        region="JP",
        latency_ms=60,
        download_mbps=80,
        packet_loss_pct=0.5,
        availability_pct=99,
    )
    score = score_node(node)
    assert score is not None
    assert score.total > 85


def test_hard_filter_rejects_slow_node():
    node = Node(
        node_id="slow-1",
        protocol="test",
        latency_ms=350,
        download_mbps=100,
        packet_loss_pct=0,
        availability_pct=99,
    )
    assert score_node(node) is None


def test_top_nodes_limit_and_region_diversity():
    nodes = [
        Node(f"jp-{i}", "test", "JP", 50 + i, 100, 0, 100)
        for i in range(5)
    ] + [
        Node("sg-1", "test", "SG", 80, 90, 0, 99),
        Node("hk-1", "test", "HK", 70, 90, 0, 99),
    ]
    result = top_nodes(nodes, limit=10)
    assert len(result) == 5
    assert sum(1 for node, _ in result if node.region == "JP") <= 3
