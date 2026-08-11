from __future__ import annotations

import socket
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """A transport-level probe result for an endpoint the operator is allowed to test."""

    host: str
    port: int
    connected: bool
    latency_ms: float | None
    error: str | None = None


def tcp_probe(host: str, port: int, *, timeout_s: float = 3.0) -> ProbeResult:
    """Measure TCP connection setup time without speaking the application protocol.

    This intentionally performs only a basic TCP connect. It does not authenticate,
    relay traffic, or attempt to bypass network controls.
    """
    if not host or not host.strip():
        raise ValueError("host is required")
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")

    started = time.perf_counter()
    try:
        with socket.create_connection((host.strip(), port), timeout=timeout_s):
            elapsed_ms = (time.perf_counter() - started) * 1000
            return ProbeResult(host.strip(), port, True, round(elapsed_ms, 2))
    except OSError as exc:
        return ProbeResult(host.strip(), port, False, None, type(exc).__name__)
