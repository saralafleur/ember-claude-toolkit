# ember-toolkit

Sara LaFleur's source-of-truth marketplace for her Claude Code skills and agents, grouped into installable plugins.

## What's inside

| Plugin | What it does |
|---|---|
| [`delivery-team`](plugins/delivery-team) | Five virtual delivery teams (intake, qa, build, release, status) that run a request through plan → test → build → release, plus a read-only status reconciler. |
| [`librarian`](plugins/librarian) | Curates durable knowledge into a shared, growing library — organized by domain/subdomain/topic, with retrieval descriptions and human-gated writes. |
| [`time-ledger`](plugins/time-ledger) | Cross-project time, token, and cost ledger built from Claude Code session transcripts — daily/weekly/monthly rollups and per-initiative journey artifacts. |
| [`dev-workflow`](plugins/dev-workflow) | `wrap-up` (close out a unit of work — audit, human gate, commit, push, merge, clean up) and `create-skill-devops` (scaffold a project-scoped `/devops` toolbox). |
| [`story-map`](plugins/story-map) | Scaffolds a complete UAT story map for an application — discovers roles/workflows/routes and generates a role-first test folder tree plus ready-to-run Playwright MCP UAT execution and status-reset agent prompts. |

## Install (Claude Code)

**1. Add this marketplace** — from GitHub:

```
/plugin marketplace add saralafleur/ember-claude-toolkit
```

Or from a local clone:

```
/plugin marketplace add /path/to/ember-claude-toolkit
```

**2. Install a plugin:**

```
/plugin install delivery-team@ember-toolkit
/plugin install librarian@ember-toolkit
/plugin install time-ledger@ember-toolkit
/plugin install dev-workflow@ember-toolkit
/plugin install story-map@ember-toolkit
```

**3. Reload** — run `/reload-plugins` to activate immediately, or restart your Claude Code session.

### Managing plugins

| Action | Command |
|---|---|
| List added marketplaces | `/plugin marketplace list` |
| List installed plugins | `/plugin list` |
| Refresh a marketplace's catalog (pull latest) | `/plugin marketplace update ember-toolkit` |
| Disable a plugin | `/plugin disable <name>@ember-toolkit` |
| Re-enable a plugin | `/plugin enable <name>@ember-toolkit` |
| Uninstall a plugin | `/plugin uninstall <name>@ember-toolkit` |
| Remove the marketplace entirely | `/plugin marketplace remove ember-toolkit` |

## Install (other tools)

This repo ports every plugin above into four other AI coding tools. Two have a real "point at this repo" marketplace, like Claude Code does; the other two require running the bundled install script after cloning, because those tools have no repo-pointer install mechanism at all.

### VS Code / GitHub Copilot (Agent Plugins, Preview)

Same shape as Claude Code's marketplace — a `.github/plugin/marketplace.json` at this repo's root lists all 5 plugins.

1. Register the marketplace — either add this to your VS Code `settings.json`:
   ```json
   "chat.plugins.marketplaces": ["saralafleur/ember-claude-toolkit"]
   ```
   or run **`Chat: Install Plugin From Source`** from the Command Palette and paste this repo's URL.
2. Browse and install any plugin by name from the Extensions view (`@agentPlugins`).

This is a VS Code **Preview** feature — the manifest schema may still shift. Each generated `.github/agents/*.agent.md` file has inline `<!-- assumption: ... -->` comments wherever a field was a best-effort guess (tool ids, `model`, delegation fields) rather than confirmed against a stable spec.

### Cursor, Gemini CLI, and Google Antigravity — via the install script

None of these three support installing from a repo pointer — Cursor and Antigravity require files to be copied into a local config directory, and Gemini CLI's `gemini extensions install` only accepts one extension per install call. The bundled script automates all three:

```bash
git clone https://github.com/saralafleur/ember-claude-toolkit.git
cd ember-claude-toolkit
node scripts/install.mjs <tool> [plugin-name|--all] [--local]
```

| Argument | Values |
|---|---|
| `<tool>` | `cursor`, `gemini`, or `antigravity` |
| `plugin-name` | `delivery-team`, `librarian`, `time-ledger`, `dev-workflow`, `story-map` — omit or pass `--all` for every plugin |
| `--local` | Install into the current project's `.cursor/`/`.agents/` instead of your user-global config. Not used by `gemini` (it manages its own install location). |

Examples:
```bash
node scripts/install.mjs cursor --all              # every plugin, globally, for Cursor
node scripts/install.mjs cursor story-map --local   # just story-map, this project only
node scripts/install.mjs gemini delivery-team        # installs via `gemini extensions install`
node scripts/install.mjs antigravity --all
```

**Requirements:** Node.js (any reasonably current version — if you already run Claude Code or Gemini CLI you already have it; both are npm-installed). For `gemini`, the `gemini` CLI itself must already be installed and on your `PATH` — the script checks and tells you how to install it if it's missing. Restart the target tool/session after installing for changes to take effect.

**Antigravity note:** its CLI can also import an already-installed Gemini CLI extension directly, so `node scripts/install.mjs gemini <plugin>` followed by Antigravity's own import command is a valid alternative path if you'd rather not run the script's `antigravity` target.

## Publishing changes

After editing anything under `plugins/<name>/`, run `/refresh-plugins` from this repo — it runs the `/sanitize-plugins` privacy/IP/secrets gate, validates the changed plugin(s) and `marketplace.json`, bumps semver, commits, tags, and pushes.
