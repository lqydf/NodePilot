from __future__ import annotations

import base64
import json
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

    # One production scan: fetch every source, globally deduplicate, TCP prefilter,
    # then real-proxy-test the shared pool. This avoids testing the same node once
    # per source and makes TOP10 a genuinely global ranking.
    result = run_once(
        urls,
        region_by_url=region_by_url,
        limit=10,
        timeout=3.0,
        max_candidates=1000,
        workers=32,
        real_proxy_limit=150,
    )

    final_quality = list(result["ranked"])
    published = _select_global_top10(final_quality, limit=10)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "generated_at": timestamp,
        "status": "proxy_verified" if published else "no_verified_nodes",
        "final_quality_ranking": published,
        "top10": published,
        "summary": {
            "source_count": len(result["sources"]),
            "candidates": int(result["candidates"]),
            "reachable": int(result["reachable"]),
            "proxy_verified": int(result["proxy_verified"]),
            "youtube_verified": int(result["youtube_verified"]),
            "published": len(published),
            "proxy_errors": dict(result.get("proxy_errors", Counter())),
        },
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUB_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Shadowrocket-style subscription: the client fetches this URL and receives
    # a base64-encoded newline-delimited server list. Credentials stay out of
    # live.json and are exposed only through the subscription endpoint itself.
    uris = [uri for uri in result.get("subscription_uris", []) if uri]
    encoded = base64.b64encode(("\n".join(uris) + ("\n" if uris else "")).encode()).decode()
    SUB_FILE.write_text(encoded + "\n", encoding="ascii")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
