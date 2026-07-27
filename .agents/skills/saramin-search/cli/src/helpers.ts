export const BASE_URL = "https://www.saramin.co.kr"

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
}

export interface JobDetail extends JobCard {
  description: string | null
  deadline: string | null
  employmentType: string | null
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

export function buildSearchUrl(query: string, page: number, companyTypes?: string[]): string {
  const params = new URLSearchParams({
    searchword: query,
    recruitPage: String(page),
    recruitSort: "relation",
    searchType: "search",
  })
  if (companyTypes?.length) {
    for (const value of companyTypes) params.append("company_type[]", value)
  }
  return `${BASE_URL}/zf_user/search?${params.toString()}`
}

export function parseSearchResults(html: string): JobCard[] {
  const results: JobCard[] = []
  const seen = new Set<string>()

  const titleRe =
    /href="\/zf_user\/jobs\/relay\/view[^"]*rec_idx=(\d+)[^"]*"[^>]*><span>([\s\S]*?)<\/span>/gi
  let match: RegExpExecArray | null

  while ((match = titleRe.exec(html)) !== null) {
    const id = match[1]
    if (seen.has(id)) continue
    seen.add(id)

    const title = clean(match[2])
    if (!title) continue

    const pos = match.index
    const chunk = html.slice(pos, pos + 6000)

    const companyMatch = chunk.match(/<strong class="corp_name">\s*<a[^>]*>([\s\S]*?)<\/a>/i)
    const company = companyMatch ? clean(companyMatch[1]) || null : null

    const condMatch = chunk.match(/class="job_condition"[^>]*>([\s\S]*?)<\/div>/i)
    const location = condMatch ? clean(condMatch[1]) || null : null

    const dateMatch = chunk.match(/<span class="job_day">([^<]+)<\/span>/i)
    let date: string | null = null
    if (dateMatch) {
      date = clean(dateMatch[1]).replace(/^(등록일|수정일)\s*/, "") || null
    }

    results.push({
      id,
      title,
      company,
      location,
      date,
      url: `${BASE_URL}/zf_user/jobs/view?rec_idx=${id}`,
    })
  }

  return results
}

export function extractDivContent(html: string, className: string): string | null {
  const escaped = className.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const openRe = new RegExp(`<div[^>]*class="[^"]*${escaped}[^"]*"[^>]*>`, "i")
  const open = openRe.exec(html)
  if (!open) return null

  let i = open.index + open[0].length
  let depth = 1
  while (depth > 0 && i < html.length) {
    const nextOpen = html.indexOf("<div", i)
    const nextClose = html.indexOf("</div>", i)
    if (nextClose === -1) return null
    if (nextOpen !== -1 && nextOpen < nextClose) {
      depth++
      i = nextOpen + 4
    } else {
      depth--
      i = nextClose + 6
    }
  }
  return html.slice(open.index + open[0].length, i - 6)
}

export function parseJobDetail(html: string, id: string): JobDetail {
  const titleMatch = html.match(/<h1 class="tit_job">\s*([\s\S]*?)\s*<\/h1>/i)
  const title = titleMatch ? clean(titleMatch[1]) : ""
  if (!title) throw new Error("Failed to parse job listing HTML")

  const companyMatch =
    html.match(/class="company"[^>]*>\s*([\s\S]*?)\s*<\/a>/i) ||
    html.match(/<a[^>]*class="company"[^>]*>\s*([\s\S]*?)\s*<\/a>/i)
  const company = companyMatch ? clean(companyMatch[1]) || null : null

  let location: string | null = null

  let description: string | null = null
  const userContent = extractDivContent(html, "user_content")
  if (userContent) {
    const withBreaks = userContent
      .replace(/<\s*br\s*\/?>/gi, "\n")
      .replace(/<\/(p|li|ul|ol|div|h\d|tr)>/gi, "\n")
    description = decodeHtmlEntities(stripTags(withBreaks)).replace(/\n{3,}/g, "\n\n").trim() || null

    const locInContent = description?.match(/근무지\s*:\s*([^\n•]+)/)
    if (locInContent) location = locInContent[1].trim()
  }

  if (!location) {
    const condMatch = html.match(/class="job_condition"[^>]*>([\s\S]*?)<\/div>/i)
    if (condMatch) {
      const text = clean(condMatch[1])
      const area = text.match(/^([\p{L}\s·]+(?:구|시|도|군)[^\d]*)/u)
      location = area ? area[1].trim() : text.split(/\s{2,}/)[0] || null
    }
  }

  let deadline: string | null = null
  const dlMatch =
    html.match(/마감일\s*(\d{4}\.\d{2}\.\d{2}(?:\s*\d{1,2}:\d{2})?)/i) ||
    html.match(/"closing_date"\s*:\s*"([^"]+)"/) ||
    html.match(/마감일[^0-9]*(\d{4}\.\d{2}\.\d{2}[^"<]*)/i) ||
    html.match(
      /접수기간\s*[:：]?\s*(\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일\s*[~～\-]\s*\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일(?:\s*\d{1,2}\s*시)?)/i,
    ) ||
    html.match(/접수기간\s*[:：]?\s*([^<\n]{10,80}?)(?:\s*제출서류|\s*접수방법)/i)
  if (dlMatch) {
    deadline = clean(dlMatch[1]) || null
    if (deadline) deadline = deadline.replace(/\s+/g, " ").trim()
  }

  let employmentType: string | null = null
  const empMatch = html.match(/고용형태[^:：]*[:：]\s*([^<\n]+)/i)
  if (empMatch) employmentType = clean(empMatch[1]) || null

  let date: string | null = null
  const regMatch = html.match(/등록일[^0-9]*(\d{2}\/\d{2}|\d{4}\.\d{2}\.\d{2})/i)
  if (regMatch) date = regMatch[1]

  return {
    id,
    title,
    company,
    location,
    date,
    url: `${BASE_URL}/zf_user/jobs/view?rec_idx=${id}`,
    description,
    deadline,
    employmentType,
  }
}

export function normalizeId(input: string): string | null {
  const url = input.match(/rec_idx=(\d+)/)
  if (url) return url[1]
  if (/^\d+$/.test(input)) return input
  return null
}

export function buildDetailUrl(id: string): string {
  return `${BASE_URL}/zf_user/jobs/view?rec_idx=${id}`
}
