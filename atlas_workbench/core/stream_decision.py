"""Stream-vs-cache decision engine.

Two entry points:
  * make_stream_decision(total_bytes, cache_min_bytes, max_cache_bytes)
    — pure function used in unit tests and by the high-level wrapper.
  * decide_stream_vs_cache(subset_plan)
    — convenience wrapper that applies project-level thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# 10 GiB — files larger than this are always streamed
MAX_CACHE_SIZE_BYTES: int = 10 * 1024 * 1024 * 1024
# 1 MiB — files smaller than this are not worth caching
MIN_CACHE_SIZE_BYTES: int = 1 * 1024 * 1024
CACHE_DIR: str = "/tmp/atlas_cache"  # nosec B108


class ReasonCode(str, Enum):
    BELOW_CACHE_THRESHOLD = "BELOW_CACHE_THRESHOLD"
    ABOVE_CACHE_THRESHOLD = "ABOVE_CACHE_THRESHOLD"
    BELOW_MIN_CACHE_THRESHOLD = "BELOW_MIN_CACHE_THRESHOLD"
    CACHE_ENABLED = "CACHE_ENABLED"


@dataclass
class StreamCacheDecision:
    cache_on: bool
    protocol: str
    cache_location: str | None
    max_cache_size_bytes: int
    reason_codes: list[ReasonCode] = field(default_factory=list)


def make_stream_decision(
    total_bytes: int,
    cache_min_bytes: int,
    max_cache_bytes: int,
) -> StreamCacheDecision:
    """Pure decision function: no I/O, no network.

    Rules
    -----
    * total_bytes < cache_min_bytes  → stream (too small to bother caching)
    * cache_min_bytes <= total_bytes <= max_cache_bytes  → cache
    * total_bytes > max_cache_bytes  → stream (too large for local cache)
    """
    if total_bytes < cache_min_bytes:
        return StreamCacheDecision(
            cache_on=False,
            protocol="root",
            cache_location=None,
            max_cache_size_bytes=max_cache_bytes,
            reason_codes=[ReasonCode.BELOW_MIN_CACHE_THRESHOLD],
        )
    if total_bytes <= max_cache_bytes:
        return StreamCacheDecision(
            cache_on=True,
            protocol="root",
            cache_location=CACHE_DIR,
            max_cache_size_bytes=max_cache_bytes,
            reason_codes=[ReasonCode.BELOW_CACHE_THRESHOLD, ReasonCode.CACHE_ENABLED],
        )
    return StreamCacheDecision(
        cache_on=False,
        protocol="root",
        cache_location=None,
        max_cache_size_bytes=max_cache_bytes,
        reason_codes=[ReasonCode.ABOVE_CACHE_THRESHOLD],
    )


def decide_stream_vs_cache(total_size_bytes: int) -> StreamCacheDecision:
    """Apply project-level thresholds to produce a stream/cache decision."""
    return make_stream_decision(
        total_bytes=total_size_bytes,
        cache_min_bytes=MIN_CACHE_SIZE_BYTES,
        max_cache_bytes=MAX_CACHE_SIZE_BYTES,
    )
