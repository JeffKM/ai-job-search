#!/usr/bin/env python3
"""Fetch JobPlanet (잡플래닛) pages via Scrapling and extract structured job JSON."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from kr_company_type import card_matches_company_type, parse_company_type  # noqa: E402

BASE_URL = "https://www.jobplanet.co.kr"


def write_error(message: str, code: str) -> None:
    json.dump({"error": message, "code": code}, sys.stderr)
    sys.stderr.write("\n")


def fetch_html(url: str, *, solve_cloudflare: bool = True, timeout_ms: int = 60000) -> str:
    from scrapling.fetchers import StealthyFetcher

    page = StealthyFetcher.fetch(
        url,
        headless=True,
        network_idle=True,
        solve_cloudflare=solve_cloudflare,
        timeout=timeout_ms,
    )
    html = getattr(page, "html_content", None) or getattr(page, "body", None) or str(page)
    if not html or len(html) < 500:
        raise RuntimeError("Empty or truncated response from JobPlanet")
    if "Attention Required" in html and "Cloudflare" in html:
        raise RuntimeError("Cloudflare challenge page returned")
    return html


def extract_json_array_after_key(html: str, key: str = '"jobs"') -> list[Any]:
    marker = f"{key}:"
    idx = html.find(marker)
    if idx < 0:
        return []
    start = html.find("[", idx)
    if start < 0:
        return []

    depth = 0
    i = start
    in_str = False
    esc = False
    while i < len(html):
        ch = html[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return json.loads(html[start : i + 1])
        i += 1
    return []


def strip_html(text: str | None) -> str | None:
    if not text:
        return None
    unescaped = html_lib.unescape(text)
    plain = re.sub(r"<[^>]+>", " ", unescaped)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain or None


def decode_text_field(text: str | None) -> str | None:
    if not text:
        return None
    value = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    value = html_lib.unescape(value)
    return value.strip() or None


def job_to_card(row: dict[str, Any]) -> dict[str, Any]:
    jd = row.get("jd") or {}
    company = row.get("company") or {}
    posting_id = str(row.get("id") or jd.get("id") or "")
    rel_url = jd.get("url") or jd.get("partial_url") or ""
    url = f"{BASE_URL}{rel_url}" if rel_url.startswith("/") else f"{BASE_URL}/job/search?posting_ids%5B%5D={posting_id}"
    cities = jd.get("cities") or []
    location = ", ".join(cities) if cities else None
    created = jd.get("created_at") or jd.get("open_at")
    date = created[:10] if isinstance(created, str) and len(created) >= 10 else None
    return {
        "id": posting_id,
        "title": jd.get("title") or "",
        "company": company.get("name"),
        "location": location,
        "date": date,
        "url": url,
    }


def query_tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\s+", query.strip()) if t]


def matches_query(card: dict[str, Any], row: dict[str, Any], query: str) -> bool:
    tokens = query_tokens(query)
    if not tokens:
        return True
    jd = row.get("jd") or {}
    company = row.get("company") or {}
    parts = [
        card.get("title") or "",
        company.get("name") or "",
        " ".join(o.get("name", "") for o in jd.get("level2_occupations") or []),
        " ".join(s.get("name", "") for s in jd.get("required_skills") or []),
    ]
    haystack = " ".join(parts).lower()
    return all(token.lower() in haystack for token in tokens)


def extract_detail_chunk(html: str, posting_id: str) -> str:
    """Return an HTML substring that contains detail fields for a posting id."""
    id_marker = f'"id":{posting_id}'
    id_pos = html.find(id_marker)
    if id_pos < 0:
        id_marker = f'"id": {posting_id}'
        id_pos = html.find(id_marker)

    if id_pos >= 0:
        window_start = max(0, id_pos - 80_000)
        window_end = min(len(html), id_pos + 8_000)
        window = html[window_start:window_end]
        rel_id = id_pos - window_start

        detail_keys = (
            "introduction",
            "required_qualification",
            "preferred_skill",
            "primary_responsibility",
            "description",
        )
        starts: list[int] = []
        for key in detail_keys:
            rel = window.rfind(f'"{key}"', 0, rel_id + 1)
            if rel < 0:
                rel = window.rfind(f'\\"{key}\\"', 0, rel_id + 1)
            if rel >= 0:
                starts.append(rel)
        if starts:
            return window[min(starts) : rel_id + 5_000]

    # Fallback: first unescaped detail blob (typical for single-posting detail pages)
    for key in ("primary_responsibility", "required_qualification", "preferred_skill"):
        pos = html.find(f'"{key}"')
        if pos >= 0:
            return html[pos : pos + 12_000]

    return ""


def field_from_escaped_html(name: str, chunk: str) -> str | None:
    """Extract a field from double-escaped JSON embedded in HTML."""
    m = re.search(rf'\\"{name}\\":\\"((?:\\\\.|[^"\\])*)\\"', chunk)
    return decode_text_field(m.group(1)) if m else None


def field_from_chunk(name: str, chunk: str) -> str | None:
    m = re.search(rf'"{name}"\s*:\s*"((?:\\.|[^"\\])*)"', chunk)
    if m:
        return decode_text_field(m.group(1))
    return field_from_escaped_html(name, chunk)


def build_description_parts(chunk: str) -> list[str]:
    description_parts: list[str] = []
    for key, label in [
        ("description", ""),
        ("primary_responsibility", "[주요업무]"),
        ("required_qualification", "[자격요건]"),
        ("preferred_skill", "[우대사항]"),
    ]:
        value = field_from_chunk(key, chunk)
        if not value:
            continue
        if key == "description":
            plain = strip_html(value)
            if plain:
                description_parts.append(plain)
        else:
            description_parts.append(f"{label}\n{value}")
    return description_parts


def extract_detail_fields(html: str, posting_id: str) -> dict[str, Any] | None:
    jobs = extract_json_array_after_key(html, '"jobs"')
    row: dict[str, Any] | None = None
    for candidate in jobs:
        if str(candidate.get("id")) == posting_id:
            row = candidate
            break

    chunk = extract_detail_chunk(html, posting_id)
    description_parts = build_description_parts(chunk) if chunk else []

    if row:
        card = job_to_card(row)
        jd = row.get("jd") or {}
        if not description_parts:
            if jd.get("description"):
                plain = strip_html(decode_text_field(jd.get("description")) or "")
                if plain:
                    description_parts.append(plain)
            resp = decode_text_field(jd.get("primary_responsibility"))
            if resp:
                description_parts.append(f"[주요업무]\n{resp}")

        location = field_from_chunk("location", chunk) if chunk else None
        if not location:
            cities = jd.get("cities") or []
            location = ", ".join(cities) if cities else None

        employment = (jd.get("job_type") or {}).get("name")
        if not employment and chunk:
            jt = re.search(r'"job_type"\s*:\s*"((?:\\.|[^"\\])*)"', chunk)
            if jt:
                employment = decode_text_field(jt.group(1))

        return {
            **card,
            "location": location or card.get("location"),
            "description": "\n\n".join(description_parts) if description_parts else None,
            "deadline": jd.get("end_at") or jd.get("end_at_factor") or (field_from_chunk("end_at", chunk) if chunk else None),
            "employmentType": employment,
        }

    if not chunk:
        return None

    title = field_from_chunk("title", chunk)
    company_name = None
    cm = re.search(r'"company"\s*:\s*\{[\s\S]*?"name"\s*:\s*"((?:\\.|[^"\\])*)"', chunk)
    if cm:
        company_name = decode_text_field(cm.group(1))

    ld = re.search(r'<script type="application/ld\+json">(\{[\s\S]*?\})</script>', html)
    ld_desc = None
    ld_title = title
    if ld:
        try:
            data = json.loads(ld.group(1))
            ld_title = data.get("title") or ld_title
            ld_desc = strip_html(data.get("description"))
        except json.JSONDecodeError:
            pass

    if not description_parts and ld_desc:
        description_parts = [ld_desc]

    location = field_from_chunk("location", chunk)
    end_at = field_from_chunk("end_at", chunk) or field_from_chunk("end_at_factor", chunk)
    employment = None
    jt = re.search(r'"job_type"\s*:\s*\{[\s\S]*?"name"\s*:\s*"((?:\\.|[^"\\])*)"', chunk)
    if jt:
        employment = decode_text_field(jt.group(1))
    if not employment:
        jt_plain = re.search(r'"job_type"\s*:\s*"((?:\\.|[^"\\])*)"', chunk)
        if jt_plain:
            employment = decode_text_field(jt_plain.group(1))

    rel_url = None
    um = re.search(r'"url"\s*:\s*"(/companies/[^"]+)"', chunk)
    if um:
        rel_url = um.group(1)

    return {
        "id": posting_id,
        "title": ld_title or title or "(untitled)",
        "company": company_name,
        "location": location,
        "date": None,
        "url": f"{BASE_URL}{rel_url}" if rel_url else f"{BASE_URL}/job/search?posting_ids%5B%5D={posting_id}",
        "description": "\n\n".join(description_parts) if description_parts else ld_desc,
        "deadline": end_at,
        "employmentType": employment,
    }


def cmd_search(args: argparse.Namespace) -> int:
    query = args.query.strip()
    page = max(1, args.page)
    max_pages = max(1, args.max_pages)
    limit = args.limit if args.limit is not None else 20
    seen: set[str] = set()
    cards: list[dict[str, Any]] = []

    try:
        for offset in range(max_pages):
            current_page = page + offset
            url = f"{BASE_URL}/job/search?keyword={quote(query)}&page={current_page}"
            html = fetch_html(url, timeout_ms=args.timeout_ms)
            rows = extract_json_array_after_key(html)
            if not rows:
                break

            for row in rows:
                card = job_to_card(row)
                if not card["id"] or not card["title"] or card["id"] in seen:
                    continue
                if query and not matches_query(card, row, query):
                    continue
                if args.company_type and not card_matches_company_type(args.company_type, card.get("company")):
                    continue
                seen.add(card["id"])
                cards.append(card)
                if len(cards) >= limit:
                    break

            if len(cards) >= limit:
                break
    except Exception as exc:  # noqa: BLE001
        write_error(str(exc), "FETCH_FAILED")
        return 1

    meta: dict[str, Any] = {"count": len(cards), "page": page}
    if args.company_type:
        meta["company_type"] = args.company_type
        meta["company_type_mode"] = "client"
    payload = {"meta": meta, "results": cards}
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_detail(args: argparse.Namespace) -> int:
    posting_id = str(args.id).strip()
    if not posting_id.isdigit():
        write_error(f"Invalid posting id: {args.id}", "BAD_ID")
        return 1

    url = f"{BASE_URL}/job/search?posting_ids%5B%5D={posting_id}"
    try:
        html = fetch_html(url, timeout_ms=args.timeout_ms)
    except Exception as exc:  # noqa: BLE001
        write_error(str(exc), "FETCH_FAILED")
        return 1

    row = extract_detail_fields(html, posting_id)
    if not row:
        write_error("Job not found", "NOT_FOUND")
        return 1

    detail = row

    if args.format == "plain":
        lines = [
            detail.get("title") or "",
            f"{detail.get('company') or '—'} · {detail.get('location') or '—'}",
            f"Deadline: {detail.get('deadline')}" if detail.get("deadline") else "",
            "",
            detail.get("description") or "(no description)",
            "",
            f"URL: {detail.get('url')}",
        ]
        sys.stdout.write("\n".join([l for l in lines if l != ""]) + "\n")
    else:
        json.dump(detail, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="JobPlanet fetch + extract (Scrapling)")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search")
    search.add_argument("--query", "-q", required=True)
    search.add_argument("--page", type=int, default=1)
    search.add_argument("--limit", "-n", type=int, default=20)
    search.add_argument("--max-pages", type=int, default=5, help="Pages to scan when keyword filter is client-side")
    search.add_argument(
        "--company-type",
        dest="company_type_raw",
        help="Filter by company size: major, enterprise-1000, mid, sme, startup, foreign, public, kospi, kosdaq",
    )
    search.add_argument("--timeout-ms", type=int, default=60000)

    detail = sub.add_parser("detail")
    detail.add_argument("id")
    detail.add_argument("--format", choices=["json", "plain"], default="json")
    detail.add_argument("--timeout-ms", type=int, default=60000)

    args = parser.parse_args()
    if args.command == "search":
        args.company_type = parse_company_type(getattr(args, "company_type_raw", None))
        if getattr(args, "company_type_raw", None) and not args.company_type:
            write_error("Invalid --company-type", "BAD_COMPANY_TYPE")
            return 1
        return cmd_search(args)
    if args.command == "detail":
        return cmd_detail(args)
    write_error("Unknown command", "BAD_CMD")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
