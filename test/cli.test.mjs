import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const CLI = join(ROOT, "bin", "scifig.mjs");
const SOURCE = join(ROOT, "skills", "scifig");
const VERSION = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")).version;
const MANIFEST = ".scifig-install.json";
const IGNORED = new Set(["__pycache__", ".DS_Store"]);

function makeHome(...markers) {
  const home = mkdtempSync(join(tmpdir(), "scifig-home-"));
  for (const marker of markers) mkdirSync(join(home, marker), { recursive: true });
  return home;
}

// stdin is a pipe here, so the CLI always runs non-interactively.
function run(home, args, env = {}) {
  return spawnSync(process.execPath, [CLI, ...args], {
    encoding: "utf8",
    env: { PATH: process.env.PATH, HOME: home, USERPROFILE: home, ...env },
  });
}

function json(result) {
  assert.equal(result.stderr, "", "stderr should be empty");
  return JSON.parse(result.stdout);
}

function listFiles(dir, prefix = "") {
  return readdirSync(join(dir, prefix), { withFileTypes: true }).flatMap((entry) => {
    if (IGNORED.has(entry.name) || entry.name.endsWith(".pyc")) return [];
    const rel = join(prefix, entry.name);
    return entry.isDirectory() ? listFiles(dir, rel) : [rel];
  });
}

const codexTarget = (home) => join(home, ".agents", "skills", "scifig");
const antigravityTarget = (home) => join(home, ".gemini", "config", "skills", "scifig");

// The 29 agents setup detects, in the order and with the ids it uses.
const SUPPORTED_CLIENTS = [
  "claude_code", "claude_desktop", "codex", "cursor", "codebuddy", "cline", "gemini_cli", "windsurf", "devin",
  "opencode", "antigravity", "copilot_cli", "commandcode", "qwen_code", "kimi", "vscode", "trae", "workbuddy",
  "lm_studio", "grok_build", "omp", "pi", "hermes", "qoder", "droid", "zcode", "dsh", "freebuff", "grok_bot",
];
const shared = (home) => join(home, ".agents", "skills", "scifig");
const plan = (home, args, env) => json(run(home, ["setup", "--dry-run", "--json", ...args], env)).targets.map(({ client, clients, path }) => ({ client, clients, path }));

test("setup --dry-run plans an install for every detected agent and writes nothing", () => {
  const home = makeHome(".codex", ".gemini/config");
  const result = run(home, ["setup", "--dry-run", "--json"]);
  assert.equal(result.status, 0);
  const out = json(result);
  assert.equal(out.dry_run, true);
  assert.equal(out.applied, false);
  assert.deepEqual(
    out.targets.map(({ client, path, action }) => ({ client, path, action })),
    [
      { client: "shared", path: codexTarget(home), action: "install" },
      { client: "antigravity", path: antigravityTarget(home), action: "install" },
    ],
  );
  assert.equal(existsSync(join(home, ".agents")), false);
  assert.equal(existsSync(join(home, ".gemini", "config", "skills")), false);
});

test("setup --yes copies the whole skill and records a manifest", () => {
  const home = makeHome(".codex");
  const out = json(run(home, ["setup", "--yes", "--json"]));
  assert.equal(out.applied, true);
  const target = codexTarget(home);
  const expected = listFiles(SOURCE);
  assert.ok(expected.length > 0);
  for (const rel of expected) {
    assert.deepEqual(readFileSync(join(target, rel)), readFileSync(join(SOURCE, rel)), rel);
  }
  const manifest = JSON.parse(readFileSync(join(target, MANIFEST), "utf8"));
  assert.equal(manifest.package, "scifig-agents");
  assert.equal(manifest.version, VERSION);
});

test("a second setup reports the install as unchanged and leaves it alone", () => {
  const home = makeHome(".codex");
  run(home, ["setup", "--yes", "--json"]);
  const manifestPath = join(codexTarget(home), MANIFEST);
  const before = readFileSync(manifestPath, "utf8");
  const out = json(run(home, ["setup", "--yes", "--json"]));
  assert.equal(out.targets[0].action, "unchanged");
  assert.equal(out.targets[0].installed_version, VERSION);
  assert.equal(readFileSync(manifestPath, "utf8"), before);
});

