import pytest

from app.services.measurement import Measurement, merge_measurements
from app.services.quality import quality_score


def test_measurement_validation():
    with pytest.raises(ValueError):
        Measurement(-1, 10, 0, 100)
    with pytest.raises(ValueError):
        Measurement(50, 10, 101, 100)


def test_merge_uses_median():
    result = merge_measurements([
        Measurement(60, 50, 1, 98),
        Measurement(70, 60, 2, 99),
        Measurement(500, 1, 50, 20),
    ])
    assert result == Measurement(70, 50, 2, 98)


def test_quality_score_fast_stable_candidate():
    result = quality_score(Measurement(60, 80, 0.5, 99))
    assert result.eligible is True
    assert result.score > 85


def test_quality_score_rejects_slow_candidate():
    result = quality_score(Measurement(301, 100, 0, 100))
    assert result.eligible is False
    assert result.reason == "latency_above_300ms"
