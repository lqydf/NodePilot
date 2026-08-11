from __future__ import annotations

import argparse

from app.services.runner import run_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one NodePilot live scan")
    parser.add_argument("urls", nargs="+", help="public text node-source URLs")
    parser.add_argument("--region", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    result = run_once(
        args.urls,
        region=args.region,
        limit=args.limit,
        timeout=args.timeout,
    )

    print("NodePilot Live Scan")
    print("=" * 40)
    for source in result["sources"]:
        status = "OK" if source["fetched"] else "FAILED"
        suffix = f" - {source['error']}" if source["error"] else ""
        print(f"{status:>6}  {source['url']}  nodes={source['node_count']}{suffix}")
    print()
    print(f"Candidates: {result['candidates']}")
    print(f"Reachable:  {result['reachable']}")
    print()
    print("TOP 10")
    if not result["ranked"]:
        print("No eligible nodes yet (throughput measurement is not enabled in this MVP).")
        return
    for item in result["ranked"]:
        print(
            f"{item['rank']:>2}. {item['region'] or '-':<4} "
            f"{item['latency_ms']:>7.1f} ms  score={item['score']:>6.2f}  {item['node_id']}"
        )


if __name__ == "__main__":
    main()
