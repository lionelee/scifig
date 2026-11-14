import { dirname, sep } from "node:path";
import { cancel, confirm, intro, isCancel, multiselect, outro } from "@clack/prompts";

/*
 * The terminal side of setup and uninstall, modelled on rea-agents' setup (dist/cli/interactiveSetup.js in
 * rea-agents 6.9.0). A row is a target of bin/scifig.mjs with its plan and `found`, the agents found here
 * that read it; `apply` does the work. Everything goes to stderr, as in rea-agents.
 */

const BLOCKED = "holds a scifig folder this tool did not install";
const STANDARD_IO = { input: process.stdin, output: process.stderr };

/** As rea-agents decides: only at a terminal, and only when no flag asks for a plan, JSON or no questions. */
export function isInteractive(options, streams = process) {
  return (
    !options.yes &&
    !options["dry-run"] &&
    !options.json &&
    streams.stdin.isTTY === true &&
    streams.stdout.isTTY === true &&
    streams.stderr.isTTY === true
  );
}

/** The folders ticked when the list opens: those an agent found here reads, and those holding an install of ours. */
export function initialSelection(rows) {
  return rows
    .filter((row) => row.action !== "blocked" && (row.found.length > 0 || row.action === "update" || row.action === "unchanged"))
    .map((row) => row.path);
}

const nameOf = (row) => (row.clients.length > 1 ? "Shared folder" : row.label);
const tilde = (path, home) => (path === home || path.startsWith(home + sep) ? `~${path.slice(home.length)}` : path);

function humanList(values) {
  if (values.length < 2) return values[0] ?? "";
  if (values.length === 2) return `${values[0]} and ${values[1]}`;
  return `${values.slice(0, -1).join(", ")}, and ${values.at(-1)}`;
}

function hintOf(row) {
  if (row.action === "blocked") return BLOCKED;
  const more = row.found.length > 3 ? ` and ${row.found.length - 3} more` : "";
  const found =
    row.found.length === 0 ? "not found" : row.clients.length > 1 ? `found: ${row.found.slice(0, 3).join(", ")}${more}` : "found";
  const installed =
    row.action === "update" ? `installed ${row.installed_version}, will update` : row.action === "unchanged" ? "up to date" : "";
  return [found, installed].filter(Boolean).join(" · ");
}

function session(io) {
  return {
    opts: { input: io.input, output: io.output, withGuide: true },
    line: (text) => io.output.write(`${text}\n`),
  };
}

function stop({ opts }, message) {
  cancel(message, opts);
  return 1;
}

/** The checkbox list. Resolves to the paths ticked, or undefined when cancelled. */
async function pick(rows, { opts }, home) {
  const width = Math.max(...rows.map((row) => nameOf(row).length));
  const picked = await multiselect({
    ...opts,
    message: "Which skills folders should get scifig?",
    options: rows.map((row) => ({
      value: row.path,
      label: `${nameOf(row).padEnd(width)}  ${tilde(dirname(row.path), home)}`,
      hint: hintOf(row),
      disabled: row.action === "blocked",
    })),
    initialValues: initialSelection(rows),
    required: false,
    showInstructions: false,
    maxItems: Math.max(5, Math.min(rows.length, (opts.output.rows ?? 24) - 8)),
  });
  return isCancel(picked) ? undefined : picked;
}

/** --accessible: one yes-or-no question per folder instead of the list. */
async function askEach(rows, { opts, line }, home) {
  const ticked = new Set(initialSelection(rows));
  const picked = [];
  for (const row of rows) {
    if (row.action === "blocked") {
      line(`│  Skipping ${nameOf(row)}: ${BLOCKED}`);
      continue;
    }
    const answer = await confirm({
      ...opts,
      message: `Install into ${nameOf(row)} (${tilde(dirname(row.path), home)})? ${hintOf(row)}`,
      initialValue: ticked.has(row.path),
      vertical: true,
    });
    if (isCancel(answer)) return undefined;
    if (answer) picked.push(row.path);
  }
  return picked;
}

function review(rows, { line }, home, version) {
  const pad = "".padEnd(10);
  line("│");
  line("◆  Ready to review");
  for (const row of rows) {
    const versions =
      row.action === "update" ? ` · ${row.installed_version} → ${version}` : row.action === "unchanged" ? ` · ${row.installed_version}` : "";
    line("│");
    line(`│  ${row.action.toUpperCase().padEnd(10)} ${nameOf(row)}${versions}`);
    line(`│  ${pad} ${tilde(row.path, home)}`);
    if (row.action === "blocked") line(`│  ${pad} ${row.reason}`);
    else if (row.clients.length > 1 && row.found.length > 0) line(`│  ${pad} read by ${humanList(row.found)}`);
  }
  line("│");
}

