import { test } from "node:test";
import assert from "node:assert/strict";
import { PassThrough, Writable } from "node:stream";
import { stripVTControlCharacters } from "node:util";
import { initialSelection, isInteractive, setupFlow, uninstallFlow } from "../lib/tui.mjs";

const HOME = "/home/u";
const KEY = { enter: "\r", space: " ", down: "\x1b[B", right: "\x1b[C", ctrlC: "\x03" };
const LIST = "Which skills folders should get scifig?";

/** A terminal for clack: keeps what is written as text; `rows` and `columns` size the list. */
class Screen extends Writable {
  text = "";
  columns = 120;
  rows = 40;
  _write(chunk, _encoding, done) {
    this.text += chunk.toString();
    this.emit("text");
    done();
  }
}

const plain = (screen) => stripVTControlCharacters(screen.text);

/** Types each step's keys once the step's text has appeared on the screen, one step after another. */
function typist(screen, input, steps) {
  let from = 0;
  let next = 0;
  screen.on("text", () => {
    while (next < steps.length) {
      const [text, keys] = steps[next];
      const at = plain(screen).indexOf(text, from);
      if (at === -1) return;
      from = at + text.length;
      next += 1;
      setImmediate(() => input.write(keys));
    }
  });
}

/** A folder row as bin/scifig.mjs builds it: a target, its plan, and the agents found that read it. */
const row = ({ label, clients = [label], path, action = "install", found = [], installed_version = null, reason }) => ({
  client: clients.length > 1 ? "shared" : "x",
  clients,
  label,
  path,
  action,
  installed_version,
  found,
  ...(reason ? { reason } : {}),
});

const CLAUDE = row({ label: "Claude Code", path: `${HOME}/.claude/skills/scifig`, found: ["Claude Code"] });
const SHARED = row({ label: "Codex, Cursor", clients: ["codex", "cursor"], path: `${HOME}/.agents/skills/scifig`, found: ["Codex", "Cursor"] });
const TRAE = row({ label: "Trae", path: `${HOME}/.trae/skills/scifig` });
const FOREIGN = row({
  label: "Hermes",
  path: `${HOME}/.hermes/skills/scifig`,
  action: "blocked",
  found: ["Hermes"],
  reason: "exists but was not installed by scifig-agents; move or remove it first",
});

async function runSetup({ rows, steps, detected = ["Claude Code", "Codex", "Cursor"], choose = true, accessible = false, apply }) {
  const input = new PassThrough();
  const screen = new Screen();
  typist(screen, input, steps);
  const applied = [];
  const code = await setupFlow({
    version: "0.2.0",
    rows,
    detected,
    choose,
    accessible,
    apply: apply ?? ((path) => applied.push(path)),
    home: HOME,
    io: { input, output: screen },
  });
  return { code, applied, text: plain(screen) };
}

test("setup asks only at a terminal, and only without --yes, --dry-run or --json", () => {
  const tty = { stdin: { isTTY: true }, stdout: { isTTY: true }, stderr: { isTTY: true } };
  const none = { yes: false, "dry-run": false, json: false };
  assert.equal(isInteractive(none, tty), true);
  for (const flag of ["yes", "dry-run", "json"]) assert.equal(isInteractive({ ...none, [flag]: true }, tty), false, flag);
  for (const stream of ["stdin", "stdout", "stderr"]) {
    assert.equal(isInteractive(none, { ...tty, [stream]: { isTTY: false } }), false, stream);
  }
});

test("the list opens with the folders of the agents found, and those holding an install of ours, ticked", () => {
  const older = row({ label: "Qoder", path: `${HOME}/.qoder/skills/scifig`, action: "update", installed_version: "0.1.0" });
  const current = row({ label: "ZCode", path: `${HOME}/.zcode/skills/scifig`, action: "unchanged", installed_version: "0.2.0" });
  assert.deepEqual(initialSelection([CLAUDE, TRAE, older, current, FOREIGN]), [CLAUDE.path, older.path, current.path]);
});

