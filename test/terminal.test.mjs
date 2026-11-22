import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { stripVTControlCharacters } from "node:util";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const CLI = join(ROOT, "bin", "scifig.mjs");
const VERSION = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")).version;
// Python's pty module gives the CLI a real terminal, on macOS and Linux alike, and passes our keys on to it.
const PTY = "import pty, sys; sys.exit(pty.spawn(sys.argv[1:]) >> 8)";
const skip = process.platform === "win32" || spawnSync("python3", ["-c", "import pty"]).status !== 0 ? "needs python3 and a pty" : false;

function makeHome(...markers) {
  const home = mkdtempSync(join(tmpdir(), "scifig-home-"));
  for (const marker of markers) mkdirSync(join(home, marker), { recursive: true });
  return home;
}

const env = (home) => ({ PATH: process.env.PATH, HOME: home, USERPROFILE: home });

/**
 * Runs the CLI in a 100x40 terminal and types each step's keys once the step's text has appeared.
 * Resolves with the exit code and the screen as plain text.
 */
function runInTerminal(home, args, steps) {
  return new Promise((resolve, reject) => {
    // A new pty is 0x0, which clack would wrap after every character; give it a size first.
    const command = `stty cols 100 rows 40 && exec "${process.execPath}" "${CLI}" ${args.join(" ")}`;
    const child = spawn("python3", ["-c", PTY, "sh", "-c", command], { env: env(home) });
    let screen = "";
    let from = 0;
    let next = 0;
    child.stdout.on("data", (data) => {
      screen += data;
      const text = stripVTControlCharacters(screen);
      while (next < steps.length) {
        const [want, keys] = steps[next];
        const at = text.indexOf(want, from);
        if (at === -1) break;
        from = at + want.length;
        next += 1;
        setTimeout(() => child.stdin.write(keys), 50);
      }
    });
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error(`no exit within 20 s; the screen was:\n${stripVTControlCharacters(screen)}`));
    }, 20_000);
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, screen: stripVTControlCharacters(screen) });
    });
  });
}

test("in a terminal, setup lists the folders, ticks those of the agents found, and installs after two Enters", { skip }, async () => {
  const home = makeHome(".codex", ".gemini/config");
  const { code, screen } = await runInTerminal(home, ["setup"], [
    ["Which skills folders should get scifig?", "\r"],
    ["Apply these 2 changes?", "\r"],
  ]);
  assert.equal(code, 0, screen);
  assert.match(screen, /Found: Codex, Gemini CLI, and Antigravity/);
  assert.ok(existsSync(join(home, ".agents", "skills", "scifig", "SKILL.md")));
  assert.ok(existsSync(join(home, ".gemini", "config", "skills", "scifig", "SKILL.md")));
  assert.equal(existsSync(join(home, ".claude", "skills", "scifig")), false);
});

test("in a terminal, uninstall shows what it will remove and asks first", { skip }, async () => {
  const home = makeHome(".codex");
  assert.equal(spawnSync(process.execPath, [CLI, "setup", "--yes"], { env: env(home) }).status, 0);
  const { code, screen } = await runInTerminal(home, ["uninstall"], [["Remove this copy?", "\r"]]);
  assert.equal(code, 0, screen);
  assert.ok(screen.includes(`REMOVE  Shared folder · ${VERSION}`), screen);
  assert.equal(existsSync(join(home, ".agents", "skills", "scifig")), false);
});
