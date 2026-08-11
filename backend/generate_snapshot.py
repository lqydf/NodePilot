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


def _select_diverse_top10(items: list[dict[str, object]], *, limit: int = 10, per_region: int = 3) -> list[dict[str, object]]:
    """Prefer low latency while preventing one source region from filling the list."""
    ordered = sorted(items, key=lambda item: (float(item["latency_ms"]), str(item["node_id"])))
    selected: list[dict[str, object]] = []
    counts: dict[str, int] = {}

    for item in ordered:
        region = str(item.get("region") or "UNKNOWN")
        if counts.get(region, 0) >= per_region:
            continue
        selected.append(item)
        counts[region] = counts.get(region, 0) + 1
        if len(selected) == limit:
            break

    if len(selected) < limit:
        chosen = {str(item["node_id"]) for item in selected}
        for item in ordered:
            if str(item["node_id"]) in chosen:
                continue
            selected.append(item)
            if len(selected) == limit:
                break

    for rank, item in enumerate(selected, start=1):
        item["rank"] = rank
    return selected


def main() -> None:
    sources = [source for source in ASIA_SOURCES if source.enabled]
    urls = enabled_urls(sources)
    region_by_url = {source.url.strip(): source.region for source in sources if source.region}

    all_reachable: list[dict[str, object]] = []
    source_results: list[dict[str, object]] = []
    final_quality: list[dict[str, object]] = []

    # Scan each East-Asia source independently so one large country feed cannot
    # consume the global candidate budget before other regions are considered.
    for url in urls:
        result = run_once(
            [url],
            region_by_url=region_by_url,
            limit=10,
            timeout=3.0,
            max_candidates=400,
            workers=32,
        )
        source_results.extend(result["sources"])
        all_reachable.extend(result["reachable_ranked"])
        final_quality.extend(result["ranked"])

    published = _select_diverse_top10(all_reachable, limit=10, per_region=3)

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "generated_at": timestamp,
        "status": "tcp_reachable",
        "final_quality_ranking": final_quality[:10],
        "top10": published,
        "summary": {
            "source_count": len(source_results),
            "candidates": sum(int(result["node_count"]) for result in source_results),
            "reachable": len(all_reachable),
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
