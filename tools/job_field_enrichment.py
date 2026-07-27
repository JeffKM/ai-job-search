#!/usr/bin/env python3
"""Extract seniority / role track / tech stack from Korean job title + description.

Used by merge_scrape_results, enrich_seen_jobs, and notion_sync_jobs.
Heuristics only — never invents skills not present in the text.
"""

from __future__ import annotations

import re
from typing import Any

# --- Seniority ---------------------------------------------------------------

_INTERN = re.compile(r"인턴|체험형|internship", re.I)
_JUNIOR_ONLY = re.compile(
    r"(?:^|[^\w])신입(?:[^\w]|$)|신입\s*채용|신입\s*모집|entry[\s-]?level|new\s*grad",
    re.I,
)
_EXPERIENCED = re.compile(
    r"경력사원|경력직|경력\s*\d|경력\s*필수|시니어|senior|lead\b|principal|"
    r"\d+\s*년\s*이상|\d+\s*~\s*\d+\s*년|연차",
    re.I,
)
_EITHER = re.compile(
    r"신입\s*[·/,/|]\s*경력|경력\s*[·/,/|]\s*신입|경력무관|신입/?경력|"
    r"신입\s*또는\s*경력|경력\s*무관",
    re.I,
)
_YEARS = re.compile(
    r"(?<!20)(?<!19)(?:경력\s*)?(\d{1,2})\s*[~～\-–]\s*(\d{1,2})\s*년|"
    r"(?:경력\s*)(\d{1,2})\s*년\s*(?:이상|\+|↑)?|"
    r"(?<![12]\d)(\d{1,2})\s*년\s*(?:이상|\+|↑)",
    re.I,
)

# --- Role track --------------------------------------------------------------

_ROLE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("비개발", re.compile(r"채용담당|recruiter|영업|마케팅|회계|경리|인사\b|HR\b|총무|운전|경비", re.I)),
    ("AI/ML", re.compile(r"\bML\b|머신러닝|딥러닝|LLM|생성형\s*AI|AI\s*엔지니어|MLOps|데이터\s*사이언", re.I)),
    ("데이터", re.compile(r"데이터\s*엔지니어|data\s*engineer|데이터\s*분석|analytics|DW\b|ETL|BigQuery|Spark", re.I)),
    ("인프라/DevOps", re.compile(r"DevOps|SRE|인프라|클라우드\s*엔지니어|Kubernetes|k8s|플랫폼\s*엔지니어|Site\s*Reliability", re.I)),
    ("모바일", re.compile(r"Android|iOS|Flutter|React\s*Native|모바일\s*개발|앱\s*개발", re.I)),
    ("프론트엔드", re.compile(r"프론트\s*엔드|프론트엔드|frontend|front-end|React|Vue\.?js|Next\.?js|UI\s*개발", re.I)),
    ("백엔드", re.compile(r"백\s*엔드|백엔드|backend|back-end|서버\s*개발|Server\s*Developer|API\s*개발", re.I)),
    ("풀스택", re.compile(r"풀\s*스택|풀스택|fullstack|full-stack", re.I)),
]

# --- Tech stack lexicon (order = preference for display) ---------------------

_STACK_TERMS: list[tuple[str, re.Pattern[str]]] = [
    ("Python", re.compile(r"\bPython\b|파이썬", re.I)),
    ("Java", re.compile(r"\bJava\b(?!\s*Script)|자바(?!\s*스크립트)", re.I)),
    ("Kotlin", re.compile(r"\bKotlin\b|코틀린", re.I)),
    ("Go", re.compile(r"\bGo(?:lang)?\b|고랭", re.I)),
    ("TypeScript", re.compile(r"\bTypeScript\b|\bTS\b", re.I)),
    ("JavaScript", re.compile(r"\bJavaScript\b|\bJS\b|자바스크립트", re.I)),
    ("Node.js", re.compile(r"\bNode\.?js\b|\bNode\b", re.I)),
    ("Spring", re.compile(r"\bSpring\b(?:\s*Boot)?|스프링", re.I)),
    ("Django", re.compile(r"\bDjango\b", re.I)),
    ("FastAPI", re.compile(r"\bFastAPI\b", re.I)),
    ("NestJS", re.compile(r"\bNest\.?js\b", re.I)),
    ("Express", re.compile(r"\bExpress\.?js\b|\bExpress\b", re.I)),
    ("React", re.compile(r"\bReact\b(?!\s*Native)", re.I)),
    ("Next.js", re.compile(r"\bNext\.?js\b", re.I)),
    ("Vue", re.compile(r"\bVue\.?js\b|\bVue\b", re.I)),
    ("Angular", re.compile(r"\bAngular\b", re.I)),
    ("Swift", re.compile(r"\bSwift\b", re.I)),
    ("Flutter", re.compile(r"\bFlutter\b", re.I)),
    ("React Native", re.compile(r"React\s*Native", re.I)),
    ("C++", re.compile(r"\bC\+\+\b", re.I)),
    ("C#", re.compile(r"\bC#\b|\.NET", re.I)),
    ("Rust", re.compile(r"\bRust\b", re.I)),
    ("Scala", re.compile(r"\bScala\b", re.I)),
    ("PHP", re.compile(r"\bPHP\b", re.I)),
    ("Ruby", re.compile(r"\bRuby\b|Rails", re.I)),
    ("PostgreSQL", re.compile(r"Postgres(?:ql)?|PostgreSQL", re.I)),
    ("MySQL", re.compile(r"\bMySQL\b|MariaDB", re.I)),
    ("MongoDB", re.compile(r"\bMongoDB?\b", re.I)),
    ("Redis", re.compile(r"\bRedis\b", re.I)),
    ("Kafka", re.compile(r"\bKafka\b", re.I)),
    ("AWS", re.compile(r"\bAWS\b|Amazon\s*Web", re.I)),
    ("GCP", re.compile(r"\bGCP\b|Google\s*Cloud", re.I)),
    ("Azure", re.compile(r"\bAzure\b", re.I)),
    ("Docker", re.compile(r"\bDocker\b", re.I)),
    ("Kubernetes", re.compile(r"\bKubernetes\b|\bk8s\b", re.I)),
    ("GraphQL", re.compile(r"\bGraphQL\b", re.I)),
    ("gRPC", re.compile(r"\bgRPC\b", re.I)),
    ("Terraform", re.compile(r"\bTerraform\b", re.I)),
    ("Spark", re.compile(r"\bSpark\b", re.I)),
    ("Airflow", re.compile(r"\bAirflow\b", re.I)),
    ("TensorFlow", re.compile(r"\bTensorFlow\b", re.I)),
    ("PyTorch", re.compile(r"\bPyTorch\b", re.I)),
]


