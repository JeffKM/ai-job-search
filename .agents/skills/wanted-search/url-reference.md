# Wanted (원티드) API Reference

Base URL: `https://www.wanted.co.kr`

## Search

```
GET /api/chaos/navigation/v1/results
```

| Parameter | Description |
|-----------|-------------|
| `country` | `kr` (South Korea) |
| `query` | Keyword search |
| `years` | `-1` (all experience levels) |
| `locations` | `all` or a location key (e.g. `seoul`) |
| `job_sort` | `job.latest_order` (newest first) |
| `limit` | Page size (max 100) |
| `offset` | Pagination offset |

Response: `{ "data": [ { "id", "position", "company": { "name" }, "address": { "location", "district" } } ] }`

Job URL pattern: `https://www.wanted.co.kr/wd/{id}`

## Detail

```
GET /api/chaos/jobs/v4/{id}/details
```

Response fields used: `data.job.detail` (position, intro, main_tasks, requirements, preferred_points, benefits), `data.job.due_time`, `data.job.company.name`, `data.job.address`.

Official OpenAPI (requires key): https://openapi.wanted.jobs/

## Notes

- CloudFront may block bare curl without a browser User-Agent.
- The public navigation API does not expose posting dates in search results.
- When `--query` is set, results are also filtered client-side on title/company.
