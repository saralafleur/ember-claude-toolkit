#!/usr/bin/env node
// Installs ember-toolkit plugins into tools with no native "point at this repo"
// marketplace: Cursor, Gemini CLI, and Google Antigravity. Runs identically on
// macOS, Linux, and Windows (no chmod, no PowerShell execution-policy prompt).
//
// Claude Code and VS Code Copilot are NOT handled here — both have a real
// marketplace command of their own. See the root README.md for those.
//
// Usage:
//   node scripts/install.mjs <tool> [plugin-name|--all] [--local]
//
//   tool          cursor | gemini | antigravity
//   plugin-name   delivery-team | librarian | time-ledger | dev-workflow | story-map
//                 (omit, or pass --all, to install every plugin)
//   --local       install into the current directory's project-level config
//                 instead of your user-global config. Not used by gemini,
//                 which always installs through its own extensions system.
//
// Examples:
//   node scripts/install.mjs cursor --all
//   node scripts/install.mjs cursor story-map --local
//   node scripts/install.mjs gemini delivery-team
//   node scripts/install.mjs antigravity --all

import { existsSync, mkdirSync, cpSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const PLUGINS_DIR = join(REPO_ROOT, 'plugins');

const ALL_PLUGINS = ['delivery-team', 'librarian', 'time-ledger', 'dev-workflow', 'story-map'];
const TOOLS = ['cursor', 'gemini', 'antigravity'];

function usage() {
  console.log(`
Usage: node scripts/install.mjs <tool> [plugin-name|--all] [--local]

  tool          ${TOOLS.join(' | ')}
  plugin-name   one of: ${ALL_PLUGINS.join(', ')}  (or --all for every plugin)
  --local       install into the current directory's project-level config
                instead of your user-global config (not used by gemini)

Examples:
  node scripts/install.mjs cursor --all
  node scripts/install.mjs cursor story-map --local
  node scripts/install.mjs gemini delivery-team
  node scripts/install.mjs antigravity --all
`);
}

const args = process.argv.slice(2);
const tool = args[0];
const isLocal = args.includes('--local');
const pluginArg = args.find((a, i) => i > 0 && a !== '--local');

if (!tool || !TOOLS.includes(tool)) {
  usage();
  process.exit(tool ? 1 : 0);
}

let plugins;
if (!pluginArg || pluginArg === '--all') {
  plugins = ALL_PLUGINS;
} else if (ALL_PLUGINS.includes(pluginArg)) {
  plugins = [pluginArg];
} else {
  console.error(`Unknown plugin "${pluginArg}". Choose one of: ${ALL_PLUGINS.join(', ')}, or --all\n`);
  usage();
  process.exit(1);
}

function copyNamedSubfolders(srcDir, destDir) {
  if (!existsSync(srcDir)) return false;
  mkdirSync(destDir, { recursive: true });
  for (const name of readdirSync(srcDir)) {
    cpSync(join(srcDir, name), join(destDir, name), { recursive: true });
  }
  return true;
}

function installCursor(plugin) {
  const src = join(PLUGINS_DIR, plugin, 'cursor');
  if (!existsSync(src)) {
    console.warn(`  ! ${plugin}: no Cursor port found, skipping`);
    return;
  }
  const base = isLocal ? join(process.cwd(), '.cursor') : join(homedir(), '.cursor');
  const gotSkills = copyNamedSubfolders(join(src, 'skills'), join(base, 'skills'));
  const gotAgents = copyNamedSubfolders(join(src, 'agents'), join(base, 'agents'));
  console.log(`  ${gotSkills || gotAgents ? '✓' : '!'} ${plugin} → ${base}`);
}

function installAntigravity(plugin) {
  const src = join(PLUGINS_DIR, plugin, 'antigravity');
  if (!existsSync(src)) {
    console.warn(`  ! ${plugin}: no Antigravity port found, skipping`);
    return;
  }
  const base = isLocal
    ? join(process.cwd(), '.agents', 'plugins', plugin)
    : join(homedir(), '.gemini', 'config', 'plugins', plugin);
  mkdirSync(base, { recursive: true });
  cpSync(src, base, { recursive: true });
  console.log(`  ✓ ${plugin} → ${base}`);
}

function installGemini(plugin) {
  const src = join(PLUGINS_DIR, plugin, 'gemini');
  if (!existsSync(src)) {
    console.warn(`  ! ${plugin}: no Gemini CLI port found, skipping`);
    return;
  }
  try {
    execFileSync('gemini', ['--version'], { stdio: 'ignore' });
  } catch {
    console.error(`  ✗ ${plugin}: the \`gemini\` CLI isn't on your PATH.`);
    console.error(`    Install it first (npm install -g @google/gemini-cli), then run:`);
    console.error(`    gemini extensions install "${src}"`);
    return;
  }
  try {
    execFileSync('gemini', ['extensions', 'install', src, '--consent'], { stdio: 'inherit' });
    console.log(`  ✓ ${plugin} installed as a Gemini CLI extension`);
  } catch (err) {
    console.error(`  ✗ ${plugin}: \`gemini extensions install\` failed — ${err.message}`);
  }
}

console.log(`Installing for ${tool}${isLocal ? ' (project-local)' : ' (user-global)'}: ${plugins.join(', ')}\n`);

for (const plugin of plugins) {
  if (tool === 'cursor') installCursor(plugin);
  else if (tool === 'antigravity') installAntigravity(plugin);
  else if (tool === 'gemini') installGemini(plugin);
}

console.log('\nDone. Restart your tool/session for the changes to take effect.');
