import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { applyInstall, digestTree } from "../lib/install.mjs";

const CLI = join(dirname(fileURLToPath(import.meta.url)), "..", "bin", "scifig.mjs");

function makeSource(root) {
  const dir = join(root, "source");
  mkdirSync(join(dir, "scripts"), { recursive: true });
  writeFileSync(join(dir, "SKILL.md"), "new skill");
  writeFileSync(join(dir, "scripts", "tool.py"), "print('hi')");
  return { dir, version: "9.9.9", digest: digestTree(dir) };
}

test("a failed copy leaves the previous install intact and no half-copied skill behind", () => {
  const root = mkdtempSync(join(tmpdir(), "scifig-install-"));
  const source = makeSource(root);
  const skills = join(root, "skills");
  const target = join(skills, "scifig");
  mkdirSync(target, { recursive: true });
  writeFileSync(join(target, "SKILL.md"), "old skill");

  chmodSync(join(source.dir, "scripts", "tool.py"), 0o000); // unreadable: the copy fails part-way
  try {
    assert.throws(() => applyInstall(target, source));
  } finally {
    chmodSync(join(source.dir, "scripts", "tool.py"), 0o644);
  }
  assert.equal(readFileSync(join(target, "SKILL.md"), "utf8"), "old skill");
  assert.deepEqual(readdirSync(skills), ["scifig"]);
});

test("the half-made copy of a setup that was killed is cleared by the next one", () => {
  const root = mkdtempSync(join(tmpdir(), "scifig-stale-"));
  const source = makeSource(root);
  const skills = join(root, "skills");
  const stale = join(skills, ".scifig.staging-12345"); // an agent could load its SKILL.md as a second skill
  mkdirSync(stale, { recursive: true });
  writeFileSync(join(stale, "SKILL.md"), "half a skill");

  applyInstall(join(skills, "scifig"), source);

  assert.deepEqual(readdirSync(skills), ["scifig"]);
});

test("the digest ignores Python caches and changes with any file content", () => {
  const root = mkdtempSync(join(tmpdir(), "scifig-digest-"));
  const { dir, digest } = makeSource(root);
  mkdirSync(join(dir, "scripts", "__pycache__"));
  writeFileSync(join(dir, "scripts", "__pycache__", "tool.cpython-312.pyc"), "cache");
  assert.equal(digestTree(dir), digest);
  writeFileSync(join(dir, "scripts", "tool.py"), "print('changed')");
  assert.notEqual(digestTree(dir), digest);
});

test("a filesystem error is reported in one line, without a stack trace", () => {
  const root = mkdtempSync(join(tmpdir(), "scifig-error-"));
  const file = join(root, "not-a-folder");
  writeFileSync(file, "");
  const result = spawnSync(process.execPath, [CLI, "setup", "--dir", join(file, "skills"), "--yes"], {
    encoding: "utf8",
    env: { PATH: process.env.PATH, HOME: root, USERPROFILE: root },
  });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /^scifig-agents: .+\n$/);
});