test("Enter twice installs into the folders ticked at the start, after showing what will change", async () => {
  const { code, applied, text } = await runSetup({
    rows: [CLAUDE, SHARED, TRAE],
    steps: [[LIST, KEY.enter], ["Apply these 2 changes?", KEY.enter]],
  });
  assert.equal(code, 0);
  assert.deepEqual(applied, [CLAUDE.path, SHARED.path]);
  assert.match(text, /Install the scifig skill, version 0\.2\.0, into your coding agents\./);
  assert.match(text, /Found: Claude Code, Codex, and Cursor/);
  assert.match(text, /Keys: ↑\/↓ move · Space toggle · Enter confirm · Ctrl-C cancel/);
  assert.match(text, /Ready to review/);
  assert.match(text, /INSTALL\s+Shared folder/);
  assert.match(text, /read by Codex and Cursor/);
  assert.match(text, /Installed {2}Claude Code {2}~\/\.claude\/skills\/scifig/);
  assert.match(text, /Done\. Start a new session in Claude Code, Codex, and Cursor so they pick up the skill\./);
});

test("Space unticks a folder, which is then left alone", async () => {
  const { code, applied } = await runSetup({
    rows: [CLAUDE, SHARED, TRAE],
    steps: [[LIST, KEY.down + KEY.space + KEY.enter], ["Apply this change?", KEY.enter]],
  });
  assert.equal(code, 0);
  assert.deepEqual(applied, [CLAUDE.path]);
});

test("Ctrl-C at the list changes nothing", async () => {
  const { code, applied, text } = await runSetup({ rows: [CLAUDE], steps: [[LIST, KEY.ctrlC]] });
  assert.equal(code, 1);
  assert.deepEqual(applied, []);
  assert.match(text, /Setup cancelled\. No changes were made\./);
});

test("answering No at the confirmation changes nothing", async () => {
  const { code, applied, text } = await runSetup({
    rows: [CLAUDE],
    steps: [[LIST, KEY.enter], ["Apply this change?", KEY.right + KEY.enter]],
  });
  assert.equal(code, 1);
  assert.deepEqual(applied, []);
  assert.match(text, /Setup cancelled\. No changes were made\./);
});

test("unticking every folder changes nothing", async () => {
  const { code, applied, text } = await runSetup({ rows: [CLAUDE], steps: [[LIST, KEY.space + KEY.enter]] });
  assert.equal(code, 1);
  assert.deepEqual(applied, []);
  assert.match(text, /Nothing selected\. No changes were made\./);
});

test("a folder holding someone else's scifig is shown, skipped by the cursor and never ticked", async () => {
  // Down from Claude Code passes over the blocked folder to Trae, and Space ticks Trae.
  const { code, applied, text } = await runSetup({
    rows: [CLAUDE, FOREIGN, TRAE],
    steps: [[LIST, KEY.down + KEY.space + KEY.enter], ["Apply these 2 changes?", KEY.enter]],
  });
  assert.equal(code, 0);
  assert.deepEqual(applied, [CLAUDE.path, TRAE.path]);
  assert.match(text, /Hermes\s+~\/\.hermes\/skills \(holds a scifig folder this tool did not install\)/);
});

test("an older install of ours is ticked, and shown with both versions", async () => {
  const older = row({ label: "Claude Code", path: CLAUDE.path, found: ["Claude Code"], action: "update", installed_version: "0.1.0" });
  const { code, applied, text } = await runSetup({ rows: [older], steps: [[LIST, KEY.enter], ["Apply this change?", KEY.enter]] });
  assert.equal(code, 0);
  assert.deepEqual(applied, [older.path]);
  assert.match(text, /found · installed 0\.1\.0, will update/);
  assert.match(text, /UPDATE\s+Claude Code · 0\.1\.0 → 0\.2\.0/);
  assert.match(text, /Updated {2}Claude Code {2}~\/\.claude\/skills\/scifig/);
});

test("when every folder ticked is up to date it says so and asks nothing more", async () => {
  const current = row({ label: "Claude Code", path: CLAUDE.path, found: ["Claude Code"], action: "unchanged", installed_version: "0.2.0" });
  const { code, applied, text } = await runSetup({ rows: [current], steps: [[LIST, KEY.enter]] });
  assert.equal(code, 0);
  assert.deepEqual(applied, []);
  assert.match(text, /UNCHANGED\s+Claude Code · 0\.2\.0/);
  assert.match(text, /Already up to date\. Nothing to do\./);
  assert.doesNotMatch(text, /Apply th/);
});

test("with no agent found it still offers every folder, with none ticked", async () => {
  const { code, applied, text } = await runSetup({ rows: [TRAE], detected: [], steps: [[LIST, KEY.enter]] });
  assert.equal(code, 1);
  assert.deepEqual(applied, []);
  assert.match(text, /No agents found\. Choose any folder below\./);
  assert.match(text, /Nothing selected\. No changes were made\./);
});

