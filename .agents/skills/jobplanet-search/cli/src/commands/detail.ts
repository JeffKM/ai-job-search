import { runPython, writeError } from "../helpers.js"

export interface DetailOpts {
  id: string
  format: "json" | "plain"
}

function normalizeId(input: string): string | null {
  const url = input.match(/posting_ids(?:%5B%5D|\[\])=(\d+)/) || input.match(/job_postings\/(\d+)/)
  if (url) return url[1]
  if (/^\d+$/.test(input)) return input
  return null
}

export async function runDetail(opts: DetailOpts): Promise<number> {
  const id = normalizeId(opts.id)
  if (!id) {
    writeError(`Could not parse a posting id from "${opts.id}"`, "BAD_ID")
    return 1
  }

  const result = await runPython(["detail", id, "--format", opts.format])
  if (result.exitCode !== 0) {
    if (result.stderr) process.stderr.write(result.stderr + (result.stderr.endsWith("\n") ? "" : "\n"))
    else writeError("JobPlanet detail failed", "DETAIL_FAILED")
    return 1
  }

  process.stdout.write(result.stdout + "\n")
  return 0
}
