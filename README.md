# NodePilot

NodePilot is a network-node discovery and quality monitoring platform for Asia-focused users.

## V1 goals

- Collect node data only from public/authorized sources.
- Normalize and deduplicate node records.
- Measure latency, packet loss, throughput, and availability.
- Rank candidates for video-streaming use cases.
- Generate a TOP 10 result from measured candidates.

> This repository currently contains the V1 scoring foundation. Source collection and active network testing will be added only with appropriate authorization and rate limits.

## Repository structure

```text
NodePilot/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   └── tests/
├── docs/
└── scripts/
```

## Run tests

```bash
cd backend
python -m pytest
```
