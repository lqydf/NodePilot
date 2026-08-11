from __future__ import annotations

import time
from collections.abc import Iterable


def measure_download_mbps(chunks: Iterable[bytes], *, started_at: float | None = None, finished_at: float | None = None) -> float:
    """Calculate throughput from an already-authorized byte stream.

    This function deliberately does not establish proxy connections or choose a
    remote target. The caller supplies the byte stream from an approved test
    adapter, which keeps measurement separate from transport/protocol logic.
    """
    start = time.perf_counter() if started_at is None else started_at
    total_bytes = sum(len(chunk) for chunk in chunks)
    end = time.perf_counter() if finished_at is None else finished_at
    elapsed = end - start
    if elapsed <= 0:
        raise ValueError("measurement duration must be positive")
    if total_bytes < 0:
        raise ValueError("byte count cannot be negative")
    return round((total_bytes * 8) / elapsed / 1_000_000, 3)