test("setup replaces an install whose contents differ from the package", () => {
  const home = makeHome(".codex");
  run(home, ["setup", "--yes", "--json"]);
  const target = codexTarget(home);
  writeFileSync(join(target, "stale.txt"), "left over from an older version");
  const manifest = JSON.parse(readFileSync(join(target, MANIFEST), "utf8"));
  writeFileSync(join(target, MANIFEST), JSON.stringify({ ...manifest, version: "0.0.1", digest: "old" }));

  const out = json(run(home, ["setup", "--yes", "--json"]));
  assert.equal(out.targets[0].action, "update");
  assert.equal(out.targets[0].installed_version, "0.0.1");
  assert.equal(existsSync(join(target, "stale.txt")), false);
  assert.equal(JSON.parse(readFileSync(join(target, MANIFEST), "utf8")).version, VERSION);
});

test("setup refuses to touch a scifig folder it did not install", () => {
  const home = makeHome(".codex");
  const target = codexTarget(home);
  mkdirSync(target, { recursive: true });
  writeFileSync(join(target, "SKILL.md"), "someone else's skill");

  const result = run(home, ["setup", "--yes", "--json"]);
  assert.equal(result.status, 1);
  const out = JSON.parse(result.stdout);
  assert.equal(out.applied, false);
  assert.equal(out.targets[0].action, "blocked");
  assert.equal(readFileSync(join(target, "SKILL.md"), "utf8"), "someone else's skill");
});

test("setup without --yes changes nothing when it cannot ask", () => {
  const home = makeHome(".codex");
  const result = run(home, ["setup"]);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /--yes/);
  assert.equal(existsSync(codexTarget(home)), false);
});

test("setup fails with guidance when no agent is detected", () => {
  const home = makeHome();
  const result = run(home, ["setup", "--yes"]);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /--client/);
});

test("--client claude_code honours CLAUDE_CONFIG_DIR", () => {
  const home = makeHome();
  const configDir = join(home, "custom-claude");
  const out = json(run(home, ["setup", "--client", "claude_code", "--yes", "--json"], { CLAUDE_CONFIG_DIR: configDir }));
  assert.equal(out.targets[0].path, join(configDir, "skills", "scifig"));
  assert.ok(existsSync(join(configDir, "skills", "scifig", MANIFEST)));
});

test("--dir installs into an arbitrary skills folder", () => {
  const home = makeHome();
  const dir = join(home, "elsewhere", "skills");
  const out = json(run(home, ["setup", "--dir", dir, "--yes", "--json"]));
  assert.deepEqual(out.targets.map((t) => t.path), [join(dir, "scifig")]);
  assert.ok(existsSync(join(dir, "scifig", MANIFEST)));
});

test("an unknown client is a usage error", () => {
  const result = run(makeHome(), ["setup", "--client", "nope", "--yes"]);
  assert.equal(result.status, 2);
  assert.match(result.stderr, /nope/);
});

test("uninstall removes installs it made and nothing else", () => {
  const home = makeHome(".codex", ".gemini/config");
  run(home, ["setup", "--client", "codex", "--yes", "--json"]);
  const foreign = antigravityTarget(home);
  mkdirSync(foreign, { recursive: true });
  writeFileSync(join(foreign, "SKILL.md"), "someone else's skill");

  const out = json(run(home, ["uninstall", "--yes", "--json"]));
  assert.deepEqual(
    out.targets.map(({ client, action }) => ({ client, action })),
    [
      { client: "shared", action: "remove" },
      { client: "antigravity", action: "blocked" },
    ],
  );
  assert.equal(existsSync(codexTarget(home)), false);
  assert.ok(existsSync(join(foreign, "SKILL.md")));
});

test("doctor reports the state of every supported agent", () => {
  const home = makeHome(".codex");
  run(home, ["setup", "--yes", "--json"]);
  const out = json(run(home, ["doctor", "--json"]));
  const byClient = Object.fromEntries(out.clients.map((c) => [c.client, c]));
  assert.deepEqual(Object.keys(byClient), SUPPORTED_CLIENTS);
  assert.equal(byClient.codex.detected, true);
  assert.equal(byClient.codex.state, "installed");
  assert.equal(byClient.codex.installed_version, VERSION);
  assert.equal(byClient.codex.up_to_date, true);
  assert.equal(byClient.antigravity.detected, false);
  assert.equal(byClient.antigravity.state, "not_installed");
  assert.ok("uv" in out.tools);
});

test("doctor says what still works in an agent without an image tool", () => {
  const result = run(makeHome(".claude"), ["doctor"]);
  assert.equal(result.status, 0);
  const line = result.stdout.split("\n").find((text) => text.includes("Claude Code"));
  assert.match(line, /no built-in image tool \(diagrams, charts, export and checks still work\)/);
});

test("doctor lists the 29 supported agents in order, with their ids", () => {
  const out = json(run(makeHome(), ["doctor", "--json"]));
  assert.deepEqual(out.clients.map(({ client }) => client), SUPPORTED_CLIENTS);
});

