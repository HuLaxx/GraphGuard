import math

import pytest

from ml.review.benchmark_local import summarize_latencies


def test_nearest_rank_bounded_p50_p95():
    samples = [float(i) for i in range(1, 21)]
    result = summarize_latencies(list(reversed(samples)))
    assert result == {
        "count": 20,
        "min_ms": 1.0,
        "p50_ms": 10.0,
        "p95_ms": 19.0,
        "max_ms": 20.0,
    }


@pytest.mark.parametrize("durations", [[], [-1], [float("nan")], [math.inf]])
def test_nonfinite_and_invalid_durations_fail_closed(durations):
    with pytest.raises(ValueError):
        summarize_latencies(durations)


def test_single_sample_p50_and_p95_use_observation():
    value = summarize_latencies([0.301])
    assert value["p50_ms"] == value["p95_ms"] == 0.301
