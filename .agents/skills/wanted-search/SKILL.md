---
name: wanted-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search for jobs in South Korea on
  Wanted (원티드), find Korean startup/tech job listings, or look up a specific
  Wanted posting. Trigger for 채용, 구인, 채용공고, 원티드, wanted.co.kr, IT jobs
  Korea, developer jobs Seoul, startup jobs Korea, 백엔드 채용, 프론트엔드 채용,
  데이터 채용, 서울 채용, 판교 채용.
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/wanted-search/cli/src/cli.ts *)
---

# Wanted Search Skill

Search live job listings from [Wanted (원티드)](https://www.wanted.co.kr) for the
South Korean market. No authentication and **zero runtime dependencies** — runs with
just `bun`.

## ⚠️ Personal use only

Uses Wanted's public JSON endpoints. Keep request volume low and do not use for bulk
data collection or commercial scraping. Run on your own responsibility.

## Commands

### Search

```bash
bun run .agents/skills/wanted-search/cli/src/cli.ts search [flags]
```

- `--query, -q` — keywords (title, skill, role)
- `--location, -l` — location key (`seoul`, `all`, …). Default: `all`
- `--page` — 1-indexed page (default 1)
- `--limit, -n` — cap results (default 20)
- `--company-type, -t` — `major` | `enterprise-1000` | `mid` | `sme` | `startup` | `foreign` | `public` | `kospi` | `kosdaq` (client-side heuristics)
- `--format` — `json` (default) | `table` | `plain`

### Detail

```bash
bun run .agents/skills/wanted-search/cli/src/cli.ts detail <id|url> [--format json|plain]
```

## Examples

```bash
# Backend roles in Korea
bun run .agents/skills/wanted-search/cli/src/cli.ts search -q "백엔드" --format table

# Python developer, Seoul area
bun run .agents/skills/wanted-search/cli/src/cli.ts search -q "python" -l seoul --limit 10

# Full posting text
bun run .agents/skills/wanted-search/cli/src/cli.ts detail 376430 --format plain
```

## Output shape

Search JSON: `{ "meta": { "count", "page" }, "results": [ { "id", "title", "company", "location", "date", "url" } ] }`

Missing fields are `null`. See `url-reference.md` for endpoint details.
