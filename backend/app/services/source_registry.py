from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """A user-configured public text source."""

    url: str
    region: str | None = None
    enabled: bool = True


def enabled_urls(sources: list[SourceConfig]) -> list[str]:
    """Return enabled HTTP(S) source URLs in stable order without duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for source in sources:
        url = source.url.strip()
        if not source.enabled or not url:
            continue
        if not (url.startswith("https://") or url.startswith("http://")):
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append(url)
    return result
