"""Korean company-type filter (Python mirror of shared/kr-company-type.ts)."""

from __future__ import annotations

import re
from typing import Literal

CompanyType = Literal[
    "major",
    "enterprise-1000",
    "mid",
    "sme",
    "startup",
    "foreign",
    "public",
    "kospi",
    "kosdaq",
]

COMPANY_TYPE_VALUES: tuple[CompanyType, ...] = (
    "major",
    "enterprise-1000",
    "mid",
    "sme",
    "startup",
    "foreign",
    "public",
    "kospi",
    "kosdaq",
)

_ALIASES: dict[str, CompanyType] = {
    "major": "major",
    "대기업": "major",
    "enterprise1000": "enterprise-1000",
    "enterprise-1000": "enterprise-1000",
    "1000대": "enterprise-1000",
    "매출1000대": "enterprise-1000",
    "mid": "mid",
    "중견": "mid",
    "sme": "sme",
    "중소": "sme",
    "startup": "startup",
    "스타트업": "startup",
    "foreign": "foreign",
    "외국계": "foreign",
    "public": "public",
    "공기업": "public",
    "kospi": "kospi",
    "kosdaq": "kosdaq",
    "scale001": "major",
    "scale002": "enterprise-1000",
    "scale003": "mid",
    "scale004": "sme",
    "scale005": "startup",
}

_MAJOR_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"삼성",
        r"LG(?:전자|디스플레이|이노텍|유플러스|화학|생활)",
        r"SK(?:하이닉스|텔레콤|이노베이션|네트웍스|바이오)",
        r"현대(?:자동차|모비스|중공업|건설|글로비스)",
        r"HD현대",
        r"기아",
        r"포스코",
        r"한화",
        r"롯데",
        r"\bCJ\b",
        r"두산",
        r"KT",
        r"네이버",
        r"카카오",
        r"쿠팡",
        r"한국전력",
        r"공기업",
        r"공사",
    ]
]

_FOREIGN_PATTERNS = [re.compile(p, re.I) for p in [r"외국계", r"\bInc\.?\b", r"\bCorp\.?\b", r"\bLtd\.?\b"]]
_STARTUP_PATTERNS = [re.compile(p, re.I) for p in [r"스타트업", r"벤처"]]


def parse_company_type(raw: str | None) -> CompanyType | None:
    if not raw or not raw.strip():
        return None
    key = raw.strip().lower()
    return _ALIASES.get(key) or _ALIASES.get(raw.strip())


def _name_matches(name: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(name) for p in patterns)


def infer_company_type_from_name(name: str | None) -> CompanyType | None:
    if not name or not name.strip():
        return None
    n = name.strip()
    if _name_matches(n, _MAJOR_PATTERNS):
        return "major"
    if _name_matches(n, _FOREIGN_PATTERNS):
        return "foreign"
    if _name_matches(n, _STARTUP_PATTERNS):
        return "startup"
    return None


def card_matches_company_type(type_: CompanyType, company: str | None) -> bool:
    inferred = infer_company_type_from_name(company)
    if inferred == type_:
        return True
    if type_ == "major":
        return inferred in ("major", "enterprise-1000")
    if type_ == "enterprise-1000":
        return inferred in ("major", "enterprise-1000")
    if type_ == "sme":
        return inferred == "sme" or (inferred is None and not _name_matches(company or "", _MAJOR_PATTERNS))
    if type_ == "startup":
        return inferred == "startup" or (inferred is None and not _name_matches(company or "", _MAJOR_PATTERNS))
    if type_ == "public":
        return inferred == "public" or bool(re.search(r"공기업|공사|공단|공공", company or ""))
    return inferred == type_
