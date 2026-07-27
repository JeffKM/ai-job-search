---
name: saramin-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search for jobs in South Korea on
  Saramin (사람인), find Korean job listings, or look up a Saramin posting.
  Trigger for 사람인, saramin.co.kr, 채용, 구인, 채용공고, 백엔드 채용, 개발자 채용,
  서울 채용, 경력 채용, 신입 채용, jobs Korea.
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/saramin-search/cli/src/cli.ts *)
---

# Saramin Search Skill

Search live job listings from [Saramin (사람인)](https://www.saramin.co.kr). No
authentication, zero runtime dependencies.

## ⚠️ Personal use only

Parses public HTML search pages. Keep volume low; do not bulk-scrape.

## Commands

```bash
bun run .agents/skills/saramin-search/cli/src/cli.ts search --query "<keywords>" [flags]
bun run .agents/skills/saramin-search/cli/src/cli.ts detail <rec_idx|url> [--format json|plain]
```

Flags: `--query/-q` (required), `--page`, `--limit/-n`, `--company-type/-t` (native `company_type[]` on Saramin — e.g. `major` → `scale001`), `--format json|table|plain`

## Examples

```bash
bun run .agents/skills/saramin-search/cli/src/cli.ts search -q "python" --format table
bun run .agents/skills/saramin-search/cli/src/cli.ts search -q "데이터 엔지니어" --page 2
bun run .agents/skills/saramin-search/cli/src/cli.ts detail 54519167 --format plain
```

See `url-reference.md` for HTML parsing anchors.