/** Applies each row in turn, one line apiece, and stops at the first filesystem error. False if one failed. */
function applyAll(rows, apply, verb, { line }, home) {
  for (const row of rows) {
    try {
      apply(row.path);
    } catch (error) {
      if (!error.syscall) throw error;
      line(`✗  ${nameOf(row)}: ${error.message}`);
      return false;
    }
    line(`◆  ${verb(row)}  ${nameOf(row)}  ${tilde(row.path, home)}`);
  }
  return true;
}

/**
 * Interactive setup: say what was found, let the user pick folders (unless `choose` is false because --client
 * or --dir named them), show the changes, confirm, apply. Resolves to the exit code.
 */
export async function setupFlow({ version, rows, detected, choose, accessible = false, apply, home, io = STANDARD_IO }) {
  const ui = session(io);
  intro("scifig-agents setup", ui.opts);
  ui.line(`│  Install the scifig skill, version ${version}, into your coding agents.`);
  ui.line("│");
  ui.line(detected.length === 0 ? "◆  No agents found. Choose any folder below." : `◆  Found: ${humanList(detected)}`);
  ui.line("│");
  ui.line(accessible ? "│  Keys: Enter answer · Ctrl-C cancel" : "│  Keys: ↑/↓ move · Space toggle · Enter confirm · Ctrl-C cancel");

  let chosen = rows;
  if (choose) {
    const paths = await (accessible ? askEach(rows, ui, home) : pick(rows, ui, home));
    if (paths === undefined) return stop(ui, "Setup cancelled. No changes were made.");
    chosen = rows.filter((row) => paths.includes(row.path));
    if (chosen.length === 0) return stop(ui, "Nothing selected. No changes were made.");
  }

  review(chosen, ui, home, version);
  if (chosen.some((row) => row.action === "blocked")) {
    return stop(ui, "Nothing was changed: move the blocked folder away, or pick the other agents with --client.");
  }
  const pending = chosen.filter((row) => row.action === "install" || row.action === "update");
  if (pending.length === 0) {
    outro("Already up to date. Nothing to do.", ui.opts);
    return 0;
  }
  const approved = await confirm({
    ...ui.opts,
    message: pending.length === 1 ? "Apply this change?" : `Apply these ${pending.length} changes?`,
    active: "Yes, apply",
    inactive: "No, cancel",
    initialValue: true,
    vertical: accessible,
  });
  if (isCancel(approved) || !approved) return stop(ui, "Setup cancelled. No changes were made.");

  if (!applyAll(pending, apply, (row) => (row.action === "install" ? "Installed" : "Updated"), ui, home)) return 1;
  const agents = [...new Set(pending.flatMap((row) => row.found))];
  outro(
    agents.length === 0
      ? "Done. Start a new agent session so it picks up the skill."
      : `Done. Start a new session in ${humanList(agents)} so they pick up the skill.`,
    ui.opts,
  );
  return 0;
}

/** Interactive uninstall: the same review and confirmation as setup, without a list to choose from. */
export async function uninstallFlow({ targets, accessible = false, apply, home, io = STANDARD_IO }) {
  const ui = session(io);
  intro("scifig-agents uninstall", ui.opts);
  const removable = targets.filter((target) => target.action === "remove");
  if (removable.length === 0) {
    outro("Nothing to remove.", ui.opts);
    return 0;
  }
  ui.line("│");
  ui.line("◆  Ready to review");
  for (const target of targets.filter((target) => target.action !== "absent")) {
    ui.line("│");
    ui.line(target.action === "remove" ? `│  REMOVE  ${nameOf(target)} · ${target.installed_version}` : `│  SKIP    ${nameOf(target)}`);
    ui.line(`│          ${tilde(target.path, home)}`);
    if (target.action === "blocked") ui.line("│          not installed by scifig-agents; left alone");
  }
  ui.line("│");
  const approved = await confirm({
    ...ui.opts,
    message: removable.length === 1 ? "Remove this copy?" : `Remove these ${removable.length} copies?`,
    active: "Yes, remove",
    inactive: "No, cancel",
    initialValue: true,
    vertical: accessible,
  });
  if (isCancel(approved) || !approved) return stop(ui, "Uninstall cancelled. Nothing was removed.");
  if (!applyAll(removable, apply, () => "Removed", ui, home)) return 1;
  outro("Removed.", ui.opts);
  return 0;
}
