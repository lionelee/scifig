import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";

export const SKILL_NAME = "scifig";
export const MANIFEST = ".scifig-install.json";
const PACKAGE = "scifig-agents";
const NOT_OURS = "exists but was not installed by scifig-agents; move or remove it first";

const isJunk = (name) => name === "__pycache__" || name === ".DS_Store" || name.endsWith(".pyc");

function listFiles(dir, prefix = "") {
  return readdirSync(join(dir, prefix), { withFileTypes: true })
    .filter((entry) => !isJunk(entry.name))
    .sort((a, b) => (a.name < b.name ? -1 : 1))
    .flatMap((entry) => {
      const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
      return entry.isDirectory() ? listFiles(dir, rel) : [rel];
    });
}

/** Content hash of a skill folder, so a changed package is detected even at the same version. */
export function digestTree(dir) {
  const hash = createHash("sha256");
  for (const rel of listFiles(dir)) hash.update(rel).update("\0").update(readFileSync(join(dir, rel))).update("\0");
  return hash.digest("hex");
}

/** The manifest of an install made by this package, or null for anything else. */
export function readManifest(target) {
  try {
    const manifest = JSON.parse(readFileSync(join(target, MANIFEST), "utf8"));
    return manifest.package === PACKAGE ? manifest : null;
  } catch {
    return null;
  }
}

export function planInstall(target, source) {
  if (!existsSync(target)) return { action: "install", installed_version: null };
  const manifest = readManifest(target);
  if (!manifest) return { action: "blocked", installed_version: null, reason: NOT_OURS };
  const current = manifest.version === source.version && manifest.digest === source.digest;
  return { action: current ? "unchanged" : "update", installed_version: manifest.version };
}

export function planUninstall(target) {
  if (!existsSync(target)) return { action: "absent", installed_version: null };
  const manifest = readManifest(target);
  if (!manifest) return { action: "blocked", installed_version: null, reason: NOT_OURS };
  return { action: "remove", installed_version: manifest.version };
}

/** Copy the skill next to its destination first, then swap, so a failed copy leaves the old install intact. */
export function applyInstall(target, source) {
  const staging = join(dirname(target), `.${SKILL_NAME}.staging-${process.pid}`);
  mkdirSync(dirname(target), { recursive: true });
  // A setup that was killed while copying left its half-made copy here, where an agent could load it as a second skill.
  for (const name of readdirSync(dirname(target))) {
    if (name.startsWith(`.${SKILL_NAME}.staging-`)) rmSync(join(dirname(target), name), { recursive: true, force: true });
  }
  try {
    cpSync(source.dir, staging, { recursive: true, filter: (path) => !isJunk(basename(path)) });
    const manifest = { package: PACKAGE, version: source.version, digest: source.digest, installed_at: new Date().toISOString() };
    writeFileSync(join(staging, MANIFEST), `${JSON.stringify(manifest, null, 2)}\n`);
    rmSync(target, { recursive: true, force: true });
    renameSync(staging, target);
  } finally {
    // After a successful rename there is nothing left to remove; after a failure this is the half-made copy.
    rmSync(staging, { recursive: true, force: true });
  }
}

export function applyUninstall(target) {
  rmSync(target, { recursive: true, force: true });
}
