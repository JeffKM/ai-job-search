export const BASE_URL = "https://www.jobkorea.co.kr"

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

export async function htmlFetch(url: string): Promise<string> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": UA,
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
      },
      redirect: "follow",
      signal: AbortSignal.timeout(15000),
    })
    if (response.status === 429 || response.status >= 500) {
      if (attempt === maxRetries) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`)
      }
      const jitter = Math.floor(Math.random() * 500)
      await new Promise((r) => setTimeout(r, delay + jitter))
      delay = Math.min(delay * 2, 8000)
      continue
    }
    if (response.status === 404) return ""
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`)
    }
    return response.text()
  }
  throw new Error("Request failed after max retries")
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  location: string | null
  date: string | null
  url: string
  companyTypeLabel?: string | null
}

export interface JobDetail extends JobCard {
  description: string | null
  deadline: string | null
  employmentType: string | null
  /** Hard-skill chips from JobKorea job-hub payload when present */
  skills?: string[]
  /** Signed S3 HTML body URL for the full posting (may expire) */
  descriptionUrl?: string | null
}

function numericEntity(cp: number): string {
  return cp >= 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : ""
}

export function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, dec) => numericEntity(parseInt(dec, 10)))
    .replace(/&#[xX]([0-9a-fA-F]+);/g, (_, hex) => numericEntity(parseInt(hex, 16)))
    .replace(/&nbsp;/g, " ")
}

function stripTags(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
}

function clean(html: string): string {
  return decodeHtmlEntities(stripTags(html))
}

export function buildSearchUrl(query: string, page: number, companyTypeTab?: string): string {
  const params = new URLSearchParams({
    stext: query,
    Page_No: String(page),
  })
  if (companyTypeTab) params.set("tab", companyTypeTab)
  return `${BASE_URL}/Search/?${params.toString()}`
}

