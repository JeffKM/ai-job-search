import {
  buildDetailUrl,
  htmlFetch,
  normalizeId,
  parseJobDetail,
  writeError,
} from "../helpers.js"

export interface DetailOpts {
  id: string
  format: "json" | "plain"
}

export async function runDetail(opts: DetailOpts): Promise<number> {
  const id = normalizeId(opts.id)
  if (!id) {
    writeError(`Could not parse a job ID from "${opts.id}"`, "BAD_ID")
    return 1
  }

  try {
    const html = await htmlFetch(buildDetailUrl(id))
    if (!html) {
      writeError("Job not found", "NOT_FOUND")
      return 1
    }
    const job = parseJobDetail(html, id)

    if (opts.format === "plain") {
      const lines = [
        job.title,
        `${job.company || "—"} · ${job.location || "—"}`,
        job.deadline ? `Deadline: ${job.deadline}` : "",
        job.employmentType ? `Employment: ${job.employmentType}` : "",
        "",
        job.description || "(no description)",
        "",
        `URL: ${job.url}`,
      ].filter((l) => l !== "")
      process.stdout.write(lines.join("\n") + "\n")
    } else {
      process.stdout.write(JSON.stringify(job) + "\n")
    }
    return 0
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    writeError(msg.includes("parse") ? msg : msg, msg.includes("parse") ? "PARSE_ERROR" : "DETAIL_FAILED")
    return 1
  }
}
