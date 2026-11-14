import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL(".", import.meta.url));
const python = path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
if (!existsSync(python)) {
  console.error("Python environment missing. See the backend setup steps in README.md.");
  process.exit(1);
}
const server = spawn(python, ["-m", "uvicorn", "app.main:app", "--reload", "--reload-dir", "app", "--host", "127.0.0.1", "--port", "8000"], {
  cwd: root, stdio: "inherit",
});
server.on("error", error => { console.error(error.message); process.exitCode = 1; });
server.on("exit", code => { process.exitCode = code ?? 0; });
process.on("SIGINT", () => server.kill("SIGINT"));
process.on("SIGTERM", () => server.kill("SIGTERM"));
