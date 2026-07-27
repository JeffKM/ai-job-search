---
name: jobplanet-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search for jobs on JobPlanet (잡플래닛),
  find Korean job listings with company reviews, or look up a JobPlanet posting.
  Trigger for 잡플래닛, jobplanet.co.kr, 채용, 기업리뷰 채용, python 채용, 백엔드 채용,
  서울 채용, IT 채용 Korea.
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/jobplanet-search/cli/src/cli.ts *)
---

# JobPlanet Search Skill

Search live job listings from [JobPlanet (잡플래닛)](https://www.jobplanet.co.kr). Uses
**Scrapling** (Python + Chromium) to fetch pages behind Cloudflare, then a **bun CLI**
wrapper for the standard portal-skill contract.

## Setup (once per clone)

```bash
cd .agents/skills/jobplanet-search/cli
bun install
bun run setup
```

This creates `fetch/.venv` with `scrapling[fetchers]` and installs the browser via
`scrapling install`.

## ⚠️ Personal use only

Browser automation against a protected site — keep volume low (handful of requests per
`/scrape` run). Not for bulk or commercial scraping.

## Commands

```bash
bun run .agents/skills/jobplanet-search/cli/src/cli.ts search --query "<keywords>" [flags]
bun run .agents/skills/jobplanet-search/cli/src/cli.ts detail <posting_id|url> [--format json|plain]
```

Flags: `--query/-q` (required), `--page`, `--limit/-n`, `--max-pages` (default 5; client-side keyword filter scans multiple pages), `--company-type/-t` (client-side heuristics), `--format json|table|plain`

**Note:** JobPlanet often ignores the `keyword` URL param; matching is done client-side on title, company, occupations, and skills. Each fetch takes ~15–30s (Chromium).

## Examples

```bash
bun run .agents/skills/jobplanet-search/cli/src/cli.ts search -q "python" --format table
bun run .agents/skills/jobplanet-search/cli/src/cli.ts search -q "백엔드" --limit 5
bun run .agents/skills/jobplanet-search/cli/src/cli.ts detail 1500010 --format plain
```

## Architecture

| Layer | Role |
|-------|------|
| `fetch/fetch.py` | Scrapling StealthyFetcher + HTML JSON extraction |
| `fetch/.venv` | Repo-local Python deps (gitignored) |
| `cli/src/cli.ts` | Portal-skill CLI contract (`search` / `detail`) |

See `url-reference.md` for parsing anchors.
