import {
  buildSearchUrl,
  htmlFetch,
  parseSearchResults,
  writeError,
  type JobCard,
} from "../helpers.js"
import {
  companyTypeFilterMeta,
  filterByCompanyType,
  jobkoreaTab,
  type CompanyType,
} from "../../../../shared/kr-company-type.js"

export interface SearchOpts {
  query: string
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
    return `${c.id.padEnd(10)} ${title} ${company} ${loc}`
  })
  const header =
    "ID".padEnd(10) + " " + "TITLE".padEnd(36) + " " + "COMPANY".padEnd(20) + " " + "LOCATION".padEnd(16)
  return [header, "-".repeat(header.length), ...rows].join("\n")
}

export async function runSearch(opts: SearchOpts): Promise<number> {
  try {
    const tab = opts.companyType ? jobkoreaTab(opts.companyType) : undefined
    const html = await htmlFetch(buildSearchUrl(opts.query, opts.page, tab))
    let cards = parseSearchResults(html)
    if (opts.companyType) {
      cards = filterByCompanyType(cards, opts.companyType)
    }
    if (opts.limit !== undefined && opts.limit >= 0) {
      cards = cards.slice(0, opts.limit)
    }

    const meta = {
      count: cards.length,
      page: opts.page,
      ...(opts.companyType ? companyTypeFilterMeta(opts.companyType, tab ? "native" : "client") : {}),
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
