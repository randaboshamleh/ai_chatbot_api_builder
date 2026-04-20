# Performance Test Results (Actual Run)

Date: 2026-04-20  
Tool: Locust 2.43.4  
Command:

```bash
python -m locust -f tests/performance/locustfile.py \
  --headless -u 5 -r 1 -t 20s \
  --host http://127.0.0.1:8000 \
  --csv tests/performance/locust-results-local \
  --html tests/performance/locust-report-local.html \
  --exit-code-on-error 0
```

## Summary

- Total requests: `44`
- Total failures: `0`
- Average response time: `9.63 ms`
- Median response time: `5 ms`
- p95 response time: `42 ms`
- Throughput: `2.39 req/s`

## Endpoint Breakdown

| Endpoint | Requests | Failures | Avg (ms) |
|---|---:|---:|---:|
| `List Documents` | 25 | 0 | 6 |
| `Get Analytics` | 8 | 0 | 13 |
| `Chat Query (RAG)` | 7 | 0 | 19 |
| `Upload Document` | 4 | 0 | 4 |

## Notes

- This run validates performance-test infrastructure and baseline latency in local CI settings.
- Artifacts generated:
  - `tests/performance/locust-report-local.html`
  - `tests/performance/locust-results-local_*.csv`
