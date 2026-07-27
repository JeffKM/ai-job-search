# Search Queries for Job Scraper

<!-- SETUP: Customize these queries based on your skills, target roles, and location -->

## Installed portal CLIs (primary for `/scrape`)

`/scrape` discovers every portal skill under `.agents/skills/*/SKILL.md` and runs its CLI first. Shipped country-agnostic CLIs include `linkedin-search` and `freehire-search`; Danish demos, Korean portals (`wanted-search`, `jobkorea-search`, `saramin-search`, `jobplanet-search`), and any skill you add with `/add-portal` are included the same way. You do **not** need a matching `site:` line below for those CLIs to run.

The `site:` query templates in this file are the **WebSearch fallback** — for portals without a CLI, company career pages, or when a CLI fails.

### Company-size filter (`--company-type`)

Installed Korean CLIs accept `--company-type` / `-t` on `search`:

| Value | Meaning |
|-------|---------|
| `major` | 대기업 |
| `enterprise-1000` | 매출 1000대 |
| `mid` | 중견 |
| `sme` | 중소 |
| `startup` | 스타트업 |
| `foreign` | 외국계 |
| `public` | 공기업 |
| `kospi` / `kosdaq` | 상장 (사람인 native) |

Example: `/scrape 백엔드 — 대기업만` → CLIs run with `--company-type major`. Saramin/JobKorea use native URL filters where possible; Wanted/JobPlanet/LinkedIn use client-side heuristics on company names.

## Search Sites

Primary (your market's job boards - scaffold one with `/add-portal`):
- **wanted.co.kr** - Wanted (원티드) startup/tech roles — `wanted-search` CLI
- **jobkorea.co.kr** - JobKorea (잡코리아) general/corporate — `jobkorea-search` CLI
- **saramin.co.kr** - Saramin (사람인) general/corporate — `saramin-search` CLI
- **linkedin.com/jobs** - LinkedIn job listings (filter: [YOUR_COUNTRY] / [YOUR_CITY]); also covered by `linkedin-search` CLI
- **jobplanet.co.kr** - JobPlanet (잡플래닛) + company reviews — `jobplanet-search` CLI (Scrapling; run `bun run setup` once)
- **[YOUR_ADDITIONAL_JOB_BOARD]** - another major board for your market (optional)

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for known target companies

## Query Categories

Queries are grouped by priority. Each query should be combined with your location terms (e.g. your city, region, or metro area) where the site supports it.

### Priority 1: [YOUR_PRIMARY_ROLE_TYPE]

These match your strongest and most desired career direction.

```
site:wanted.co.kr "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_CITY]
site:jobkorea.co.kr "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_CITY]
site:saramin.co.kr "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_CITY]
site:jobplanet.co.kr "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_COUNTRY]
```

### Priority 2: [YOUR_DOMAIN_EXPERTISE]

These match your domain expertise.

```
site:[YOUR_JOB_BOARD] [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY] OR [YOUR_REGION]
site:[YOUR_JOB_BOARD] [YOUR_DOMAIN_KEYWORD_2] [YOUR_COUNTRY]
site:linkedin.com/jobs [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY] [YOUR_COUNTRY]
```

### Priority 3: [YOUR_ADJACENT_ROLE_TYPE]

Adjacent roles you could pivot into.

```
site:[YOUR_JOB_BOARD] "[YOUR_ADJACENT_TITLE_1]" [YOUR_KEY_SKILL] [YOUR_CITY]
site:[YOUR_JOB_BOARD] "[YOUR_ADJACENT_TITLE_2]" [YOUR_KEY_SKILL] [YOUR_CITY]
```

### Priority 4: Broader Technical / Consulting

Wider net for general technical roles.

```
site:[YOUR_JOB_BOARD] [YOUR_KEY_SKILL] developer [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_KEY_SKILL] developer" [YOUR_CITY]
site:[YOUR_JOB_BOARD] "technical consultant" [YOUR_DOMAIN] [YOUR_CITY]
```

## Location Filter

When evaluating results, verify the job location is within reasonable commute distance from your home. Define acceptable areas:
- [YOUR_CITY] and surrounding areas
- [ACCEPTABLE_AREA_1]
- [ACCEPTABLE_AREA_2]
- [BORDERLINE_AREA] (borderline - ~X min by transit)
- [TOO_FAR_AREA] (too far)

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries
