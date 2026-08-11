import pytest

from app.services.throughput import measure_download_mbps


def test_throughput_calculation():
    chunks = [b"x" * 500_000, b"y" * 500_000]
    assert measure_download_mbps(chunks, started_at=10.0, finished_at=11.0) == 8.0


def test_throughput_handles_empty_stream():
    assert measure_download_mbps([], started_at=10.0, finished_at=11.0) == 0.0


def test_throughput_rejects_zero_duration():
    with pytest.raises(ValueError, match="duration"):
        measure_download_mbps([b"x"], started_at=10.0, finished_at=10.0)
