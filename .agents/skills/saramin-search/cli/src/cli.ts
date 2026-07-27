#!/usr/bin/env bun

import { runSearch, type SearchOpts } from "./commands/search.js"
import { runDetail, type DetailOpts } from "./commands/detail.js"
import { COMPANY_TYPE_HELP, parseCompanyType } from "../../../shared/kr-company-type.js"

interface Flags {
  _: string[]
  [k: string]: string | boolean | string[]
}

function parseFlags(argv: string[]): Flags {
  const flags: Flags = { _: [] }
  const alias: Record<string, string> = { q: "query", n: "limit", t: "company-type" }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a.startsWith("--") || a.startsWith("-")) {
      const key = alias[a.replace(/^-+/, "")] ?? a.replace(/^-+/, "")
      const next = argv[i + 1]
      if (next === undefined || next.startsWith("-")) flags[key] = true
      else {
        flags[key] = next
        i++
      }
    } else {
      ;(flags._ as string[]).push(a)
    }
  }
  return flags
}

const HELP = `saramin-cli — search jobs on Saramin (사람인), South Korea

USAGE
  bun run src/cli.ts search --query "<keywords>" [flags]
  bun run src/cli.ts detail <id|url> [--format json|plain]

SEARCH FLAGS
  --query, -q <text>   Keywords. REQUIRED.
  --page <n>           1-indexed page (default 1).
  --limit, -n <n>      Cap results (client-side).
  --company-type, -t   Filter by company size: ${COMPANY_TYPE_HELP}
  --format <fmt>       json (default) | table | plain.

EXAMPLES
  bun run src/cli.ts search -q "python" --format table
  bun run src/cli.ts search -q "백엔드 개발자" --page 2 --limit 10
  bun run src/cli.ts search -q "python" --company-type major --format table
  bun run src/cli.ts detail 54519167 --format plain

Personal use only — keep request volume low.
`

async function main(): Promise<number> {
  const argv = process.argv.slice(2)
  const flags = parseFlags(argv)
  const cmd = (flags._ as string[])[0]

  if (!cmd || flags.help || flags.h) {
    process.stdout.write(HELP)
    return cmd ? 0 : 1
  }

  if (cmd === "search") {
    const query = typeof flags.query === "string" ? flags.query : undefined
    if (!query) {
      process.stderr.write(JSON.stringify({ error: "--query is required", code: "NO_QUERY" }) + "\n")
      return 1
    }

    const parseIntFlag = (name: string, raw: string | boolean | string[]): number | null => {
      const val = parseInt(raw as string, 10)
      if (isNaN(val)) {
        process.stderr.write(JSON.stringify({ error: `--${name} must be a number`, code: "BAD_ARG" }) + "\n")
        return null
      }
      return val
    }

    if (flags.page !== undefined) {
      const v = parseIntFlag("page", flags.page)
      if (v === null) return 1
      flags.page = String(v)
    }
    if (flags.limit !== undefined) {
      const v = parseIntFlag("limit", flags.limit)
      if (v === null) return 1
      flags.limit = String(v)
    }

    const fmt = (flags.format as string) || "json"
    let companyType: SearchOpts["companyType"]
    if (flags["company-type"] !== undefined) {
      const parsed = parseCompanyType(flags["company-type"] as string)
      if (!parsed) {
        process.stderr.write(
          JSON.stringify({ error: `Invalid --company-type (use: ${COMPANY_TYPE_HELP})`, code: "BAD_COMPANY_TYPE" }) +
            "\n",
        )
        return 1
      }
      companyType = parsed
    }

    const opts: SearchOpts = {
      query,
      page: flags.page ? Math.max(1, parseInt(flags.page as string, 10)) : 1,
      limit: flags.limit ? parseInt(flags.limit as string, 10) : undefined,
      companyType,
      format: (["json", "table", "plain"].includes(fmt) ? fmt : "json") as SearchOpts["format"],
    }
    return runSearch(opts)
  }

  if (cmd === "detail") {
    const id = (flags._ as string[])[1]
    if (!id) {
      process.stderr.write(JSON.stringify({ error: "detail requires an <id|url>", code: "NO_ID" }) + "\n")
      return 1
    }
    const fmt = (flags.format as string) || "json"
    return runDetail({ id, format: fmt === "plain" ? "plain" : "json" })
  }

  process.stderr.write(JSON.stringify({ error: `Unknown command "${cmd}"`, code: "BAD_CMD" }) + "\n")
  return 1
}

main()
  .then((code) => process.exit(code))
  .catch((e) => {
    process.stderr.write(JSON.stringify({ error: e instanceof Error ? e.message : String(e), code: "INTERNAL_ERROR" }) + "\n")
    process.exit(1)
  })
