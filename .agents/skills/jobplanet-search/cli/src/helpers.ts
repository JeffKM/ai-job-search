import { join } from "path"
import { existsSync } from "fs"

const CLI_ROOT = join(import.meta.dir, "..")
const FETCH_DIR = join(CLI_ROOT, "..", "fetch")
const VENV_PYTHON = join(FETCH_DIR, ".venv", "bin", "python")
const FETCH_SCRIPT = join(FETCH_DIR, "fetch.py")

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

export function pythonPath(): string {
  if (existsSync(VENV_PYTHON)) return VENV_PYTHON
  writeError(
    "JobPlanet fetch venv not found. Run: cd .agents/skills/jobplanet-search/cli && bun run setup",
    "NO_VENV",
  )
  process.exit(1)
}

export interface RunPythonResult {
  stdout: string
  stderr: string
  exitCode: number
}

export async function runPython(args: string[]): Promise<RunPythonResult> {
  const python = pythonPath()
  const proc = Bun.spawn([python, FETCH_SCRIPT, ...args], {
    cwd: FETCH_DIR,
    stdout: "pipe",
    stderr: "pipe",
  })
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ])
  return { stdout: stdout.trim(), stderr: stderr.trim(), exitCode }
}

export function renderTable(results: Array<Record<string, string | null>>): string {
  if (results.length === 0) return "No results."
  const rows = results.map((c) => {
    const id = String(c.id ?? "").padEnd(10)
    const title = String(c.title ?? "").slice(0, 34).padEnd(34)
    const company = String(c.company ?? "—").slice(0, 18).padEnd(18)
    const loc = String(c.location ?? "—").slice(0, 16).padEnd(16)
    return `${id} ${title} ${company} ${loc}`
  })
  const header =
    "ID".padEnd(10) + " " + "TITLE".padEnd(34) + " " + "COMPANY".padEnd(18) + " " + "LOCATION".padEnd(16)
  return [header, "-".repeat(header.length), ...rows].join("\n")
}

export function skillRoot(): string {
  return join(CLI_ROOT, "..")
}
