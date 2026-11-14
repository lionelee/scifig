import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DOCS = join(dirname(fileURLToPath(import.meta.url)), "..", "docs");
const page = () => readFileSync(join(DOCS, "index.html"), "utf8");

test("every command on the Pages site has a copy button that copies exactly that command", () => {
  const html = page();
  const commands = [...html.matchAll(/<code>(npx [^<]+)<\/code>/g)].map((match) => match[1]);
  const copied = [...html.matchAll(/data-copy="([^"]+)"/g)].map((match) => match[1]);
  assert.ok(commands.length >= 5, `found ${commands.length} commands`);
  assert.deepEqual(copied, commands);
});

test("the Pages gallery opens figures at full size in the page, from files in docs/", () => {
  const html = page();
  assert.match(html, /<dialog class="viewer"/);
  const shots = [...html.matchAll(/<a class="shot" href="([^"]+)"/g)].map((match) => match[1]);
  assert.equal(shots.length, 4);
  for (const href of shots) assert.ok(existsSync(join(DOCS, href)), `missing ${href}`);
});

test("the Pages site loads nothing from another site, and every file it shows is in docs/", () => {
  const html = page();
  assert.doesNotMatch(html, /<script[^>]+\ssrc=|<link[^>]+rel="stylesheet"|@import|url\(\s*["']?https?:/i);
  for (const [, src] of html.matchAll(/\ssrc="([^"]+)"/g)) {
    assert.ok(!/^[a-z]+:/i.test(src) && existsSync(join(DOCS, src)), `src ${src}`);
  }
});
