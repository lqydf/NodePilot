from __future__ import annotations

from app.services.source_registry import SourceConfig


# Global public feeds. Region is metadata only; it never excludes a node from
# ranking. The product target is now China users: global nodes remain eligible,
# but the verification/ranking policy is explicitly optimized for Chinese users.
GLOBAL_SOURCES = [
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/JP.txt", region="JP"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/HK.txt", region="HK"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/SG.txt", region="SG"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/KR.txt", region="KR"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/TW.txt", region="TW"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/US.txt", region="US"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/CA.txt", region="CA"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/GB.txt", region="GB"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/DE.txt", region="DE"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/NL.txt", region="NL"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/FR.txt", region="FR"),
    SourceConfig(url="https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/countries/AU.txt", region="AU"),
    SourceConfig(url="https://raw.githubusercontent.com/wiki/gfpcom/free-proxy-list/lists/vless.txt", region=None),
    SourceConfig(url="https://raw.githubusercontent.com/wiki/gfpcom/free-proxy-list/lists/vmess.txt", region=None),
    SourceConfig(url="https://raw.githubusercontent.com/wiki/gfpcom/free-proxy-list/lists/trojan.txt", region=None),
    SourceConfig(url="https://raw.githubusercontent.com/wiki/gfpcom/free-proxy-list/lists/ss.txt", region=None),
]

# Backward-compatible alias for older imports.
ASIA_SOURCES = GLOBAL_SOURCES
