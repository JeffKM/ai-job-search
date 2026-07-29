#!/usr/bin/env bash
# Daily KR major-company scrape → seen_jobs.json → Notion.
# Requires: bun, python3, NOTION_TOKEN (+ NOTION_PARENT_PAGE_ID on first run)
# Config: job_scraper/daily_config.json (optional; see daily_config.example.json)

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

LOG_DIR="${REPO}/job_scraper/logs"
TMP_DIR="${REPO}/job_scraper/tmp"
mkdir -p "$LOG_DIR" "$TMP_DIR"

TODAY="$(date +%F)"
LOG="${LOG_DIR}/daily_${TODAY}.log"
exec >>"$LOG" 2>&1
echo "===== daily_kr_notion_pipeline ${TODAY} $(date +%T) ====="

CONFIG="${REPO}/job_scraper/daily_config.json"
EXAMPLE="${REPO}/job_scraper/daily_config.example.json"
if [[ ! -f "$CONFIG" ]]; then
  echo "No daily_config.json — copying example defaults."
  cp "$EXAMPLE" "$CONFIG"
fi

# Load queries / company type via python (portable JSON; no bash mapfile — macOS bash 3.2)
QUERIES_FILE="${TMP_DIR}/queries_${TODAY}.txt"
python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("job_scraper/daily_config.json").read_text(encoding="utf-8"))
out = Path("job_scraper/tmp") / ("queries_" + __import__("datetime").date.today().isoformat() + ".txt")
out.write_text("\n".join(cfg.get("queries") or ["개발", "엔지니어", "데이터"]) + "\n", encoding="utf-8")
meta = Path("job_scraper/tmp") / "daily_meta.env"
meta.write_text(
    "COMPANY_TYPE={ct}\nFIT={fit}\nLIMIT={lim}\nINCLUDE_JOBPLANET={jp}\n".format(
        ct=cfg.get("company_type") or "major",
        fit=cfg.get("notion_fit") or "high,medium",
        lim=int(cfg.get("limit_per_query") or 20),
        jp="1" if cfg.get("include_jobplanet") else "0",
    ),
    encoding="utf-8",
)
PY
# shellcheck disable=SC1091
source "${TMP_DIR}/daily_meta.env"

PORTALS=(
  "saramin-search"
  "jobkorea-search"
  "wanted-search"
)

run_search() {
  local portal="$1" query="$2"
  local out="${TMP_DIR}/${portal}_${TODAY}_$(echo "$query" | tr ' /' '__').json"
  local cli=".agents/skills/${portal}/cli/src/cli.ts"
  if [[ ! -f "$cli" ]]; then
    echo "skip missing portal: $portal"
    return 0
  fi
  echo "→ $portal  q=$query  t=$COMPANY_TYPE"
  if bun run "$cli" search -q "$query" -t "$COMPANY_TYPE" -n "$LIMIT" --format json >"$out" 2>"${out}.err"; then
    python3 tools/merge_scrape_results.py --portal "$portal" "$out" || true
  else
    echo "WARN: $portal failed for '$query' (see ${out}.err)"
  fi
}

# launchd는 로그인 셸 PATH를 물려받지 않는다. bun을 흔한 설치 위치에서 직접 찾는다.
if ! command -v bun >/dev/null 2>&1; then
  for cand in \
    "$HOME/.bun/bin/bun" \
    /opt/homebrew/bin/bun \
    /usr/local/bin/bun \
    "$HOME"/.nvm/versions/node/*/bin/bun \
    "$HOME"/.local/share/pnpm/bun \
    "$HOME"/.volta/bin/bun
  do
    if [[ -x "$cand" ]]; then
      PATH="$(dirname "$cand"):$PATH"
      export PATH
      echo "found bun at $cand"
      break
    fi
  done
fi

if ! command -v bun >/dev/null 2>&1; then
  echo "ERROR: bun not found (PATH=$PATH)"
  exit 1
fi

while IFS= read -r q || [[ -n "$q" ]]; do
  [[ -z "$q" ]] && continue
  for portal in "${PORTALS[@]}"; do
    run_search "$portal" "$q"
    sleep 1
  done
done <"$QUERIES_FILE"

# Optional: JobPlanet (slow Scrapling). Enable via include_jobplanet in config.
if [[ "${INCLUDE_JOBPLANET:-0}" == "1" ]]; then
  while IFS= read -r q || [[ -n "$q" ]]; do
    [[ -z "$q" ]] && continue
    run_search "jobplanet-search" "$q"
  done <"$QUERIES_FILE"
fi

echo "→ Enrich seniority / role / stack (title + selective detail)"
python3 tools/enrich_seen_jobs.py --fetch-detail --fit "$FIT" --limit 80

echo "→ Notion sync (scraped-only fit=$FIT, 마감 지난 공고는 휴지통으로 정리)"
python3 tools/notion_sync_jobs.py --scraped-only --fit "$FIT"
echo "===== done $(date +%T) ====="
