---
name: jobkorea-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search for jobs in South Korea on
  JobKorea (잡코리아), find Korean corporate job listings, or look up a JobKorea
  posting. Trigger for 잡코리아, jobkorea.co.kr, 채용, 구인, 채용공고, 대기업 채용,
  IT 채용, 개발자 채용, 서울 채용, jobs Korea.
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/jobkorea-search/cli/src/cli.ts *)
---

# JobKorea Search Skill

Search live job listings from [JobKorea (잡코리아)](https://www.jobkorea.co.kr). No
authentication, zero runtime dependencies.

## ⚠️ Personal use only

Parses public HTML search pages. Keep volume low; do not bulk-scrape.

## Commands

```bash
bun run .agents/skills/jobkorea-search/cli/src/cli.ts search --query "<keywords>" [flags]
bun run .agents/skills/jobkorea-search/cli/src/cli.ts detail <gi_no|url> [--format json|plain]
```

Flags: `--query/-q` (required), `--page`, `--limit/-n`, `--company-type/-t` (`major`, `mid`, `sme`, `startup`, `foreign`, `public`, …), `--format json|table|plain`

## Examples

```bash
bun run .agents/skills/jobkorea-search/cli/src/cli.ts search -q "python" --format table
bun run .agents/skills/jobkorea-search/cli/src/cli.ts search -q "DevOps" --limit 15
bun run .agents/skills/jobkorea-search/cli/src/cli.ts detail 49546039 --format plain
```

See `url-reference.md` for HTML parsing anchors.
