import { describe, expect, test } from "bun:test"
import { runCLI, parseJSON } from "./helpers"

describe("Wanted CLI error contract", () => {
  test("detail without an ID fails with JSON on stderr", async () => {
    const result = await runCLI(["detail"])
    expect(result.exitCode).toBe(1)
    expect(result.stdout).toBe("")
    expect(JSON.parse(result.stderr)).toEqual({
      error: "detail requires an <id|url>",
      code: "NO_ID",
    })
  })

  test("invalid page flag fails before making a request", async () => {
    const result = await runCLI(["search", "--query", "developer", "--page", "nope"])
    expect(result.exitCode).toBe(1)
    expect(JSON.parse(result.stderr).code).toBe("BAD_ARG")
  })
})

describe("Wanted CLI live smoke", () => {
  test("search returns structured results", async () => {
    const result = await runCLI(["search", "--query", "개발", "--limit", "3", "--format", "json"])
    const data = parseJSON<{ meta: { count: number }; results: Array<{ id: string; title: string; url: string }> }>(
      result,
    )
    expect(data.results.length).toBeGreaterThan(0)
    expect(data.results[0].id).toMatch(/^\d+$/)
    expect(data.results[0].title.length).toBeGreaterThan(0)
    expect(data.results[0].url).toContain("wanted.co.kr/wd/")
  })
})
