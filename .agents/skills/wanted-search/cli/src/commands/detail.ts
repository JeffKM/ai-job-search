import { fetchJobDetail, normalizeId, writeError } from "../helpers.js"

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
    const job = await fetchJobDetail(id)

    if (opts.format === "plain") {
      const lines = [
        job.title,
        `${job.company || "—"} · ${job.location || "—"}`,
        job.seniority ? `Seniority: ${job.seniority}` : "",
        job.deadline ? `Deadline: ${job.deadline}` : "",
        job.status ? `Status: ${job.status}` : "",
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
    if (msg.includes("not found")) {
      writeError("Job not found", "NOT_FOUND")
    } else {
      writeError(msg, "DETAIL_FAILED")
    }
    return 1
  }
}
