from __future__ import annotations

import base64
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.services.default_sources import GLOBAL_SOURCES
from app.services.runner import run_once
from app.services.source_registry import enabled_urls

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DATA_FILE = FRONTEND / "data" / "live.json"
SUB_FILE = FRONTEND / "sub" / "top10.txt"


def _select_global_top10(items: list[dict[str, object]], *, limit: int = 10) -> list[dict[str, object]]:
    """Select the globally best measured nodes without regional quotas."""
    ordered = sorted(
        items,
        key=lambda item: (
            -float(item.get("score", 0)),
            float(item.get("latency_ms", 999999)),
            str(item.get("node_id", "")),
        ),
    )
    selected = ordered[:limit]
    for rank, item in enumerate(selected, start=1):
        item["rank"] = rank
    return selected


def main() -> None:
    sources = [source for source in GLOBAL_SOURCES if source.enabled]
    urls = enabled_urls(sources)
    region_by_url = {source.url.strip(): source.region for source in sources if source.region}

    source_results: list[dict[str, object]] = []
    final_quality: list[dict[str, object]] = []
    reachable_count = 0
    proxy_errors: Counter[str] = Counter()

    # Scan each source independently so one large feed cannot consume the
    # entire global candidate budget before other regions are considered.
    for url in urls:
        result = run_once(
            [url],
            region_by_url=region_by_url,
            limit=10,
            timeout=3.0,
            max_candidates=400,
            workers=32,
            real_proxy_limit=60,
        )
        source_results.extend(result["sources"])
        reachable_count += int(result["reachable"])
        final_quality.extend(result["ranked"])
        proxy_errors.update(result.get("proxy_errors", {}))

    published = _select_global_top10(final_quality, limit=10)

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    real_proxy = os.environ.get("NODEPILOT_REAL_PROXY_TEST") == "1"
    payload = {
        "generated_at": timestamp,
        "status": "proxy_verified" if real_proxy and published else "no_verified_nodes" if real_proxy else "tcp_reachable",
        "final_quality_ranking": _select_global_top10(final_quality, limit=10),
        "top10": published,
        "summary": {
            "source_count": len(source_results),
            "candidates": sum(int(result["node_count"]) for result in source_results),
            "reachable": reachable_count,
            "proxy_verified": len(final_quality) if real_proxy else 0,
            "published": len(published),
            "proxy_errors": dict(proxy_errors),
        },
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUB_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    uris = [item["source_uri"] for item in published if item.get("source_uri")]
    encoded = base64.b64encode(("\n".join(uris) + ("\n" if uris else "")).encode()).decode()
    SUB_FILE.write_text(encoded + "\n", encoding="ascii")

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
