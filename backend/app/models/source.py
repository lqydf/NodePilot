from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class NodeSource:
    """A public/authorized source that can provide node text."""

    source_id: str
    name: str
    url: str
    enabled: bool = True
    region_hint: Optional[str] = None
