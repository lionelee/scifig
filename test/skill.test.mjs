import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SKILL = join(dirname(fileURLToPath(import.meta.url)), "..", "skills", "scifig");
const read = (...parts) => readFileSync(join(SKILL, ...parts), "utf8");
const docs = () => ["SKILL.md", ...readdirSync(join(SKILL, "references")).filter((f) => f.endsWith(".md")).map((f) => join("references", f))];
const scripts = () => readdirSync(join(SKILL, "scripts")).filter((f) => f.endsWith(".py"));

function frontmatter() {
  const match = read("SKILL.md").match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  assert.ok(match, "SKILL.md must start with YAML frontmatter");
  const fields = Object.fromEntries(match[1].split("\n").map((line) => [line.slice(0, line.indexOf(":")), line.slice(line.indexOf(":") + 1).trim()]));
  return { raw: match[1], fields, body: match[2] };
}

test("SKILL.md frontmatter names the skill and says when to use it", () => {
  const { raw, fields } = frontmatter();
  assert.deepEqual(Object.keys(fields), ["name", "description"]);
  assert.equal(fields.name, "scifig");
  assert.match(fields.description, /^Use when /);
  assert.ok(raw.length <= 1024, `frontmatter is ${raw.length} characters, limit 1024`);
});

test("SKILL.md stays a short router", () => {
  const words = frontmatter().body.split(/\s+/).filter(Boolean).length;
  assert.ok(words <= 500, `SKILL.md body is ${words} words, limit 500`);
});

test("every file a document points to exists", () => {
  for (const doc of docs()) {
    for (const [ref] of read(doc).matchAll(/\b(?:references|scripts)\/[\w.-]+\.(?:md|json|py)\b/g)) {
      assert.ok(existsSync(join(SKILL, ref)), `${doc} points to missing ${ref}`);
    }
  }
});

test("every reference and script is reachable from the documents", () => {
  const all = docs().map((doc) => read(doc)).join("\n");
  for (const doc of docs().slice(1)) assert.ok(all.includes(doc), `${doc} is never mentioned`);
  for (const script of scripts()) assert.ok(all.includes(`scripts/${script}`), `scripts/${script} is never mentioned`);
});

test("every command-line flag shown in the documents exists in its script", () => {
  for (const doc of docs()) {
    for (const line of read(doc).split("\n")) {
      const script = line.match(/scripts\/([\w-]+\.py)/)?.[1];
      if (!script) continue;
      const source = read("scripts", script);
      for (const [flag] of line.matchAll(/(?<![\w-])--[a-z][a-z-]*/g)) {
        if (flag === "--help") continue; // argparse adds it to every script
        const declared = source.includes(`"${flag}"`) || source.includes(`'${flag}'`);
        assert.ok(declared, `${doc}: ${script} has no ${flag} (line: ${line.trim()})`);
      }
    }
  }
});
