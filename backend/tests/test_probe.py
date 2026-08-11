from app.services.probe import ProbeResult, tcp_probe


def test_probe_rejects_invalid_input():
    for args in [("", 443), ("example.com", 0), ("example.com", 65536)]:
        try:
            tcp_probe(*args)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input should raise ValueError")


def test_probe_result_shape():
    result = ProbeResult("example.com", 443, True, 12.5)
    assert result.connected is True
    assert result.latency_ms == 12.5
    assert result.error is None


def test_probe_failure_is_structured():
    result = tcp_probe("invalid.invalid", 443, timeout_s=0.1)
    assert result.connected is False
    assert result.latency_ms is None
    assert result.error
