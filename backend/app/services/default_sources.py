from __future__ import annotations

from app.services.source_registry import SourceConfig


# Publicly documented raw URI feed. The source itself says its Asia feed is
# composed of live V2Ray/Xray configurations and is refreshed periodically.
# NodePilot still performs its own endpoint checks before publishing results.
ASIA_SOURCES = [
    SourceConfig(
        url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/continents/Asia.txt",
        region="ASIA",
    )
]
