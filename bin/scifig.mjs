#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { createInterface } from "node:readline/promises";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { CLIENTS, isPresent, sharedSkillsDir, skillsDirOf } from "../lib/clients.mjs";
import { SKILL_NAME, applyInstall, applyUninstall, digestTree, planInstall, planUninstall, readManifest } from "../lib/install.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const VERSION = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")).version;
const SOURCE_DIR = join(ROOT, "skills", SKILL_NAME);

/** The agent ids, a few to a line under the option that takes them. */
const CLIENT_IDS = CLIENTS.map((c) => c.id)
  .join(", ")
  .replace(/(.{1,74})(, |$)/g, (_, line, comma) => `                  ${line}${comma ? "," : ""}\n`)
  .trimEnd();

const USAGE = `scifig-agents ${VERSION}

Usage: scifig-agents <command> [options]

Commands:
  setup       Install the scifig skill into your agents
  uninstall   Remove installs made by this tool
  doctor      Show where the skill is installed and what its scripts need

Options:
  --client <id>   An agent to install into (repeatable; default: every agent found):
${CLIENT_IDS}
  --dir <path>    A skills folder to use as well (repeatable)
  --dry-run       Show the plan without changing anything
  --yes           Apply without asking
  --json          Machine-readable output
  --version       Print the version
  --help          Print this help`;

class UsageError extends Error {}

function parse(argv) {
  try {
    return parseArgs({
      args: argv,
      allowPositionals: true,
      options: {
        client: { type: "string", multiple: true, default: [] },
        dir: { type: "string", multiple: true, default: [] },
        "dry-run": { type: "boolean", default: false },
        yes: { type: "boolean", default: false },
        json: { type: "boolean", default: false },
        version: { type: "boolean", default: false },
        help: { type: "boolean", default: false },
      },
    });
  } catch (error) {
    throw new UsageError(error.message);
  }
}

const isExplicit = (options) => options.client.length > 0 || options.dir.length > 0;
const hostContext = () => ({ home: homedir(), env: process.env, platform: process.platform });

/**
 * The --client/--dir choices, or every client accepted by `byDefault` when none are given: one target per
 * folder. Agents that read the same folder share one target, which names them all; the shared
 * ~/.agents/skills is client "shared", as in rea-agents.
 */
function selectTargets(options, context, byDefault) {
  const unknown = options.client.filter((id) => !CLIENTS.some((c) => c.id === id));
  if (unknown.length > 0) {
    throw new UsageError(`unknown client: ${unknown.join(", ")} (choose from ${CLIENTS.map((c) => c.id).join(", ")})`);
  }
  const shared = join(sharedSkillsDir(context), SKILL_NAME);
  const targets = new Map();
  for (const c of CLIENTS.filter((c) => (isExplicit(options) ? options.client.includes(c.id) : byDefault(c)))) {
    const path = join(skillsDirOf(c, context), SKILL_NAME);
    const target = targets.get(path) ?? { client: path === shared ? "shared" : c.id, clients: [], labels: [], path };
    target.clients.push(c.id);
    target.labels.push(c.label);
    targets.set(path, target);
  }
  for (const dir of options.dir) {
    const path = join(resolve(dir), SKILL_NAME);
    if (!targets.has(path)) targets.set(path, { client: "custom", clients: [], labels: ["Custom folder"], path });
  }
  return [...targets.values()].map(({ labels, ...target }) => ({ ...target, label: labels.join(", ") }));
}

function printPlan(title, targets, footer) {
  console.log(`scifig-agents ${VERSION}: ${title}`);
  for (const t of targets) {
    const extra = t.reason ?? (t.installed_version ? `(installed: ${t.installed_version})` : "");
    const shared = t.clients.length > 1; // a folder several agents read: name them on a line of their own
    console.log(`  ${t.action.padEnd(10)} ${(shared ? "Shared folder" : t.label).padEnd(14)} ${t.path}  ${extra}`.trimEnd());
    if (shared) console.log(`  ${"".padEnd(10)} read by ${t.label}`);
  }
  if (footer) console.log(footer);
}

async function confirm(question) {
  const prompt = createInterface({ input: process.stdin, output: process.stdout });
  const answer = await prompt.question(`${question} [y/N] `);
  prompt.close();
  return /^y(es)?$/i.test(answer.trim());
}

/**
 * Show a plan, get consent, apply it. Returns the exit code.
 * `fatal` actions stop everything; `idle` actions need no work.
 */
