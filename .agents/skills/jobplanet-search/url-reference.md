# JobPlanet (잡플래닛) — Scrapling fetch reference

Base URL: `https://www.jobplanet.co.kr`

## Why Scrapling

Plain HTTP (`fetch`/curl) often receives Cloudflare challenge pages. This skill uses
Scrapling `StealthyFetcher` (Chromium) via `fetch/fetch.py`.

## Search (browser page)

```
GET /job/search?keyword={query}&page={page}
```

The response HTML embeds a dehydrated JSON payload containing:

```json
"jobs": [
  {
    "id": 1500010,
    "jd": {
      "title": "...",
      "cities": ["서울"],
      "created_at": "...",
      "end_at": "...",
      "url": "/companies/{company_id}/job_postings/{id}/..."
    },
    "company": { "name": "...", "id": ... }
  }
]
```

Extraction: bracket-match the array after `"jobs":` in HTML.

The portal may not always honour `keyword` server-side; `fetch.py` also filters client-side
on title, company, occupations, and skills.

## Detail

```
GET /job/search?posting_ids[]={id}
```

Fields used: `jd.title`, `company.name`, `jd.cities`, `description`, `primary_responsibility`,
`required_qualification`, `preferred_skill`, `end_at`, plus schema.org `JobPosting` JSON-LD fallback.

## Setup (repo venv)

```bash
cd .agents/skills/jobplanet-search/cli
bun run setup
```

Creates `fetch/.venv`, installs `scrapling[fetchers]`, runs `scrapling install` (Playwright browser).

## Notes

- Typical fetch latency: 15–30s (browser startup).
- Keep volume low — personal job search only.
- `.venv/` is gitignored; `requirements.txt` is the source of truth.