test("agents without a skills folder of their own share one copy in ~/.agents/skills", () => {
  const home = makeHome(".codex", ".cursor", ".codeium/windsurf");

  assert.deepEqual(plan(home, []), [{ client: "shared", clients: ["codex", "cursor", "windsurf"], path: shared(home) }]);
});

test("an agent with a skills folder of its own gets the skill there", () => {
  const home = makeHome(".codebuddy", ".workbuddy", ".zcode/cli", ".factory", ".qoder");

  assert.deepEqual(plan(home, []), [
    { client: "codebuddy", clients: ["codebuddy"], path: join(home, ".codebuddy", "skills", "scifig") },
    { client: "workbuddy", clients: ["workbuddy"], path: join(home, ".workbuddy", "skills", "scifig") },
    { client: "qoder", clients: ["qoder"], path: join(home, ".qoder", "skills", "scifig") },
    { client: "droid", clients: ["droid"], path: join(home, ".factory", "skills", "scifig") },
    { client: "zcode", clients: ["zcode"], path: join(home, ".zcode", "skills", "scifig") },
  ]);
});

test("an Antigravity folder counts as Gemini CLI's too", () => {
  const home = makeHome(".gemini/config");

  assert.deepEqual(plan(home, []), [
    { client: "shared", clients: ["gemini_cli"], path: shared(home) },
    { client: "antigravity", clients: ["antigravity"], path: antigravityTarget(home) },
  ]);
});

test("an agent is found by its configuration file as well as by its folder", () => {
  const home = makeHome();
  writeFileSync(join(home, ".claude.json"), "{}");

  assert.deepEqual(plan(home, []), [{ client: "claude_code", clients: ["claude_code"], path: join(home, ".claude", "skills", "scifig") }]);
});

test("the agents' folder overrides in the environment are honoured", () => {
  const home = makeHome();
  const env = { QODER_CONFIG_DIR: join(home, "q"), FACTORY_HOME_OVERRIDE: join(home, "f"), GEMINI_CLI_HOME: join(home, "g"), DSH_AGENTS_HOME: join(home, "d") };

  assert.deepEqual(plan(home, ["--client", "qoder", "--client", "droid", "--client", "gemini_cli", "--client", "dsh"], env), [
    { client: "gemini_cli", clients: ["gemini_cli"], path: join(home, "g", ".agents", "skills", "scifig") },
    { client: "qoder", clients: ["qoder"], path: join(home, "q", "skills", "scifig") },
    { client: "droid", clients: ["droid"], path: join(home, "f", ".factory", "skills", "scifig") },
    { client: "dsh", clients: ["dsh"], path: join(home, "d", "skills", "scifig") },
  ]);
});

test("doctor lists the agents it found and names the others", () => {
  const result = run(makeHome(".codex"), ["doctor"]);
  const lines = result.stdout.split("\n");

  assert.ok(lines.some((line) => /^\s+Codex\s+found/.test(line)));
  assert.match(lines.find((line) => line.includes("Not found:")), /Cursor/);
});

test("--help lists --accessible", () => {
  const result = run(makeHome(), ["--help"]);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /--accessible\s+Ask about one folder at a time instead of showing a list/);
});

test("--accessible changes nothing about a setup that cannot ask", () => {
  const home = makeHome(".codex");
  const out = json(run(home, ["setup", "--accessible", "--yes", "--json"]));
  assert.equal(out.applied, true);
  assert.ok(existsSync(join(codexTarget(home), "SKILL.md")));
});

test("--version prints the package version", () => {
  const result = run(makeHome(), ["--version"]);
  assert.equal(result.status, 0);
  assert.equal(result.stdout.trim(), VERSION);
});

test("setup --json without --yes still prints the plan as JSON when it cannot ask", () => {
  const home = makeHome(".codex");
  const result = run(home, ["setup", "--json"]);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /--yes/);
  const out = JSON.parse(result.stdout);
  assert.equal(out.applied, false);
  assert.equal(out.targets[0].action, "install");
  assert.equal(existsSync(codexTarget(home)), false);
});

test("a blocked folder stops the whole setup and says how to go on", () => {
  const home = makeHome(".codex", ".gemini/config");
  mkdirSync(codexTarget(home), { recursive: true });
  writeFileSync(join(codexTarget(home), "SKILL.md"), "someone else's skill");

  const result = run(home, ["setup", "--yes"]);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /blocked\s+Shared folder/);
  assert.match(result.stdout, /read by Codex, Gemini CLI/);
  assert.match(result.stdout, /--client/);
  assert.equal(existsSync(antigravityTarget(home)), false);
});
