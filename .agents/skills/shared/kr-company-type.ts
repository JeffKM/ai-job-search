/** Korean company-type filter shared by portal-search CLIs. */

export const COMPANY_TYPE_VALUES = [
  "major",
  "enterprise-1000",
  "mid",
  "sme",
  "startup",
  "foreign",
  "public",
  "kospi",
  "kosdaq",
] as const

export type CompanyType = (typeof COMPANY_TYPE_VALUES)[number]

export const COMPANY_TYPE_HELP =
  "major (대기업) | enterprise-1000 (매출1000대) | mid (중견) | sme (중소) | startup | foreign (외국계) | public (공기업) | kospi | kosdaq"

const ALIASES: Record<string, CompanyType> = {
  major: "major",
  "대기업": "major",
  enterprise1000: "enterprise-1000",
  "enterprise-1000": "enterprise-1000",
  "1000대": "enterprise-1000",
  "매출1000대": "enterprise-1000",
  mid: "mid",
  "중견": "mid",
  sme: "sme",
  "중소": "sme",
  startup: "startup",
  "스타트업": "startup",
  foreign: "foreign",
  "외국계": "foreign",
  public: "public",
  "공기업": "public",
  kospi: "kospi",
  kosdaq: "kosdaq",
  scale001: "major",
  scale002: "enterprise-1000",
  scale003: "mid",
  scale004: "sme",
  scale005: "startup",
}

export function parseCompanyType(raw: string | undefined): CompanyType | null {
  if (!raw?.trim()) return null
  const key = raw.trim().toLowerCase()
  return ALIASES[key] ?? ALIASES[raw.trim()] ?? null
}

/** JobKorea Search `tab` query value (best-effort server filter). */
export function jobkoreaTab(type: CompanyType): string | undefined {
  switch (type) {
    case "major":
      return "major"
    case "mid":
    case "sme":
      return "SME"
    case "foreign":
      return "foreign"
    case "public":
      return "MME"
    default:
      return undefined
  }
}

/** Saramin `company_type[]` values. */
export function saraminCompanyTypes(type: CompanyType): string[] | undefined {
  switch (type) {
    case "major":
      return ["scale001"]
    case "enterprise-1000":
      return ["scale002"]
    case "mid":
      return ["scale003"]
    case "sme":
      return ["scale004"]
    case "startup":
      return ["scale005"]
    case "foreign":
      return ["foreign"]
    case "public":
      return ["public"]
    case "kospi":
      return ["kospi"]
    case "kosdaq":
      return ["kosdaq"]
    default:
      return undefined
  }
}

/** JobKorea list badge text → company type. */
const JOBKOREA_BADGE_MAP: Record<string, CompanyType> = {
  "믿고보는 대기업": "major",
  "탄탄한 중견기업": "mid",
}

export function jobkoreaBadgeType(label: string | null | undefined): CompanyType | null {
  if (!label) return null
  return JOBKOREA_BADGE_MAP[label.trim()] ?? null
}

const MAJOR_PATTERNS: RegExp[] = [
  /삼성/i,
  /LG(?:전자|디스플레이|이노텍|유플러스|화학|생활)/i,
  /SK(?:하이닉스|텔레콤|이노베이션|네트웍스|바이오)/i,
  /현대(?:자동차|모비스|중공업|건설|글로비스)/i,
  /HD현대/i,
  /기아/i,
  /포스코/i,
  /한화/i,
  /롯데/i,
  /\bCJ\b/i,
  /두산/i,
  /GS(?:칼텍스|리테일|건설)?/i,
  /KT/i,
  /네이버/i,
  /카카오/i,
  /쿠팡/i,
  /한국전력/i,
  /한국가스공사/i,
  /공기업/i,
  /공사/i,
]

const MID_PATTERNS: RegExp[] = [/중견/i, /강소/i]

const FOREIGN_PATTERNS: RegExp[] = [/외국계/i, /글로벌/i, /\bInc\.?\b/i, /\bCorp\.?\b/i, /\bLtd\.?\b/i]

const STARTUP_PATTERNS: RegExp[] = [/스타트업/i, /벤처/i]

function nameMatchesPatterns(name: string, patterns: RegExp[]): boolean {
  return patterns.some((re) => re.test(name))
}

/** Client-side fallback when a portal has no native company-size filter. */
export function inferCompanyTypeFromName(name: string | null | undefined): CompanyType | null {
  if (!name?.trim()) return null
  const n = name.trim()
  if (nameMatchesPatterns(n, MAJOR_PATTERNS)) return "major"
  if (nameMatchesPatterns(n, FOREIGN_PATTERNS)) return "foreign"
  if (nameMatchesPatterns(n, STARTUP_PATTERNS)) return "startup"
  if (nameMatchesPatterns(n, MID_PATTERNS)) return "mid"
  return null
}

export function cardMatchesCompanyType(
  type: CompanyType,
  card: { company: string | null; companyTypeLabel?: string | null },
): boolean {
  const badgeType = card.companyTypeLabel ? jobkoreaBadgeType(card.companyTypeLabel) : null
  const inferred = inferCompanyTypeFromName(card.company)
  const effective = badgeType ?? inferred

  if (effective === type) return true

  switch (type) {
    case "major":
      return effective === "major" || effective === "enterprise-1000"
    case "enterprise-1000":
      return effective === "enterprise-1000" || effective === "major"
    case "mid":
      return effective === "mid"
    case "sme":
      return effective === "sme" || (effective == null && !nameMatchesPatterns(card.company ?? "", MAJOR_PATTERNS))
    case "startup":
      return effective === "startup" || (effective == null && !nameMatchesPatterns(card.company ?? "", MAJOR_PATTERNS))
    case "foreign":
      return effective === "foreign"
    case "public":
      return effective === "public" || /공기업|공사|공단|공사\b|공공/i.test(card.company ?? "")
    case "kospi":
    case "kosdaq":
      return false
    default:
      return false
  }
}

export function filterByCompanyType<T extends { company: string | null; companyTypeLabel?: string | null }>(
  cards: T[],
  type: CompanyType,
): T[] {
  return cards.filter((c) => cardMatchesCompanyType(type, c))
}

export type CompanyTypeFilterMode = "native" | "client" | "not_applicable"

export function companyTypeFilterMeta(
  type: CompanyType,
  mode: CompanyTypeFilterMode,
): { company_type: CompanyType; company_type_mode: CompanyTypeFilterMode } {
  return { company_type: type, company_type_mode: mode }
}
