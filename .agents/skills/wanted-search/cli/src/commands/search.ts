import {
  fetchSearchPage,
  filterByQuery,
  writeError,
  type JobCard,
} from "../helpers.js"
import {
  companyTypeFilterMeta,
  filterByCompanyType,
  type CompanyType,
} from "../../../../shared/kr-company-type.js"

export interface SearchOpts {
  query?: string
  location?: string
  page: number
  limit?: number
  companyType?: CompanyType
  format: "json" | "table" | "plain"
}

function renderTable(cards: JobCard[]): string {
  if (cards.length === 0) return "No results."
  const rows = cards.map((c) => {
    const title = (c.title || "").slice(0, 36).padEnd(36)
    const company = (c.company || "—").slice(0, 20).padEnd(20)
    const loc = (c.location || "—").slice(0, 16).padEnd(16)
    return `${c.id.padEnd(8)} ${title} ${company} ${loc}`
  })
  const header =
    "ID".padEnd(8) + " " + "TITLE".padEnd(36) + " " + "COMPANY".padEnd(20) + " " + "LOCATION".padEnd(16)
  return [header, "-".repeat(header.length), ...rows].join("\n")
}

export async function runSearch(opts: SearchOpts): Promise<number> {
  try {
    const pageSize = opts.limit && opts.limit > 0 ? Math.min(opts.limit, 100) : 20
    let cards = await fetchSearchPage({
      query: opts.query,
      page: opts.page,
      limit: pageSize,
      location: opts.location,
    })

    if (opts.query?.trim()) {
      const filtered = filterByQuery(cards, opts.query)
      if (filtered.length > 0) cards = filtered
    }

    if (opts.companyType) {
      cards = filterByCompanyType(cards, opts.companyType)
    }

    if (opts.limit !== undefined && opts.limit >= 0) {
      cards = cards.slice(0, opts.limit)
    }

    const meta = {
      count: cards.length,
      page: opts.page,
      ...(opts.companyType ? companyTypeFilterMeta(opts.companyType, "client") : {}),
    }

    if (opts.format === "table") {
      process.stdout.write(renderTable(cards) + "\n")
    } else if (opts.format === "plain") {
      process.stdout.write(
        cards
          .map(
            (c) =>
              `${c.title}\n  ${c.company || "—"} · ${c.location || "—"}\n  id: ${c.id}\n  ${c.url}`,
          )
          .join("\n\n") + "\n",
      )
    } else {
      process.stdout.write(JSON.stringify({ meta, results: cards }, null, 2) + "\n")
    }
    return 0
  } catch (e) {
    writeError(e instanceof Error ? e.message : String(e), "SEARCH_FAILED")
    return 1
  }
}
