from app.services.collector import collect_from_text
from app.services.parser import parse_node_uri


def test_parser_accepts_supported_uri():
    node = parse_node_uri("vless://user@example.com:443#demo", region="JP")
    assert node is not None
    assert node.protocol == "vless"
    assert node.region == "JP"


def test_parser_rejects_unsupported_uri():
    assert parse_node_uri("http://example.com:80") is None


def test_collector_deduplicates_endpoints():
    text = "\n".join(
        [
            "vless://user@example.com:443#one",
            "vless://another@example.com:443#two",
            "vless://third@example.com:443#three",
            "vless://user@example.com:443#duplicate",
            "not-a-node",
        ]
    )
    nodes = collect_from_text(text, region="JP")
    assert len(nodes) == 3
