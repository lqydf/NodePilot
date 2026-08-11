from __future__ import annotations

from app.models.node import Node
from app.services.deduplicator import deduplicate
from app.services.parser import parse_text


def collect_from_text(text: str, *, region: str | None = None) -> list[Node]:
    """Convert already-obtained source text into unique normalized nodes.

    Network fetching is deliberately outside this function so future source
    adapters can enforce source permissions, rate limits, and robots/terms
    requirements independently.
    """
    return deduplicate(parse_text(text, region=region))
