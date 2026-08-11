from app.services.live_pipeline import run_live_pipeline


def test_live_pipeline_wires_fetch_parse_probe_and_rank(monkeypatch):
    class FetchResult:
        ok = True
        text = "vless://user@example.com:443#one"
        error = None

    class ProbeResult:
        connected = True
        latency_ms = 42.0
        error = None

    monkeypatch.setattr("app.services.live_pipeline.fetch_source", lambda url, timeout: FetchResult())
    monkeypatch.setattr("app.services.live_pipeline.probe", lambda host, port, timeout: ProbeResult())

    result = run_live_pipeline(["https://example.com/nodes"], region="JP")

    assert result.candidates == 1
    assert result.reachable == 1
    assert len(result.ranked) == 0  # no throughput measurement yet
    assert result.sources[0].fetched is True
    assert result.sources[0].node_count == 1


def test_live_pipeline_records_source_failure(monkeypatch):
    class FetchResult:
        ok = False
        text = ""
        error = "timeout"

    monkeypatch.setattr("app.services.live_pipeline.fetch_source", lambda url, timeout: FetchResult())

    result = run_live_pipeline(["https://example.com/nodes"])

    assert result.candidates == 0
    assert result.reachable == 0
    assert result.ranked == []
    assert result.sources[0].fetched is False
    assert result.sources[0].error == "timeout"