def infer_role(text: str, title: str = "") -> str:
    title = title or ""
    # Title is authoritative when it names a track clearly.
    title_hits: list[str] = []
    for label, pat in _ROLE_PATTERNS:
        if label == "비개발":
            if pat.search(title) and not re.search(r"개발|엔지니어|engineer", title, re.I):
                return "비개발"
            continue
        if pat.search(title):
            title_hits.append(label)
    if "프론트엔드" in title_hits and "백엔드" in title_hits:
        return "풀스택"
    if "풀스택" in title_hits:
        return "풀스택"
    for p in ("백엔드", "프론트엔드", "모바일", "데이터", "AI/ML", "인프라/DevOps"):
        if p in title_hits:
            return p

    blob = f"{title}\n{text}"
    if not blob.strip():
        return "미상"
    if _ROLE_PATTERNS[0][1].search(blob) and not re.search(
        r"개발|엔지니어|engineer|developer", blob, re.I
    ):
        return "비개발"

    hits: list[str] = []
    for label, pat in _ROLE_PATTERNS:
        if label == "비개발":
            continue
        if pat.search(blob):
            hits.append(label)
    if not hits:
        if re.search(r"개발|엔지니어|engineer|developer|프로그래머", blob, re.I):
            return "기타개발"
        return "미상"
    if "프론트엔드" in hits and "백엔드" in hits:
        return "풀스택"
    if "풀스택" in hits:
        return "풀스택"
    # Prefer product tracks over infra keywords that often appear in any JD
    priority = ["백엔드", "프론트엔드", "모바일", "AI/ML", "데이터", "인프라/DevOps", "풀스택"]
    for p in priority:
        if p in hits:
            return p
    return hits[0]


_STACK_ALIASES: dict[str, str] = {
    "JAVA": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "node": "Node.js",
    "react.js": "React",
    "reactjs": "React",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "spring boot": "Spring",
    "springboot": "Spring",
    "spring framework": "Spring",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mssql": "SQL Server",
    "sql server": "SQL Server",
    "k8s": "Kubernetes",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
}


def normalize_stack_name(name: str) -> str:
    raw = name.strip()
    if not raw:
        return ""
    key = raw.lower()
    if raw.upper() in _STACK_ALIASES:
        return _STACK_ALIASES[raw.upper()]
    if key in _STACK_ALIASES:
        return _STACK_ALIASES[key]
    # Title-case common all-caps chips except known acronyms
    acronyms = {"AWS", "GCP", "SQL", "API", "ETL", "ML", "AI", "CI", "CD", "UI", "UX", "IOS"}
    if raw.upper() in acronyms:
        return raw.upper() if raw.upper() != "IOS" else "iOS"
    for canonical, pat in _STACK_TERMS:
        if pat.fullmatch(raw) or pat.search(raw) and len(raw) <= 24:
            return canonical
    return raw


def merge_stacks(*groups: list[str] | None, limit: int = 16) -> list[str]:
    out: list[str] = []
    for group in groups:
        if not group:
            continue
        for item in group:
            name = normalize_stack_name(item)
            if name and name not in out:
                out.append(name)
            if len(out) >= limit:
                return out
    return out


