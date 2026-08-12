from app.services.default_sources import GLOBAL_SOURCES


REFERENCE_URL = "https://node.clash-node.com/uploads/2026/08/2-20260805.yaml"


def test_reference_clash_yaml_source_is_enabled_and_global():
    matches = [source for source in GLOBAL_SOURCES if source.url == REFERENCE_URL]
    assert len(matches) == 1
    assert matches[0].enabled is True
    # No region restriction: this source can contribute nodes from anywhere.
    assert matches[0].region is None
