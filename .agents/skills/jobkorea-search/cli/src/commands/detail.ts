import {
  buildDetailUrl,
  htmlFetch,
  normalizeId,
  parseJobDetail,
  writeError,
  decodeHtmlEntities,
} from "../helpers.js"

async function fetchDescriptionBody(url: string | null | undefined): Promise<string | null> {
  if (!url) return null
  try {
    const html = await htmlFetch(url)
    if (!html) return null
    const text = decodeHtmlEntities(
      html
        .replace(/<\s*br\s*\/?>/gi, "\n")
        .replace(/<\/(p|li|ul|ol|div|h\d|tr)>/gi, "\n")
        .replace(/<[^>]+>/g, " "),
    )
      .replace(/\n{3,}/g, "\n\n")
      .trim()
    return text || null
  } catch {
    return null
  }
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
    const body = await fetchDescriptionBody(job.descriptionUrl)
    if (body) {
      // Keep short meta summary, then full body (skills still in job.skills)
      job.description = job.description ? `${job.description}\n\n${body}` : body
    }
    // Fold explicit skill chips into description so generic enrichers see them
    if (job.skills && job.skills.length > 0) {
      const skillLine = `기술스택: ${job.skills.join(", ")}`
      job.description = job.description ? `${job.description}\n\n${skillLine}` : skillLine
    }

    if (opts.format === "plain") {
      const lines = [
        job.title,
        `${job.company || "—"} · ${job.location || "—"}`,
        job.deadline ? `Deadline: ${job.deadline}` : "",
        job.employmentType ? `Employment: ${job.employmentType}` : "",
        job.skills?.length ? `Skills: ${job.skills.join(", ")}` : "",
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
    writeError(msg, msg.includes("parse") ? "PARSE_ERROR" : "DETAIL_FAILED")
    return 1
  }
}
