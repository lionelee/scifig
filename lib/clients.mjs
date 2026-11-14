import { existsSync, readFileSync } from "node:fs";
import { basename, dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// The agents setup finds, and where each one reads skills: the same as rea-agents 6.9.0
// (dist/application/SupportedClients.js). An agent is present when its configuration file or its own
// folder exists. Its skill goes into its own skills folder where it has one; every other agent reads the
// shared ~/.agents/skills, which then holds one copy for all of them. Where rea-agents resolves a home
// through Windows package storage (Claude Desktop installed from the Microsoft Store), this follows the
// default folder and the environment overrides only. imageTool is the agent's built-in image generation
// tool, where it is known to have one.
//
// Each function takes { home, env, platform }.

export const sharedSkillsDir = ({ home }) => join(home, ".agents", "skills");

const xdg = ({ home, env }) => env.XDG_CONFIG_HOME || join(home, ".config");
const roaming = ({ home, env }) => env.APPDATA || join(home, "AppData", "Roaming");
const macSupport = ({ home }) => join(home, "Library", "Application Support");
const expandHome = (path, home) => (path === "~" ? home : /^~[/\\]/.test(path) ? join(home, path.slice(2)) : path);

const claudeCodeDir = ({ home, env }) => env.CLAUDE_CONFIG_DIR || join(home, ".claude");
const codexDir = ({ home, env }) => env.CODEX_HOME || join(home, ".codex");
const geminiCliHome = ({ home, env }) => env.GEMINI_CLI_HOME || home;
const qoderDir = ({ home, env }) => env.QODER_CONFIG_DIR || join(home, ".qoder");
const factoryDir = ({ home, env }) => join(env.FACTORY_HOME_OVERRIDE || home, ".factory");
const dshDir = (home, override, fallback) => resolve(expandHome(override?.trim() ? override : join(home, fallback), home));

function claudeDesktopDir(context) {
  if (context.platform === "win32") return join(roaming(context), "Claude");
  return context.platform === "darwin" ? join(macSupport(context), "Claude") : join(xdg(context), "Claude");
}

function editorUserDir(context, product) {
  if (context.platform === "win32") return join(roaming(context), product, "User");
  return context.platform === "darwin" ? join(macSupport(context), product, "User") : join(xdg(context), product, "User");
}

function vscodeUserDir(context) {
  const { env } = context;
  if (env.VSCODE_PORTABLE) return join(env.VSCODE_PORTABLE, "user-data", "User");
  if (env.VSCODE_APPDATA) return join(env.VSCODE_APPDATA, "Code", "User");
  return editorUserDir(context, "Code");
}

/** Cline CLI's settings file: its overrides in Cline's order, then ~/.cline. */
function clineSettings({ home, env }) {
  if (env.CLINE_MCP_SETTINGS_PATH?.trim()) return env.CLINE_MCP_SETTINGS_PATH.trim();
  if (env.CLINE_DATA_DIR?.trim()) return join(env.CLINE_DATA_DIR.trim(), "settings", "cline_mcp_settings.json");
  if (env.CLINE_DIR?.trim()) return join(env.CLINE_DIR.trim(), "data", "settings", "cline_mcp_settings.json");
  return join(home, ".cline", "data", "settings", "cline_mcp_settings.json");
}

function openCodeDirs({ home, env, platform }) {
  const standard = join(xdg({ home, env, platform }), "opencode");
  return [env.OPENCODE_CONFIG_DIR || standard, standard, env.OPENCODE_CONFIG].filter(Boolean);
}

/** LM Studio's home: the folder its pointer file names, else ~/.cache/lm-studio where it exists, else ~/.lmstudio. */
function lmStudioDir({ home }) {
  try {
    const pointed = readFileSync(join(home, ".lmstudio-home-pointer"), "utf8").trim();
    if (isAbsolute(pointed)) return pointed;
  } catch {
    // no pointer file: LM Studio uses one of its default homes
  }
  const cache = join(home, ".cache", "lm-studio");
  return existsSync(cache) ? cache : join(home, ".lmstudio");
}

function ompDir({ home, env }) {
  const root = join(home, env.PI_CONFIG_DIR || ".omp");
  const profile = (env.OMP_PROFILE ?? env.PI_PROFILE)?.trim();
  if (profile && profile !== "default") return join(root, "profiles", profile, "agent");
  return env.PI_CODING_AGENT_DIR ? resolve(env.PI_CODING_AGENT_DIR) : join(root, "agent");
}

function piDir({ home, env }) {
  const override = env.PI_CODING_AGENT_DIR;
  if (!override) return join(home, ".pi", "agent");
  return override.startsWith("file://") ? fileURLToPath(override) : expandHome(override, home);
}

/** Hermes' home, with the profile Hermes CLI keeps active in it. */
function hermesHome({ home, env, platform }) {
  const suffix = env.HERMES_DATA_DIR_SUFFIX ?? "";
  const root = env.HERMES_HOME?.trim()
    ? resolve(expandHome(env.HERMES_HOME.trim(), home))
    : platform === "win32"
      ? join(env.LOCALAPPDATA?.trim() || join(home, "AppData", "Local"), `hermes${suffix}`)
      : join(home, `.hermes${suffix}`);
  if (basename(dirname(root)) === "profiles") return root; // a profile named outright
  try {
    const name = readFileSync(join(root, "active_profile"), "utf8").trim().toLowerCase();
    const profile = join(root, "profiles", name);
    if (name !== "default" && /^[a-z0-9][a-z0-9_-]{0,63}$/.test(name) && existsSync(profile)) return profile;
  } catch {
    // no active profile: the home itself
  }
  return root;
}

function grokBotDir({ home, env }) {
  return env.SAND_DATA_ROOT && isAbsolute(env.SAND_DATA_ROOT) ? env.SAND_DATA_ROOT : join(home, ".grokbot");
}

/** In the order rea-agents lists them. evidence: paths of which any proves the agent is present. */
export const CLIENTS = [
  {
    id: "claude_code",
    label: "Claude Code",
    evidence: (c) => [claudeCodeDir(c), join(c.env.CLAUDE_CONFIG_DIR || c.home, ".claude.json")],
    skillsDir: (c) => join(claudeCodeDir(c), "skills"),
  },
  { id: "claude_desktop", label: "Claude Desktop", evidence: (c) => [claudeDesktopDir(c)] },
  { id: "codex", label: "Codex", evidence: (c) => [codexDir(c)], imageTool: "image_gen" },
  { id: "cursor", label: "Cursor", evidence: (c) => [join(c.home, ".cursor")] },
  {
    id: "codebuddy",
    label: "CodeBuddy",
    evidence: (c) => [join(c.home, ".codebuddy")],
    skillsDir: (c) => join(c.home, ".codebuddy", "skills"),
  },
  { id: "cline", label: "Cline CLI", evidence: (c) => [clineSettings(c), dirname(clineSettings(c))] },
  {
    id: "gemini_cli",
    label: "Gemini CLI",
    evidence: (c) => [join(geminiCliHome(c), ".gemini")],
    skillsDir: (c) => join(geminiCliHome(c), ".agents", "skills"),
  },
  { id: "windsurf", label: "Windsurf", evidence: (c) => [join(c.home, ".codeium", "windsurf")] },
  {
    id: "devin",
    label: "Devin",
    evidence: (c) => [c.platform === "win32" ? join(roaming(c), "devin") : join(xdg(c), "devin")],
  },
  { id: "opencode", label: "OpenCode", evidence: openCodeDirs },
  {
    id: "antigravity",
    label: "Antigravity",
    evidence: (c) => [join(c.home, ".gemini", "config")],
    skillsDir: (c) => join(c.home, ".gemini", "config", "skills"),
    imageTool: "generate_image",
  },
  { id: "copilot_cli", label: "GitHub Copilot CLI", evidence: (c) => [c.env.COPILOT_HOME || join(c.home, ".copilot")] },
  { id: "commandcode", label: "Command Code", evidence: (c) => [join(c.home, ".commandcode")] },
  {
    id: "qwen_code",
    label: "Qwen Code",
    evidence: (c) => [c.env.QWEN_HOME ? resolve(expandHome(c.env.QWEN_HOME, c.home)) : join(c.home, ".qwen")],
  },
  { id: "kimi", label: "Kimi Code", evidence: (c) => [c.env.KIMI_CODE_HOME || join(c.home, ".kimi-code")] },
  { id: "vscode", label: "VS Code", evidence: (c) => [vscodeUserDir(c)] },
  {
    id: "trae",
    label: "Trae",
    evidence: (c) => [editorUserDir(c, "Trae")],
    skillsDir: (c) => join(c.home, ".trae", "skills"),
  },
  {
    id: "workbuddy",
    label: "WorkBuddy",
    evidence: (c) => [join(c.home, ".workbuddy")],
    skillsDir: (c) => join(c.home, ".workbuddy", "skills"),
  },
  { id: "lm_studio", label: "LM Studio", evidence: (c) => [lmStudioDir(c)] },
  { id: "grok_build", label: "Grok Build", evidence: (c) => [c.env.GROK_HOME || join(c.home, ".grok")] },
  { id: "omp", label: "OMP", evidence: (c) => [ompDir(c)] },
  { id: "pi", label: "Pi", evidence: (c) => [piDir(c)] },
  { id: "hermes", label: "Hermes", evidence: (c) => [hermesHome(c)], skillsDir: (c) => join(hermesHome(c), "skills") },
  { id: "qoder", label: "Qoder", evidence: (c) => [qoderDir(c)], skillsDir: (c) => join(qoderDir(c), "skills") },
  { id: "droid", label: "Factory Droid", evidence: (c) => [factoryDir(c)], skillsDir: (c) => join(factoryDir(c), "skills") },
  {
    id: "zcode",
    label: "ZCode",
    evidence: (c) => [join(c.home, ".zcode", "cli")],
    skillsDir: (c) => join(c.home, ".zcode", "skills"),
  },
  {
    id: "dsh",
    label: "DeepSeek Harness",
    evidence: (c) => [dshDir(c.home, c.env.DSH_HOME, ".dsh")],
    skillsDir: (c) => join(dshDir(c.home, c.env.DSH_AGENTS_HOME, ".agents"), "skills"),
  },
  {
    id: "freebuff",
    label: "FreeBuff",
    evidence: (c) => [join(c.home, ".config", "freebuff-desktop")],
    skillsDir: sharedSkillsDir,
  },
  { id: "grok_bot", label: "Grok Bot", evidence: (c) => [grokBotDir(c)] },
];

/** Where an agent reads the skill: its own skills folder, or the shared one. */
export const skillsDirOf = (client, context) => (client.skillsDir ? client.skillsDir(context) : sharedSkillsDir(context));

/** Is the agent installed: does its configuration file or its own folder exist? */
export const isPresent = (client, context) => client.evidence(context).some((path) => existsSync(path));