async function execute(command, options, targets, { apply, idle, fatal, done }) {
  const dryRun = options["dry-run"];
  const report = (applied, footer) => {
    if (options.json) console.log(JSON.stringify({ command, version: VERSION, dry_run: dryRun, applied, targets }, null, 2));
    else printPlan(dryRun ? `${command} (dry run)` : command, targets, footer);
  };

  if (targets.some((target) => fatal.includes(target.action))) {
    report(false, "Nothing was changed: move the blocked folder away, or pick the other agents with --client.");
    return 1;
  }
  if (dryRun) {
    report(false, "Dry run: nothing was changed.");
    return 0;
  }
  const pending = targets.filter((target) => !idle.includes(target.action));
  if (pending.length > 0 && !options.yes) {
    if (!process.stdin.isTTY) {
      report(false, "Nothing was changed.");
      console.error("Re-run with --yes to apply this plan, or with --dry-run to preview it.");
      return 1;
    }
    printPlan(command, targets);
    if (!(await confirm("Apply this plan?"))) {
      console.log("Nothing was changed.");
      return 1;
    }
  }
  for (const target of pending) apply(target.path);
  report(true, pending.length > 0 ? done : "Nothing to do.");
  return 0;
}

function setup(options) {
  const context = hostContext();
  const targets = selectTargets(options, context, (c) => isPresent(c, context));
  if (targets.length === 0) {
    console.error("No supported agent found. Choose one with --client, or pass a skills folder with --dir.");
    return 1;
  }
  const source = { dir: SOURCE_DIR, version: VERSION, digest: digestTree(SOURCE_DIR) };
  return execute("setup", options, targets.map((t) => ({ ...t, ...planInstall(t.path, source) })), {
    apply: (path) => applyInstall(path, source),
    idle: ["unchanged"],
    fatal: ["blocked"],
    done: "Done. Start a new agent session so it picks up the skill.",
  });
}

function uninstall(options) {
  // With no explicit choice, look everywhere and report only folders that exist.
  const targets = selectTargets(options, hostContext(), () => true)
    .map((t) => ({ ...t, ...planUninstall(t.path) }))
    .filter((t) => isExplicit(options) || t.action !== "absent");
  return execute("uninstall", options, targets, {
    apply: applyUninstall,
    idle: ["absent", "blocked"],
    fatal: [],
    done: "Removed.",
  });
}

function toolVersion(command) {
  const result = spawnSync(command, ["--version"], { encoding: "utf8" });
  return result.status === 0 ? result.stdout.trim().split("\n")[0] : null;
}

function doctor(options) {
  const context = hostContext();
  const digest = digestTree(SOURCE_DIR);
  const clients = CLIENTS.map((c) => {
    const path = join(skillsDirOf(c, context), SKILL_NAME);
    const manifest = readManifest(path);
    return {
      client: c.id,
      label: c.label,
      detected: isPresent(c, context),
      path,
      state: manifest ? "installed" : existsSync(path) ? "unmanaged" : "not_installed",
      installed_version: manifest?.version ?? null,
      up_to_date: manifest ? manifest.version === VERSION && manifest.digest === digest : null,
      native_image_tool: c.imageTool ?? null,
    };
  });
  const tools = { uv: toolVersion("uv"), python3: toolVersion("python3") };
  if (options.json) {
    console.log(JSON.stringify({ command: "doctor", version: VERSION, clients, tools }, null, 2));
    return 0;
  }
  console.log(`scifig-agents ${VERSION}: doctor`);
  // The agents found here, or with an install of their own; the rest by name only.
  const shown = clients.filter((c) => c.detected || c.state !== "not_installed");
  const width = Math.max(12, ...shown.map((c) => c.label.length));
  for (const c of shown) {
    const install =
      c.state === "installed" ? `installed ${c.installed_version}${c.up_to_date ? "" : " (outdated: run setup)"}` : c.state.replace("_", " ");
    const images = c.native_image_tool ? `image tool: ${c.native_image_tool}` : "no built-in image tool (diagrams, charts, export and checks still work)";
    console.log(`  ${c.label.padEnd(width)} ${(c.detected ? "found" : "not found").padEnd(10)} ${install.padEnd(30)} ${images}`);
  }
  const absent = clients.filter((c) => !shown.includes(c)).map((c) => c.label);
  if (absent.length > 0) console.log(`  Not found: ${absent.join(", ")}`);
  console.log(`  ${"uv".padEnd(width)} ${tools.uv ?? "missing: the Python scripts need it, see https://docs.astral.sh/uv/"}`);
  console.log(`  ${"python3".padEnd(width)} ${tools.python3 ?? "missing"}`);
  return 0;
}

async function main() {
  const { values: options, positionals } = parse(process.argv.slice(2));
  if (options.version) {
    console.log(VERSION);
    return 0;
  }
  const [command, ...rest] = positionals;
  if (options.help || command === undefined) {
    console.log(USAGE);
    return 0;
  }
  if (rest.length > 0) throw new UsageError(`unexpected argument: ${rest[0]}`);
  const commands = { setup, uninstall, doctor };
  if (!Object.hasOwn(commands, command)) throw new UsageError(`unknown command: ${command}`);
  return commands[command](options);
}

try {
  process.exitCode = await main();
} catch (error) {
  if (error instanceof UsageError) {
    console.error(`${error.message}\nRun scifig-agents --help for usage.`);
    process.exitCode = 2;
  } else if (error.syscall) {
    // A filesystem failure (permissions, a file where a folder should be): the message names the path.
    console.error(`scifig-agents: ${error.message}`);
    process.exitCode = 1;
  } else {
    throw error;
  }
}
