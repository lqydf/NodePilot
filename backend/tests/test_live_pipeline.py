from app.services.live_pipeline import run_live_pipeline
from app.services.source_fetcher import SourceFetchError


def test_live_pipeline_wires_fetch_parse_probe_and_rank(monkeypatch):
    monkeypatch.setattr(
        "app.services.live_pipeline.fetch_text_source",
        lambda url, timeout: "vless://user@example.com:443#one",
    )

    class ProbeResult:
        connected = True
        latency_ms = 42.0
        error = None

    monkeypatch.setattr(
        "app.services.live_pipeline.tcp_probe",
        lambda host, port, timeout_s: ProbeResult(),
    )

    result = run_live_pipeline(["https://example.com/nodes"], region="JP")

    assert result.candidates == 1
    assert result.reachable == 1
    assert len(result.ranked) == 0  # no throughput measurement yet
    assert result.sources[0].fetched is True
    assert result.sources[0].node_count == 1


def test_live_pipeline_records_source_failure(monkeypatch):
    def fail_fetch(url, timeout):
        raise SourceFetchError("timeout")

    monkeypatch.setattr("app.services.live_pipeline.fetch_text_source", fail_fetch)

    result = run_live_pipeline(["https://example.com/nodes"])

    assert result.candidates == 0
    assert result.reachable == 0
    assert result.ranked == []
    assert result.sources[0].fetched is False
    assert result.sources[0].error == "timeout"
