import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

test("the npm package ships the installer and the skill, and no junk, tests or evaluation tools", () => {
  const result = spawnSync("npm", ["pack", "--dry-run", "--json"], { cwd: ROOT, encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  const files = JSON.parse(result.stdout)[0].files.map((file) => file.path);
  const required = [
    "README.md",
    "LICENSE",
    "NOTICE.md",
    "bin/scifig.mjs",
    "lib/clients.mjs",
    "lib/install.mjs",
    "skills/scifig/SKILL.md",
    "skills/scifig/references/journal-figure-requirements.json",
    "skills/scifig/scripts/journals.py",
    "skills/scifig/scripts/scistyle.py",
    "skills/scifig/scripts/export_figure.py",
    "skills/scifig/scripts/check_figure.py",
    "skills/scifig/scripts/editable.py",
    "skills/scifig/scripts/panels.py",
    "skills/scifig/scripts/check_text.py",
    "skills/scifig/scripts/enlarge.py",
  ];
  for (const path of required) assert.ok(files.includes(path), `missing ${path}`);
  assert.deepEqual(files.filter((path) => /__pycache__|\.pyc$|^test\/|^eval\//.test(path)), []);
});
