#!/usr/bin/env python3
"""Enrich seen_jobs.json with seniority / role / tech stack.

By default uses title (+ any stored description). With --fetch-detail, runs each
portal's `detail` CLI for high/medium jobs missing stack or seniority.

Usage:
  python3 tools/enrich_seen_jobs.py
  python3 tools/enrich_seen_jobs.py --fetch-detail --fit high,medium --limit 40
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from job_field_enrichment import enrich_job_fields  # noqa: E402

SEEN_PATH = REPO / "job_scraper" / "seen_jobs.json"


def load_seen(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"seen": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_seen(path: Path, store: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_detail(portal: str, url: str) -> dict[str, Any] | None:
    cli = REPO / ".agents" / "skills" / portal / "cli" / "src" / "cli.ts"
    if not cli.is_file():
        return None
    # Large JDs break when read via a pipe (truncated JSON). Write to a temp file.
    out_path = Path(tempfile.mkstemp(prefix="detail_", suffix=".json")[1])
    try:
        with out_path.open("w", encoding="utf-8") as out_f:
            proc = subprocess.run(
                ["bun", "run", str(cli), "detail", url, "--format", "json"],
                cwd=REPO,
                stdout=out_f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=90,
            )
        if proc.returncode != 0:
            return None
        raw = out_path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict) and "description" not in data and "result" in data:
            data = data["result"]
        return data if isinstance(data, dict) else None
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        try:
            out_path.unlink(missing_ok=True)
        except OSError:
            pass


def apply_enrichment(job: dict[str, Any], detail: dict[str, Any] | None = None) -> bool:
    title = job.get("title") or (detail or {}).get("title") or ""
    desc = job.get("description") or ""
    hint = job.get("experience") or job.get("seniority_raw")
    skills = job.get("skills") if isinstance(job.get("skills"), list) else None
    if detail:
        if detail.get("description"):
            desc = detail["description"]
            job["description"] = desc[:8000]
        if detail.get("deadline") and not job.get("deadline"):
            job["deadline"] = detail["deadline"]
        if detail.get("seniority"):
            hint = detail["seniority"]
        if detail.get("location") and not job.get("location"):
            job["location"] = detail["location"]
        if isinstance(detail.get("skills"), list) and detail["skills"]:
            skills = detail["skills"]
            job["skills"] = skills

    fields = enrich_job_fields(
        title=title,
        description=desc,
        seniority_hint=hint if isinstance(hint, str) else None,
        skills=skills,
        existing=job,
    )
    changed = False
    for k, v in fields.items():
        if job.get(k) != v:
            job[k] = v
            changed = True
    return changed


def software_priority(job: dict[str, Any]) -> int:
    """Lower = fetch detail first."""
    title = job.get("title") or ""
    role = job.get("role") or ""
    if role == "비개발":
        return 90
    if any(
        k in title
        for k in (
            "백엔드",
            "프론트",
            "풀스택",
            "서버",
            "개발자",
            "엔지니어",
            "데이터",
            "DevOps",
            "SW",
            "소프트웨어",
            "AI",
            "ML",
        )
    ):
        return 0
    if role in ("백엔드", "프론트엔드", "풀스택", "데이터", "AI/ML", "인프라/DevOps", "모바일"):
        return 1
    if "개발" in title:
        return 5
    return 40


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seen", type=Path, default=SEEN_PATH)
    p.add_argument("--fetch-detail", action="store_true")
    p.add_argument("--fit", default="high,medium")
    p.add_argument("--limit", type=int, default=80, help="Max detail fetches")
    p.add_argument("--sleep", type=float, default=0.6)
    p.add_argument("--only-missing", action="store_true", default=True)
    p.add_argument("--all-jobs", action="store_true", help="Ignore --only-missing")
    args = p.parse_args(argv)
    only_missing = not args.all_jobs

    store = load_seen(args.seen)
    seen: dict[str, Any] = store.setdefault("seen", {})
    fit_ok = {x.strip() for x in args.fit.split(",") if x.strip()}

    updated = 0
    fetched = 0
    for key, job in seen.items():
        before = json.dumps(job, sort_keys=True, ensure_ascii=False)
        apply_enrichment(job)
        if json.dumps(job, sort_keys=True, ensure_ascii=False) != before:
            updated += 1

    if args.fetch_detail:
        candidates = []
        for key, job in seen.items():
            if (job.get("fit") or "") not in fit_ok:
                continue
            if only_missing:
                stack = job.get("stack") or []
                sen = job.get("seniority") or "미상"
                if stack and sen != "미상" and job.get("description"):
                    continue
            candidates.append((key, job))
        candidates.sort(key=lambda kv: software_priority(kv[1]))

        for key, job in candidates[: args.limit]:
            portal = job.get("portal") or ""
            url = job.get("url") or key
            detail = run_detail(portal, url)
            fetched += 1
            if detail:
                apply_enrichment(job, detail)
                updated += 1
            time.sleep(args.sleep)

    save_seen(args.seen, store)
    print(f"Enriched store: {updated} jobs touched; detail fetches={fetched}; total={len(seen)}")
    from collections import Counter

    sen = Counter((j.get("seniority") or "미상") for j in seen.values())
    roles = Counter((j.get("role") or "미상") for j in seen.values())
    with_stack = sum(1 for j in seen.values() if j.get("stack"))
    print("seniority:", dict(sen))
    print("role:", dict(roles))
    print("with_stack:", with_stack)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
