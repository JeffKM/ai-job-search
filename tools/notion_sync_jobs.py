#!/usr/bin/env python3
"""One-way sync of seen_jobs.json (+ optional tracker) into a Notion database.

Designed for unattended daily runs (cron / launchd). Prefer this over Notion MCP
when OAuth cannot run headless.

Credentials (never commit):
  NOTION_TOKEN              Integration secret (ntn_... or secret_...)
  NOTION_PARENT_PAGE_ID     Page to create the DB under (first run only)
  NOTION_DATABASE_ID        Optional; otherwise read/written via notion_sync.json

Env files loaded if present (later files override earlier):
  .env
  .env.local
  job_scraper/notion.env

Usage:
  python3 tools/notion_sync_jobs.py --include-new --fit high,medium
  python3 tools/notion_sync_jobs.py --scraped-only --fit high
  python3 tools/notion_sync_jobs.py --min-score 60
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from job_field_enrichment import ROLE_OPTIONS, SENIORITY_OPTIONS  # noqa: E402

SEEN_PATH = REPO / "job_scraper" / "seen_jobs.json"
TRACKER_PATH = REPO / "job_search_tracker.csv"
STATE_PATH = REPO / "job_scraper" / "notion_sync.json"
NOTION_VERSION = "2022-06-28"
DB_TITLE = "Job Search Pipeline"

STATUS_OPTIONS = [
    "new",
    "ranked",
    "skipped",
    "applied",
    "interview",
    "offer",
    "hired",
    "rejected",
    "no response",
    "withdrawn",
    "expired",
]
VERDICT_OPTIONS = [
    "Strong Fit",
    "Good Fit",
    "Moderate Fit",
    "Weak Fit",
    "Poor Fit",
]
FIT_OPTIONS = ["high", "medium", "low"]


def load_dotenv_files() -> None:
    for path in (REPO / ".env", REPO / ".env.local", REPO / "job_scraper" / "notion.env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = val


def notion_request(
    method: str,
    path: str,
    token: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"https://api.notion.com/v1{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API {method} {path} → {e.code}: {detail}") from e


def rich_text(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    text = str(value)[:2000]
    return [{"type": "text", "text": {"content": text}}]


def title_prop(value: str) -> dict[str, Any]:
    return {"title": rich_text(value)}


def rich_prop(value: str | None) -> dict[str, Any]:
    return {"rich_text": rich_text(value)}


def select_prop(value: str | None) -> dict[str, Any]:
    if not value:
        return {"select": None}
    return {"select": {"name": str(value)}}


def multi_select_prop(values: Any) -> dict[str, Any]:
    if not values:
        return {"multi_select": []}
    if isinstance(values, str):
        values = [v.strip() for v in values.split(",") if v.strip()]
    names = []
    for v in values:
        name = str(v).strip()
        if name and name not in names:
            names.append(name)
    return {"multi_select": [{"name": n[:100]} for n in names[:20]]}


def number_prop(value: Any) -> dict[str, Any]:
    if value is None or value == "":
        return {"number": None}
    try:
        return {"number": float(value)}
    except (TypeError, ValueError):
        return {"number": None}


def date_prop(value: str | None) -> dict[str, Any]:
    iso = normalize_date(value)
    if not iso:
        return {"date": None}
    return {"date": {"start": iso}}


def url_prop(value: str | None) -> dict[str, Any]:
    if not value:
        return {"url": None}
    return {"url": str(value)}


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if not s or s in ("상시채용", "채용시마감", "마감일 없음", "-", "—"):
        return None
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # YYYY.MM.DD or YYYY/MM/DD
    m = re.match(r"^(\d{4})[./](\d{1,2})[./](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # YYYYMMDD
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def score_to_verdict(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 85:
        return "Strong Fit"
    if score >= 70:
        return "Good Fit"
    if score >= 55:
        return "Moderate Fit"
    if score >= 40:
        return "Weak Fit"
    return "Poor Fit"


def job_key(url_or_key: str, company: str = "", title: str = "") -> str:
    if url_or_key.startswith("http"):
        return url_or_key
    base = f"{company}_{title}".lower()
    return re.sub(r"[^a-z0-9가-힣]+", "_", base).strip("_") or url_or_key


def load_seen() -> dict[str, dict[str, Any]]:
    if not SEEN_PATH.is_file():
        return {}
    data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    seen = data.get("seen", data)
    return seen if isinstance(seen, dict) else {}


def load_tracker() -> list[dict[str, str]]:
    if not TRACKER_PATH.is_file():
        return []
    with TRACKER_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_sync_set(args: argparse.Namespace) -> list[dict[str, Any]]:
    seen = load_seen()
    tracker = load_tracker()
    fit_levels = {x.strip().lower() for x in args.fit.split(",") if x.strip()}
    by_key: dict[str, dict[str, Any]] = {}

    def upsert(key: str, row: dict[str, Any]) -> None:
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
            return
        # tracker status wins when both present
        if row.get("_from_tracker") and not existing.get("_from_tracker"):
            merged = {**existing, **row}
            by_key[key] = merged
        elif existing.get("_from_tracker") and not row.get("_from_tracker"):
            merged = {**row, **existing}
            # keep tracker status
            if existing.get("status"):
                merged["status"] = existing["status"]
            by_key[key] = merged
        else:
            by_key[key] = {**existing, **row}

    if not args.scraped_only:
        for key, job in seen.items():
            if job.get("status") != "ranked":
                continue
            score = job.get("rank_score")
            try:
                score_f = float(score) if score is not None else None
            except (TypeError, ValueError):
                score_f = None
            if not args.all:
                if score_f is None or score_f < args.min_score:
                    continue
            upsert(
                key,
                {
                    "key": key,
                    "title": job.get("title") or "",
                    "company": job.get("company") or "",
                    "url": job.get("url") or key,
                    "status": job.get("status") or "ranked",
                    "fit": job.get("fit"),
                    "rank_score": score_f,
                    "verdict": job.get("verdict") or score_to_verdict(score_f),
                    "deadline": job.get("deadline"),
                    "first_seen": job.get("first_seen"),
                    "rank_date": job.get("rank_date"),
                    "portal": job.get("portal"),
                    "location": job.get("location"),
                    "seniority": job.get("seniority"),
                    "experience": job.get("experience"),
                    "role": job.get("role"),
                    "stack": job.get("stack"),
                },
            )

    if args.include_new or args.scraped_only:
        for key, job in seen.items():
            if job.get("status") != "new":
                continue
            fit = (job.get("fit") or "").lower()
            if fit_levels and fit not in fit_levels:
                continue
            upsert(
                key,
                {
                    "key": key,
                    "title": job.get("title") or "",
                    "company": job.get("company") or "",
                    "url": job.get("url") or key,
                    "status": "new",
                    "fit": fit or None,
                    "rank_score": job.get("rank_score"),
                    "verdict": job.get("verdict"),
                    "deadline": job.get("deadline"),
                    "first_seen": job.get("first_seen"),
                    "rank_date": job.get("rank_date"),
                    "portal": job.get("portal"),
                    "location": job.get("location"),
                    "seniority": job.get("seniority"),
                    "experience": job.get("experience"),
                    "role": job.get("role"),
                    "stack": job.get("stack"),
                },
            )

    for row in tracker:
        company = (row.get("company") or "").strip()
        role = (row.get("role") or row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        key = url if url.startswith("http") else job_key("", company, role)
        # Prefer matching an existing seen entry by company+title
        if key not in seen:
            for sk, sj in seen.items():
                if (sj.get("company") or "").lower() == company.lower() and (
                    sj.get("title") or ""
                ).lower() == role.lower():
                    key = sk
                    break
        base = seen.get(key, {})
        upsert(
            key,
            {
                "key": key,
                "title": role or base.get("title") or "",
                "company": company or base.get("company") or "",
                "url": url or base.get("url") or key,
                "status": (row.get("status") or base.get("status") or "applied").lower(),
                "fit": base.get("fit"),
                "rank_score": base.get("rank_score"),
                "verdict": base.get("verdict") or score_to_verdict(
                    float(base["rank_score"]) if base.get("rank_score") is not None else None
                ),
                "deadline": base.get("deadline"),
                "first_seen": base.get("first_seen"),
                "rank_date": base.get("rank_date"),
                "portal": base.get("portal"),
                "location": base.get("location"),
                "seniority": base.get("seniority"),
                "experience": base.get("experience"),
                "role": base.get("role"),
                "stack": base.get("stack"),
                "applied_on": row.get("date"),
                "channel": row.get("channel"),
                "cv_file": row.get("cv_file"),
                "cover_letter_file": row.get("cover_letter_file"),
                "_from_tracker": True,
            },
        )

    return list(by_key.values())


def database_schema() -> dict[str, Any]:
    def select_opts(names: list[str]) -> dict[str, Any]:
        return {"select": {"options": [{"name": n} for n in names]}}

    return {
        "Name": {"title": {}},
        "Company": {"rich_text": {}},
        "Score": {"number": {}},
        "Verdict": select_opts(VERDICT_OPTIONS),
        "Status": select_opts(STATUS_OPTIONS),
        "Fit": select_opts(FIT_OPTIONS),
        "Seniority": select_opts(SENIORITY_OPTIONS),
        "Experience": {"rich_text": {}},
        "Role": select_opts(ROLE_OPTIONS),
        "Tech stack": {"multi_select": {"options": []}},
        "Deadline": {"date": {}},
        "First seen": {"date": {}},
        "Ranked": {"date": {}},
        "Applied on": {"date": {}},
        "Channel": {"select": {"options": []}},
        "CV file": {"rich_text": {}},
        "Cover letter": {"rich_text": {}},
        "Portal": {"rich_text": {}},
        "URL": {"url": {}},
        "Key": {"rich_text": {}},
    }


def ensure_database(token: str, state: dict[str, Any], parent_page_id: str | None) -> str:
    db_id = state.get("database_id") or os.environ.get("NOTION_DATABASE_ID")
    if db_id:
        try:
            notion_request("GET", f"/databases/{db_id}", token)
            return db_id
        except RuntimeError:
            print(f"Stored database {db_id} missing; will recreate.", file=sys.stderr)

    if not parent_page_id:
        raise SystemExit(
            "First run needs NOTION_PARENT_PAGE_ID (share a Notion page with your "
            "integration, paste its ID into job_scraper/notion.env)."
        )

    parent_page_id = parent_page_id.replace("-", "")
    # Notion accepts UUIDs with or without dashes in API paths; normalize to dashed
    if len(parent_page_id) == 32:
        parent_page_id = (
            f"{parent_page_id[:8]}-{parent_page_id[8:12]}-"
            f"{parent_page_id[12:16]}-{parent_page_id[16:20]}-{parent_page_id[20:]}"
        )

    created = notion_request(
        "POST",
        "/databases",
        token,
        {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": DB_TITLE}}],
            "properties": database_schema(),
        },
    )
    db_id = created["id"]
    state["database_id"] = db_id
    state["database_url"] = created.get("url")
    save_state(state)
    print(f"Created database: {state.get('database_url')}")
    return db_id


def ensure_properties(token: str, db_id: str) -> None:
    db = notion_request("GET", f"/databases/{db_id}", token)
    existing = set(db.get("properties", {}).keys())
    schema = database_schema()
    missing = {k: v for k, v in schema.items() if k not in existing}
    if not missing:
        return
    notion_request("PATCH", f"/databases/{db_id}", token, {"properties": missing})


def find_page_by_key(token: str, db_id: str, key: str) -> str | None:
    result = notion_request(
        "POST",
        f"/databases/{db_id}/query",
        token,
        {
            "filter": {
                "property": "Key",
                "rich_text": {"equals": key},
            },
            "page_size": 1,
        },
    )
    results = result.get("results") or []
    if not results:
        return None
    return results[0]["id"]


def page_properties(job: dict[str, Any]) -> dict[str, Any]:
    name = f"{job.get('title') or 'Untitled'} — {job.get('company') or '?'}"
    props: dict[str, Any] = {
        "Name": title_prop(name),
        "Company": rich_prop(job.get("company")),
        "Score": number_prop(job.get("rank_score")),
        "Verdict": select_prop(job.get("verdict")),
        "Status": select_prop(job.get("status")),
        "Fit": select_prop(job.get("fit")),
        "Seniority": select_prop(job.get("seniority")),
        "Experience": rich_prop(job.get("experience")),
        "Role": select_prop(job.get("role")),
        "Tech stack": multi_select_prop(job.get("stack")),
        "Deadline": date_prop(job.get("deadline")),
        "First seen": date_prop(job.get("first_seen")),
        "Ranked": date_prop(job.get("rank_date")),
        "Applied on": date_prop(job.get("applied_on")),
        "CV file": rich_prop(job.get("cv_file")),
        "Cover letter": rich_prop(job.get("cover_letter_file")),
        "Portal": rich_prop(job.get("portal")),
        "URL": url_prop(job.get("url")),
        "Key": rich_prop(job.get("key")),
    }
    channel = job.get("channel")
    if channel:
        props["Channel"] = select_prop(str(channel))
    return props


def briefing_blocks(job: dict[str, Any]) -> list[dict[str, Any]]:
    lines = [
        f"Status: {job.get('status')}",
        f"Fit: {job.get('fit') or '—'}",
        f"Seniority: {job.get('seniority') or '—'} ({job.get('experience') or '—'})",
        f"Role: {job.get('role') or '—'}",
        f"Stack: {', '.join(job.get('stack') or []) or '—'}",
        f"Score: {job.get('rank_score') if job.get('rank_score') is not None else '—'}",
        f"Deadline: {job.get('deadline') or '—'}",
        f"First seen: {job.get('first_seen') or '—'}",
        f"Portal: {job.get('portal') or '—'}",
        f"Location: {job.get('location') or '—'}",
    ]
    if job.get("url"):
        lines.append(f"URL: {job['url']}")
    text = "\n".join(lines)[:1900]
    return [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Fit summary"}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": (
                                "Posting body is not mirrored here. Open the URL. "
                                "Documents stay local — only filenames sync."
                            )
                        },
                    }
                ]
            },
        },
    ]


def upsert_job(token: str, db_id: str, job: dict[str, Any], rebuild: bool) -> str:
    key = job["key"]
    page_id = find_page_by_key(token, db_id, key)
    props = page_properties(job)
    if page_id is None:
        notion_request(
            "POST",
            "/pages",
            token,
            {
                "parent": {"database_id": db_id},
                "properties": props,
                "children": briefing_blocks(job),
            },
        )
        return "created"
    notion_request("PATCH", f"/pages/{page_id}", token, {"properties": props})
    if rebuild:
        # Append a rebuild note rather than deleting user content
        notion_request(
            "PATCH",
            f"/blocks/{page_id}/children",
            token,
            {
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": (
                                            f"[rebuild {date.today().isoformat()}] "
                                            "properties refreshed; prior notes kept."
                                        )
                                    },
                                }
                            ]
                        },
                    }
                ]
            },
        )
    return "updated"


def load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["last_sync"] = date.today().isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--min-score", type=float, default=60.0)
    p.add_argument("--all", action="store_true", help="Include all ranked jobs")
    p.add_argument(
        "--include-new",
        action="store_true",
        help="Also sync status=new scraped jobs",
    )
    p.add_argument(
        "--scraped-only",
        action="store_true",
        help="Only sync status=new (plus tracker); implies --include-new",
    )
    p.add_argument(
        "--fit",
        default="high,medium",
        help="Fit levels for --include-new / --scraped-only (comma-separated)",
    )
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--sleep", type=float, default=0.35, help="Pause between upserts")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv_files()
    args = parse_args(argv)
    if args.scraped_only:
        args.include_new = True

    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token and not args.dry_run:
        print(
            "NOTION_TOKEN missing. Create an internal integration, share a page with it, "
            "and put the token in job_scraper/notion.env (gitignored).",
            file=sys.stderr,
        )
        return 2
    if not args.dry_run and (
        len(token) < 40
        or "replace" in token.lower()
        or token in ("ntn_replace_me", "secret_replace_me")
    ):
        print(
            "NOTION_TOKEN still looks like a placeholder (too short or contains 'replace').\n"
            "1) Open https://www.notion.so/my-integrations\n"
            "2) Open your integration → copy Internal Integration Secret (ntn_… / secret_…)\n"
            "3) Paste it into job_scraper/notion.env as NOTION_TOKEN=...\n"
            "Do not leave ntn_replace_me.",
            file=sys.stderr,
        )
        return 2
    parent_check = (os.environ.get("NOTION_PARENT_PAGE_ID") or "").strip()
    parent_hex = re.sub(r"[^0-9a-fA-F]", "", parent_check)
    if (
        not args.dry_run
        and not os.environ.get("NOTION_DATABASE_ID")
        and not load_state().get("database_id")
        and len(parent_hex) != 32
    ):
        print(
            "NOTION_PARENT_PAGE_ID must be the 32-character hex id from the Notion page URL.\n"
            "Example URL: https://www.notion.so/Job-Search-a1b2c3d4e5f6789012345678abcdef12\n"
            "→ NOTION_PARENT_PAGE_ID=a1b2c3d4e5f6789012345678abcdef12\n"
            "Also connect the integration to that page (··· → Connections).",
            file=sys.stderr,
        )
        return 2

    jobs = build_sync_set(args)
    if not jobs:
        print("Nothing to sync.")
        return 0

    filters = []
    if not args.scraped_only:
        filters.append("all ranked" if args.all else f"ranked score≥{args.min_score:g}")
    if args.include_new:
        filters.append(f"new fit∈{{{args.fit}}}")
    print(f"Sync set: {len(jobs)} jobs ({', '.join(filters) or 'tracker only'})")

    if args.dry_run:
        for j in jobs[:20]:
            print(f"  - [{j.get('status')}/{j.get('fit')}] {j.get('company')} | {j.get('title')}")
        if len(jobs) > 20:
            print(f"  … and {len(jobs) - 20} more")
        return 0

    state = load_state()
    parent = os.environ.get("NOTION_PARENT_PAGE_ID", "").strip() or None
    db_id = ensure_database(token, state, parent)
    ensure_properties(token, db_id)

    created = updated = failed = 0
    failures: list[str] = []
    for job in jobs:
        try:
            result = upsert_job(token, db_id, job, args.rebuild)
            if result == "created":
                created += 1
            else:
                updated += 1
        except Exception as e:  # noqa: BLE001 - report per-row and continue
            failed += 1
            failures.append(f"{job.get('key')}: {e}")
        time.sleep(args.sleep)

    state["database_id"] = db_id
    if not state.get("database_url"):
        try:
            meta = notion_request("GET", f"/databases/{db_id}", token)
            state["database_url"] = meta.get("url")
        except RuntimeError:
            pass
    save_state(state)

    print(
        f"## Pipeline Sync - {date.today().isoformat()}\n"
        f"Database: {state.get('database_url')}\n"
        f"Synced {len(jobs)} jobs: {created} created, {updated} updated, {failed} failed."
    )
    for f in failures[:10]:
        print(f"  FAIL {f}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
