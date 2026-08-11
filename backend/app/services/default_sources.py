from __future__ import annotations

from app.services.source_registry import SourceConfig


# East-Asia-focused feeds from the public FastNodes collection. FastNodes
# documents country-specific raw URI feeds and refreshes its collection
# periodically; NodePilot still performs its own endpoint checks.
ASIA_SOURCES = [
    SourceConfig(
        url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/JP.txt",
        region="JP",
    ),
    SourceConfig(
        url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/HK.txt",
        region="HK",
    ),
    SourceConfig(
        url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/SG.txt",
        region="SG",
    ),
    SourceConfig(
        url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/KR.txt",
        region="KR",
    ),
    SourceConfig(
        url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/TW.txt",
        region="TW",
    ),
]