test("with --client or --dir it skips the list and goes straight to the review", async () => {
  const { code, applied, text } = await runSetup({ rows: [TRAE], choose: false, steps: [["Apply this change?", KEY.enter]] });
  assert.equal(code, 0);
  assert.deepEqual(applied, [TRAE.path]);
  assert.doesNotMatch(text, new RegExp(LIST));
  assert.match(text, /Done\. Start a new agent session so it picks up the skill\./);
});

test("a blocked folder named with --client stops setup before anything is written", async () => {
  const { code, applied, text } = await runSetup({ rows: [TRAE, FOREIGN], choose: false, steps: [] });
  assert.equal(code, 1);
  assert.deepEqual(applied, []);
  assert.match(text, /BLOCKED\s+Hermes/);
  assert.match(text, /exists but was not installed by scifig-agents/);
  assert.match(text, /Nothing was changed: move the blocked folder away, or pick the other agents with --client\./);
});

test("--accessible asks about one folder at a time instead of showing the list", async () => {
  const { code, applied, text } = await runSetup({
    rows: [CLAUDE, FOREIGN, TRAE],
    accessible: true,
    steps: [
      ["Install into Claude Code (~/.claude/skills)? found", KEY.enter], // keeps the ticked default, Yes
      ["Install into Trae (~/.trae/skills)? not found", KEY.down + KEY.enter], // turns the default No into Yes
      ["Apply these 2 changes?", KEY.enter],
    ],
  });
  assert.equal(code, 0);
  assert.deepEqual(applied, [CLAUDE.path, TRAE.path]);
  assert.match(text, /Keys: Enter answer · Ctrl-C cancel/);
  assert.match(text, /Skipping Hermes: holds a scifig folder this tool did not install/);
  assert.doesNotMatch(text, new RegExp(LIST));
});

test("a filesystem error stops setup with one line that names the folder", async () => {
  const deny = () => {
    throw Object.assign(new Error("EACCES: permission denied, mkdir '/home/u/.claude/skills'"), { syscall: "mkdir" });
  };
  const { code, text } = await runSetup({ rows: [CLAUDE], apply: deny, steps: [[LIST, KEY.enter], ["Apply this change?", KEY.enter]] });
  assert.equal(code, 1);
  assert.match(text, /✗ {2}Claude Code: EACCES: permission denied/);
  assert.doesNotMatch(text, /Done\./);
});

async function runUninstall({ targets, steps }) {
  const input = new PassThrough();
  const screen = new Screen();
  typist(screen, input, steps);
  const removed = [];
  const code = await uninstallFlow({ targets, apply: (path) => removed.push(path), home: HOME, io: { input, output: screen } });
  return { code, removed, text: plain(screen) };
}

test("uninstall shows what it will remove and what it leaves, then removes after Enter", async () => {
  const ours = { ...SHARED, action: "remove", installed_version: "0.1.0" };
  const { code, removed, text } = await runUninstall({ targets: [ours, FOREIGN], steps: [["Remove this copy?", KEY.enter]] });
  assert.equal(code, 0);
  assert.deepEqual(removed, [ours.path]);
  assert.match(text, /REMOVE {2}Shared folder · 0\.1\.0/);
  assert.match(text, /SKIP {4}Hermes/);
  assert.match(text, /not installed by scifig-agents; left alone/);
  assert.match(text, /Removed {2}Shared folder {2}~\/\.agents\/skills\/scifig/);
  assert.match(text, /Removed\./);
});

test("uninstall answered No removes nothing", async () => {
  const ours = { ...CLAUDE, action: "remove", installed_version: "0.2.0" };
  const { code, removed, text } = await runUninstall({ targets: [ours], steps: [["Remove this copy?", KEY.right + KEY.enter]] });
  assert.equal(code, 1);
  assert.deepEqual(removed, []);
  assert.match(text, /Uninstall cancelled\. Nothing was removed\./);
});

test("uninstall with nothing of ours to remove says so and asks nothing", async () => {
  const { code, removed, text } = await runUninstall({ targets: [FOREIGN], steps: [] });
  assert.equal(code, 0);
  assert.deepEqual(removed, []);
  assert.match(text, /Nothing to remove\./);
  assert.doesNotMatch(text, /Remove th/);
});
