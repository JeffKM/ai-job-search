import { describe, expect, test } from "bun:test"
import { runCLI, parseJSON } from "./helpers"

describe("Saramin CLI error contract", () => {
  test("search without query fails", async () => {
    const result = await runCLI(["search"])
    expect(result.exitCode).toBe(1)
    expect(JSON.parse(result.stderr)).toEqual({ error: "--query is required", code: "NO_QUERY" })
  })

  test("detail without id fails", async () => {
    const result = await runCLI(["detail"])
    expect(result.exitCode).toBe(1)
    expect(JSON.parse(result.stderr).code).toBe("NO_ID")
  })
})

describe("Saramin CLI live smoke", () => {
  test("search returns results", async () => {
    const result = await runCLI(["search", "--query", "python", "--limit", "3"])
    const data = parseJSON<{ results: Array<{ id: string; title: string; url: string }> }>(result)
    expect(data.results.length).toBeGreaterThan(0)
    expect(data.results[0].id).toMatch(/^\d+$/)
    expect(data.results[0].url).toContain("saramin.co.kr")
  })
})
