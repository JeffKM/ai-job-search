export const BASE_URL = "https://www.wanted.co.kr"
export const SEARCH_URL = `${BASE_URL}/api/chaos/navigation/v1/results`
export const DETAIL_URL = `${BASE_URL}/api/chaos/jobs/v4`

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

export async function jsonFetch<T>(url: string): Promise<T> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": UA,
        Accept: "application/json",
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
    if (response.status === 404) {
      throw new Error("Job not found")
    }
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`)
    }
    return response.json() as Promise<T>
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
  seniority: string | null
  status: string | null
}

interface WantedSearchRow {
  id?: number
  position?: string
  due_time?: string | null
  company?: { name?: string }
  address?: { location?: string; district?: string; country?: string; full_location?: string }
}

interface WantedSearchResponse {
  data?: WantedSearchRow[]
}

interface WantedDetailResponse {
  data?: {
    job?: {
      id?: number
      status?: string
      due_time?: string | null
      detail?: {
        position?: string
        intro?: string
        main_tasks?: string
        requirements?: string
        preferred_points?: string
        benefits?: string
      }
      address?: { location?: string; district?: string; full_location?: string }
      company?: { name?: string }
    }
  }
}

function formatLocation(address?: WantedSearchRow["address"]): string | null {
  if (!address) return null
  if (address.full_location) return address.full_location
  const parts = [address.location, address.district].filter(Boolean)
  return parts.length > 0 ? parts.join(" ") : null
}

export function parseSearchRows(rows: WantedSearchRow[]): JobCard[] {
  const results: JobCard[] = []
  for (const row of rows) {
    if (row.id == null || !row.position) continue
    const id = String(row.id)
    results.push({
      id,
      title: row.position,
      company: row.company?.name ?? null,
      location: formatLocation(row.address),
      date: null,
      url: `${BASE_URL}/wd/${id}`,
    })
  }
  return results
}

export function filterByQuery(cards: JobCard[], query?: string): JobCard[] {
  if (!query?.trim()) return cards
  const q = query.trim().toLowerCase()
  return cards.filter((c) => {
    const hay = `${c.title} ${c.company ?? ""}`.toLowerCase()
    return hay.includes(q)
  })
}

export async function fetchSearchPage(opts: {
  query?: string
  page: number
  limit: number
  location?: string
}): Promise<JobCard[]> {
  const params = new URLSearchParams({
    country: "kr",
    years: "-1",
    locations: opts.location?.trim() || "all",
    job_sort: "job.latest_order",
    limit: String(Math.min(Math.max(opts.limit, 1), 100)),
    offset: String((opts.page - 1) * opts.limit),
  })
  if (opts.query?.trim()) params.set("query", opts.query.trim())

  const payload = await jsonFetch<WantedSearchResponse>(`${SEARCH_URL}?${params.toString()}`)
  return parseSearchRows(payload.data ?? [])
}

function joinSections(parts: Array<string | undefined | null>): string | null {
  const text = parts
    .map((p) => (p ?? "").trim())
    .filter(Boolean)
    .join("\n\n")
  return text || null
}

export async function fetchJobDetail(id: string): Promise<JobDetail> {
  const payload = await jsonFetch<WantedDetailResponse>(`${DETAIL_URL}/${id}/details`)
  const job = payload.data?.job
  if (!job?.id) throw new Error("Job not found")

  const detail = job.detail
  const annualFrom = (job as { annual_from?: number }).annual_from
  const annualTo = (job as { annual_to?: number }).annual_to
  let seniority: string | null = null
  if (annualFrom != null || annualTo != null) {
    if (annualFrom != null && annualTo != null) seniority = `경력 ${annualFrom}–${annualTo}년`
    else if (annualFrom != null) seniority = `경력 ${annualFrom}년+`
    else if (annualTo != null) seniority = `경력 ${annualTo}년 이하`
  }

  const jobId = String(job.id)
  return {
    id: jobId,
    title: detail?.position ?? "(untitled)",
    company: job.company?.name ?? null,
    location: formatLocation(job.address),
    date: null,
    url: `${BASE_URL}/wd/${jobId}`,
    description: joinSections([
      detail?.intro,
      detail?.main_tasks ? `[주요업무]\n${detail.main_tasks}` : null,
      detail?.requirements ? `[자격요건]\n${detail.requirements}` : null,
      detail?.preferred_points ? `[우대사항]\n${detail.preferred_points}` : null,
      detail?.benefits ? `[혜택]\n${detail.benefits}` : null,
    ]),
    deadline: job.due_time ?? null,
    employmentType: null,
    seniority,
    status: job.status ?? null,
  }
}

export function normalizeId(input: string): string | null {
  const url = input.match(/\/wd\/(\d+)/)
  if (url) return url[1]
  if (/^\d+$/.test(input)) return input
  return null
}
