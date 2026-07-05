# Prototype Benchmark Results

## EXP-001 — Express Baseline

| Metric | Value |
|--------|------:|
| Base Image | node:22 |
| Initial Build Time | 9.01 s |
| Cached Rebuild Time | 3.34 s |
| Image Size | (fill from `docker images`) |
| Status | ✅ Passed |

### Observations

- Docker layer caching reduced rebuild time significantly.
- Application started successfully.
- All endpoints responded correctly.