def infer_stack(text: str, limit: int = 12) -> list[str]:
    if not text.strip():
        return []
    found: list[str] = []
    for name, pat in _STACK_TERMS:
        if pat.search(text) and name not in found:
            found.append(name)
            if len(found) >= limit:
                break
    # Also pick up "기술스택: A, B, C" / "Skills: ..." comma lists
    for m in re.finditer(
        r"(?:기술\s*스택|사용\s*기술|필수\s*기술|Skills?|Tech\s*Stack)\s*[:：]\s*([^\n]{3,200})",
        text,
        re.I,
    ):
        parts = re.split(r"[,/|·•、]", m.group(1))
        for p in parts:
            name = normalize_stack_name(p)
            if name and name not in found and len(name) < 40:
                found.append(name)
                if len(found) >= limit:
                    return found
    return found


def infer_seniority(text: str, explicit: str | None = None, title: str = "") -> tuple[str, str | None]:
    """Return (seniority_label, experience_note).

    Labels: 신입 | 경력 | 신입·경력 | 인턴 | 미상
    Title beats body when it clearly states 신입/경력 (bodies often mention intern programs).
    """
    title = title or ""
    if title.strip():
        if _EITHER.search(title):
            note = None
            m = _YEARS.search(f"{explicit or ''} {text}")
            if m:
                if m.group(1) and m.group(2):
                    a, b = int(m.group(1)), int(m.group(2))
                    if a <= 40 and b <= 40:
                        note = f"{a}–{b}년"
                else:
                    n = m.group(3) or m.group(4)
                    if n and int(n) <= 40:
                        note = f"{int(n)}년+"
            return "신입·경력", note
        if _INTERN.search(title) and not _EXPERIENCED.search(title):
            return "인턴", None
        if _JUNIOR_ONLY.search(title) and not _EXPERIENCED.search(title):
            return "신입", None
        if _EXPERIENCED.search(title) or re.search(r"\(경력\)|경력\s*채용|경력직", title):
            note = None
            m = _YEARS.search(f"{explicit or ''} {title} {text}")
            if m:
                if m.group(1) and m.group(2):
                    a, b = int(m.group(1)), int(m.group(2))
                    if a <= 40 and b <= 40:
                        note = f"{a}–{b}년"
                else:
                    n = m.group(3) or m.group(4)
                    if n and int(n) <= 40:
                        note = f"{int(n)}년+"
            return "경력", note

    blob = " ".join(x for x in (explicit or "", text) if x)
    if not blob.strip():
        return "미상", None

    note = None
    m = _YEARS.search(blob)
    if m:
        if m.group(1) and m.group(2):
            a, b = int(m.group(1)), int(m.group(2))
            if a <= 40 and b <= 40:
                note = f"{a}–{b}년"
        else:
            n = m.group(3) or m.group(4)
            if n and int(n) <= 40:
                note = f"{int(n)}년+"

    if explicit:
        ex = explicit.strip()
        if _INTERN.search(ex):
            return "인턴", note or ex
        if _EITHER.search(ex) or ("신입" in ex and "경력" in ex):
            return "신입·경력", note or ex
        if re.search(r"신입", ex) and not re.search(r"경력", ex):
            return "신입", note or ex
        if re.search(r"경력|년", ex):
            return "경력", note or ex

    if _EITHER.search(blob):
        return "신입·경력", note
    if _JUNIOR_ONLY.search(blob) and not _EXPERIENCED.search(blob):
        return "신입", note
    if _EXPERIENCED.search(blob):
        return "경력", note
    if _INTERN.search(blob):
        return "인턴", note
    if _JUNIOR_ONLY.search(blob):
        return "신입", note
    return "미상", note


def enrich_job_fields(
    title: str = "",
    description: str = "",
    seniority_hint: str | None = None,
    skills: list[str] | None = None,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute enrichment fields. Prefer existing non-empty values unless weaker."""
    existing = existing or {}
    text = f"{title}\n{description}"
    if skills:
        text = f"{text}\n기술스택: {', '.join(skills)}"
    seniority, exp_note = infer_seniority(text, seniority_hint, title=title)
    role = infer_role(description or text, title=title)
    stack = merge_stacks(
        skills,
        infer_stack(text),
        existing.get("stack") if isinstance(existing.get("stack"), list) else None,
    )

    out: dict[str, Any] = {}
    prev_sen = existing.get("seniority")
    if not prev_sen or prev_sen == "미상" or seniority != "미상":
        out["seniority"] = seniority if seniority != "미상" or not prev_sen else prev_sen
    else:
        out["seniority"] = prev_sen

    if exp_note:
        out["experience"] = exp_note
    elif existing.get("experience"):
        out["experience"] = existing["experience"]

    prev_role = existing.get("role")
    if not prev_role or prev_role == "미상" or role != "미상":
        out["role"] = role if role != "미상" or not prev_role else prev_role
    else:
        out["role"] = prev_role

    if stack:
        out["stack"] = stack

    return out


SENIORITY_OPTIONS = ["신입", "경력", "신입·경력", "인턴", "미상"]
ROLE_OPTIONS = [
    "백엔드",
    "프론트엔드",
    "풀스택",
    "모바일",
    "데이터",
    "인프라/DevOps",
    "AI/ML",
    "기타개발",
    "비개발",
    "미상",
]
