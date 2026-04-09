"""Unit tests for make_stream_decision from stream_planner."""

from atlas_workbench.core.stream_planner import ReasonCode, make_stream_decision

_MIN = 1 * 1024 * 1024  # 1 MiB
_MAX = 10 * 1024 * 1024 * 1024  # 10 GiB


def test_below_min_cache_threshold_streams():
    result = make_stream_decision(total_bytes=_MIN - 1, cache_min_bytes=_MIN, max_cache_bytes=_MAX)
    assert result.cache_on is False
    assert ReasonCode.BELOW_MIN_CACHE_THRESHOLD in result.reason_codes


def test_within_cache_window_enables_cache():
    total = 100 * 1024 * 1024  # 100 MiB — between min and max
    result = make_stream_decision(total_bytes=total, cache_min_bytes=_MIN, max_cache_bytes=_MAX)
    assert result.cache_on is True
    assert result.cache_location is not None
    assert ReasonCode.CACHE_ENABLED in result.reason_codes


def test_above_max_cache_threshold_streams():
    total = _MAX + 1
    result = make_stream_decision(total_bytes=total, cache_min_bytes=_MIN, max_cache_bytes=_MAX)
    assert result.cache_on is False
    assert ReasonCode.ABOVE_CACHE_THRESHOLD in result.reason_codes
