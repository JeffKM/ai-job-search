import { runPython, renderTable, writeError } from "../helpers.js"

export interface SearchOpts {
  query: string
  page: number
  limit?: number
  companyType?: string
  format: "json" | "table" | "plain"
}

export async function runSearch(opts: SearchOpts): Promise<number> {
  const args = ["search", "--query", opts.query, "--page", String(opts.page)]
  if (opts.limit !== undefined) args.push("--limit", String(opts.limit))
  if (opts.companyType) args.push("--company-type", opts.companyType)

  const result = await runPython(args)
  if (result.exitCode !== 0) {
    if (result.stderr) process.stderr.write(result.stderr + (result.stderr.endsWith("\n") ? "" : "\n"))
    else writeError("JobPlanet search failed", "SEARCH_FAILED")
    return 1
  }

  if (opts.format === "json") {
    process.stdout.write(result.stdout + "\n")
    return 0
  }

  try {
    const data = JSON.parse(result.stdout) as {
      results: Array<{ id: string; title: string; company: string | null; location: string | null; date: string | null; url: string }>
    }
    if (opts.format === "table") {
      process.stdout.write(renderTable(data.results) + "\n")
    } else {
      process.stdout.write(
        data.results
          .map(
            (c) =>
              `${c.title}\n  ${c.company || "—"} · ${c.location || "—"} · ${c.date || "—"}\n  id: ${c.id}\n  ${c.url}`,
          )
          .join("\n\n") + "\n",
      )
    }
    return 0
  } catch {
    writeError("Failed to parse search JSON from fetch.py", "PARSE_ERROR")
    return 1
  }
}
