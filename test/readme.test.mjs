import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const images = (file) => [...readFileSync(join(ROOT, file), "utf8").matchAll(/<img src="([^"]+)"/g)].map((match) => match[1]);

test("both READMEs show the four example figures, from files in the repository", () => {
  const english = images("README.md");
  assert.equal(english.length, 4);
  for (const src of english) assert.ok(existsSync(join(ROOT, src)), `README.md shows a missing ${src}`);
  assert.deepEqual(images("README.zh-CN.md"), english);
});
