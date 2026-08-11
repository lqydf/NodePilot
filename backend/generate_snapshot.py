from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.default_sources import ASIA_SOURCES
from app.services.runner import run_once
from app.services.source_registry import enabled_urls

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DATA_FILE = FRONTEND / "data" / "live.json"
SUB_FILE = FRONTEND / "sub" / "top10.txt"


def main() -> None:
    sources = [source for source in ASIA_SOURCES if source.enabled]
    urls = enabled_urls(sources)
    region_by_url = {source.url.strip(): source.region for source in sources if source.region}
    result = run_once(
        urls,
        region_by_url=region_by_url,
        limit=10,
        timeout=3.0,
        max_candidates=1000,
        workers=32,
    )

    ranked = result["ranked"]
    reachable = result["reachable_ranked"]
    # Until protocol-aware throughput testing exists, only publish TCP-reachable
    # candidates and label them honestly. They are not yet YouTube-verified.
    published = reachable

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "generated_at": timestamp,
        "status": "tcp_reachable",
        "final_quality_ranking": ranked,
        "top10": published,
        "summary": {
            "source_count": len(result["sources"]),
            "candidates": result["candidates"],
            "reachable": result["reachable"],
            "published": len(published),
        },
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUB_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    uris = [item["source_uri"] for item in published if item.get("source_uri")]
    encoded = base64.b64encode(("\n".join(uris) + ("\n" if uris else "")).encode()).decode()
    SUB_FILE.write_text(encoded + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
