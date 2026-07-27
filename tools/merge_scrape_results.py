#!/usr/bin/env python3
"""Merge portal CLI search JSON into job_scraper/seen_jobs.json.

Reads one or more CLI stdout JSON files (or stdin) shaped like:
  { "results": [ { "title", "company", "url", "location", "date", ... } ] }

New URLs are inserted with status=new and a simple keyword fit heuristic.
Existing keys are left untouched (dedup).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from job_field_enrichment import enrich_job_fields  # noqa: E402

DEFAULT_SEEN = REPO / "job_scraper" / "seen_jobs.json"

HIGH_KW = re.compile(
    r"개발|엔지니어|engineer|developer|데이터|data|백엔드|프론트|풀스택|"
    r"platform|인프라|devops|ml|ai|소프트웨어|software|기획(?!.*채용)",
    re.I,
)
LOW_KW = re.compile(
    r"채용\s*담당|recruiter|영업|sales|마케팅|marketing|회계|경리|"
    r"디자이너|design(?!er\s*system)|운전|경비|조리",
    re.I,
)


def guess_fit(title: str, company: str = "") -> str:
    text = f"{title} {company}"
    if LOW_KW.search(text) and not HIGH_KW.search(title):
        return "low"
    if HIGH_KW.search(text):
        return "high"
    return "medium"


def load_json_blob(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {}
    return json.loads(raw)


def collect_results(paths: list[Path], stdin_ok: bool) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for path in paths:
        data = load_json_blob(path.read_text(encoding="utf-8"))
        portal = path.stem.replace("_search", "-search")
        for item in data.get("results") or []:
            if isinstance(item, dict):
                out.append((portal, item))
    if stdin_ok and not sys.stdin.isatty():
        data = load_json_blob(sys.stdin.read())
        for item in data.get("results") or []:
            if isinstance(item, dict):
                out.append(("stdin", item))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", nargs="*", type=Path, help="CLI JSON output files")
    p.add_argument("--seen", type=Path, default=DEFAULT_SEEN)
    p.add_argument("--portal", default="", help="Override portal tag for all rows")
    p.add_argument("--today", default=date.today().isoformat())
    args = p.parse_args(argv)

    rows = collect_results(args.files, stdin_ok=True)
    if not rows:
        print("No results to merge.")
        return 0

    if args.seen.is_file():
        store = json.loads(args.seen.read_text(encoding="utf-8"))
    else:
        store = {"seen": {}}
    seen: dict[str, Any] = store.setdefault("seen", {})

    added = 0
    for portal_guess, item in rows:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        if url in seen:
            continue
        title = item.get("title") or ""
        company = item.get("company") or ""
        portal = args.portal or item.get("portal") or portal_guess
        entry: dict[str, Any] = {
            "title": title,
            "company": company,
            "url": url,
            "first_seen": args.today,
            "fit": guess_fit(title, company),
            "status": "new",
            "portal": portal,
        }
        if item.get("location"):
            entry["location"] = item["location"]
        if item.get("deadline"):
            entry["deadline"] = item["deadline"]
        elif item.get("date"):
            entry["posted"] = item["date"]
        entry.update(
            enrich_job_fields(
                title=title,
                description=item.get("description") or "",
                seniority_hint=item.get("seniority") or item.get("career"),
            )
        )
        seen[url] = entry
        added += 1

    args.seen.parent.mkdir(parents=True, exist_ok=True)
    args.seen.write_text(
        json.dumps(store, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Merged {added} new jobs (store size {len(seen)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
