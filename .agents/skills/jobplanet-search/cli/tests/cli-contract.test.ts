import { describe, expect, test } from "bun:test"
import { runCLI, parseJSON, venvReady } from "./helpers"

describe("JobPlanet CLI error contract", () => {
  test("search without query fails", async () => {
    const result = await runCLI(["search"])
    expect(result.exitCode).toBe(1)
    expect(JSON.parse(result.stderr).code).toBe("NO_QUERY")
  })

  test("detail without id fails", async () => {
    const result = await runCLI(["detail"])
    expect(result.exitCode).toBe(1)
    expect(JSON.parse(result.stderr).code).toBe("NO_ID")
  })

  test("missing venv returns NO_VENV", async () => {
    if (venvReady()) return
    const result = await runCLI(["search", "--query", "python", "--limit", "1"])
    expect(result.exitCode).toBe(1)
    expect(JSON.parse(result.stderr).code).toBe("NO_VENV")
  })
})

describe("JobPlanet CLI live smoke", () => {
  test("search returns structured results", async () => {
    if (!venvReady()) {
      console.warn("skip live smoke: run `bun run setup` in jobplanet-search/cli first")
      return
    }
    const result = await runCLI(["search", "--query", "Linux", "--limit", "2", "--format", "json"])
    const data = parseJSON<{ meta: { count: number }; results: Array<{ id: string; title: string; url: string }> }>(
      result,
    )
    expect(data.results.length).toBeGreaterThan(0)
    expect(data.results[0].id).toMatch(/^\d+$/)
    expect(data.results[0].title.length).toBeGreaterThan(0)
    expect(data.results[0].url).toContain("jobplanet.co.kr")
  }, 120000)
})