export function parseSearchResults(html: string): JobCard[] {
  const results: JobCard[] = []
  const seen = new Set<string>()
  const cardRe = /GI_Read\/(\d+)[\s\S]{0,1500}?truncate font-semibold[^"]*">([^<]+)<\/span>/g
  let match: RegExpExecArray | null

  while ((match = cardRe.exec(html)) !== null) {
    const id = match[1]
    if (seen.has(id)) continue
    seen.add(id)

    const title = clean(match[2])
    if (!title) continue

    const pos = html.indexOf(`GI_Read/${id}`)
    const chunk = html.slice(pos, pos + 5000)

    const companyMatch = chunk.match(/text-gray700 text-typo-b2-16">([^<]+)<\/span>/i)
    const company = companyMatch ? clean(companyMatch[1]) || null : null

    const locMatch = chunk.match(
      /basicemoji-place2[\s\S]{0,250}?text-typo-b4-14">([^<]+)<\/span>/i,
    )
    const location = locMatch ? clean(locMatch[1]) || null : null

    const badgeMatch = chunk.match(/text-brand-primary">([^<]+)<\/span>/i)
    const companyTypeLabel = badgeMatch ? clean(badgeMatch[1]) || null : null

    results.push({
      id,
      title,
      company,
      location,
      date: null,
      url: `${BASE_URL}/Recruit/GI_Read/${id}`,
      companyTypeLabel,
    })
  }

  return results
}

export function extractJobHubSkills(html: string): string[] {
  // RSC payload escapes quotes as \". Prefer HARD_SKILL chips near this job's hub id;
  // ignore later recommendation carousels that also embed skills arrays.
  const normalized = html.replace(/\\"/g, '"').replace(/\\u0026/g, "&")
  const hub = normalized.match(/"jobHubId"\s*:\s*"([^"]+)"/)
  const start = hub ? normalized.indexOf(`"jobHubId":"${hub[1]}"`) : 0
  const window = normalized.slice(Math.max(0, start), start + 20000)
  // Stop before obvious related-job sections when present
  const cut = window.search(/"similar|"recommend|"relatedJobs|"jobList"/i)
  const scope = cut > 0 ? window.slice(0, cut) : window

  const out: string[] = []
  const blockRe = /"skills"\s*:\s*\[([\s\S]*?)\]/g
  let block: RegExpExecArray | null
  while ((block = blockRe.exec(scope)) !== null) {
    if (!block[1].includes("HARD_SKILL") && !block[1].includes('"name"')) continue
    const names = [...block[1].matchAll(/"name"\s*:\s*"([^"]+)"/g)].map((m) =>
      decodeHtmlEntities(m[1]).trim(),
    )
    for (const n of names) {
      // Skip benefit-like / soft labels
      if (!n || n.length > 40) continue
      if (/국가유공|보훈|전공자|우대|필수/.test(n)) continue
      if (!out.includes(n)) out.push(n)
    }
  }
  return out
}

export function extractDescriptionHtmlUrl(html: string): string | null {
  const normalized = html.replace(/\\u0026/g, "&")
  const m = normalized.match(
    /https:\/\/job-hub-files[^"'\\\s]+_DESCRIPTION\.html\?[^"'\\\s]+/,
  )
  if (!m) return null
  return m[0].replace(/\\+/g, "")
}

export function parseJobDetail(html: string, id: string): JobDetail {
  const ldMatch = html.match(/<script type="application\/ld\+json">\s*(\{[\s\S]*?\})\s*<\/script>/i)
  let title = ""
  let company: string | null = null
  let location: string | null = null
  let date: string | null = null
  let deadline: string | null = null
  let description: string | null = null
  let employmentType: string | null = null

  if (ldMatch) {
    try {
      const ld = JSON.parse(ldMatch[1]) as Record<string, unknown>
      if (typeof ld.title === "string") title = ld.title
      if (typeof ld.description === "string") description = ld.description
      if (typeof ld.datePosted === "string") date = ld.datePosted
      if (typeof ld.validThrough === "string") deadline = ld.validThrough
      if (typeof ld.employmentType === "string") employmentType = ld.employmentType
      const hiring = ld.hiringOrganization as { name?: string } | undefined
      if (hiring?.name) company = hiring.name
      const jobLoc = ld.jobLocation as { address?: { addressLocality?: string; addressRegion?: string } } | undefined
      if (jobLoc?.address) {
        location = [jobLoc.address.addressRegion, jobLoc.address.addressLocality].filter(Boolean).join(" ") || null
      }
    } catch {
      // fall through to meta tags
    }
  }

  if (!title) {
    const og = html.match(/property="og:title"[^>]+content="([^"]+)"/i)
    const ogTitle = og ? clean(og[1]) : ""
    const parts = ogTitle.split(/\s*채용\s*-\s*/)
    if (parts.length >= 2) {
      company = parts[0].trim() || company
      title = parts[1].replace(/\s*\|\s*잡코리아\s*$/, "").trim()
    } else {
      title = ogTitle.replace(/\s*\|\s*잡코리아\s*$/, "")
    }
  }
  if (!description) {
    const meta = html.match(/property="og:description"[^>]+content="([^"]+)"/i)
    description = meta ? clean(meta[1]) : null
    if (meta && !deadline) {
      const dl = clean(meta[1]).match(/마감일\s*:\s*([^,]+)/)
      if (dl) deadline = dl[1].trim()
    }
  }
  if (!title) throw new Error("Failed to parse job listing HTML")

  if (title.includes(" 채용 - ")) {
    const parts = title.split(/\s*채용\s*-\s*/)
    if (parts.length >= 2) {
      if (!company) company = parts[0].trim() || null
      title = parts[1].replace(/\s*\|\s*잡코리아\s*$/, "").trim()
    }
  }

  const skills = extractJobHubSkills(html)
  const descriptionUrl = extractDescriptionHtmlUrl(html)

  // Prefer job-hub title/company from RSC payload when LD+JSON is a thin summary
  const hubTitle = html.match(/"title"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"companyName"/)
  if (hubTitle) {
    try {
      title = JSON.parse(`"${hubTitle[1]}"`) as string
    } catch {
      /* keep existing */
    }
  }
  const hubCompany = html.match(/"companyName"\s*:\s*"((?:[^"\\]|\\.)*)"/)
  if (hubCompany && !company) {
    try {
      company = JSON.parse(`"${hubCompany[1]}"`) as string
    } catch {
      /* keep existing */
    }
  }

  return {
    id,
    title,
    company,
    location,
    date,
    url: `${BASE_URL}/Recruit/GI_Read/${id}`,
    description,
    deadline,
    employmentType,
    skills,
    descriptionUrl,
  }
}

export function normalizeId(input: string): string | null {
  const url = input.match(/GI_Read\/(\d+)/)
  if (url) return url[1]
  if (/^\d+$/.test(input)) return input
  return null
}

export function buildDetailUrl(id: string): string {
  return `${BASE_URL}/Recruit/GI_Read/${id}`
}
