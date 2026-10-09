# CK skills

Agent skills for working with CK (arbo adsets, scripts, stats queries, dashboards, titles, image prompts, shared memory).
Every skill is a folder under `skills/` with a `SKILL.md` (the open Agent Skills format), so the same files work in Claude, Codex and Hermes.

| Skill | What it does |
|---|---|
| `arbo-adset-actions` | Change live adsets: kill, pause, activate, budget, cost cap, duplicates, clones, replicates |
| `arbo-cap-scout` | Find proven test adsets and clone them into cost cap adsets |
| `arbo-competitor-scout` | Pull competitors' grown Meta Ad Library ads into a local db and turn their angles into new titles |
| `arbo-dashboards` | Build live dashboards and home-page widgets from stats queries |
| `arbo-generate-image-prompt` | Design and manage base prompts for AI ad images |
| `arbo-memory` | Shared division memory: objectives, decisions, insights, journal, tasks with handovers |
| `arbo-scripts` | Write, explain and fix arbo scripts |
| `arbo-scripts-rebalance` | Review a division's automated scripts as one system |
| `arbo-stat-queries` | Answer adset performance questions with stats queries |
| `arbo-title-creator` | Create article/ad titles by chatting |
| `arbo-title-scout` | Size and place a batch of new titles to test |
| `arbo-title-templates` | Review, validate and add the title templates behind daily title suggestions |

All skills need the CK MCP connection. `arbo-competitor-scout` also needs `python3` and a browser tool, and keeps its db in the user's own project folder (`./competitors/`), never in this repo.

## Concepts

**Verticals and themes** are the same thing: the topic a title, article and adset belongs to. A vertical is top level, and a theme is its child. They are separate only for legacy reasons. A theme narrows its vertical and never goes beyond its scope: a theme under `Sale` can't be about jobs. Names are unique across both, and a theme name works anywhere a vertical name does (titles, stats, queries). `get_verticals` returns both with `isTopLevel` / `parentVertical`. Agents create themes with `create_theme` only when the user asks. When nothing fits, agents recommend a new vertical, and the user adds it by hand. Every skill that picks verticals carries this explanation, because skills must stay self-contained.

## Install

The repo is a plugin marketplace (`arbo-skills`) with one plugin (`arbo-skills`) that holds every skill in `skills/`. Skills show up as `arbo-skills:<skill>`, e.g. `/arbo-skills:arbo-adset-actions`.

**Claude Code**
```
/plugin marketplace add aco228/arbo-skills
/plugin install arbo-skills@arbo-skills
```

**Codex**
```
codex plugin marketplace add aco228/arbo-skills
```
Then install `arbo-skills` from the plugin browser (`/plugins` inside Codex). Codex reads the same `.claude-plugin/marketplace.json`; its manifest is `.codex-plugin/plugin.json`.

**Hermes**
```
hermes skills tap add aco228/arbo-skills
hermes skills install <skill-name>
```
Or, with a local clone, add its `skills` folder to `skills.external_dirs` in `~/.hermes/config.yaml` and just `git pull` to update.

## Versioning

The plugin has an explicit `version` in both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` (keep them the same, and never put a `version` in `marketplace.json`). Claude Code and Codex only hand out a new copy of the plugin when that string changes, so **every change to a skill must bump the version** in both files before it's pushed:

- patch (`1.1.0` → `1.1.1`): wording fixes, small edits to an existing skill
- minor (`1.1.0` → `1.2.0`): a new skill, or new tools/parameters in a skill
- major (`1.x` → `2.0.0`): a skill removed or renamed

## Updating

After a new version is pushed, each tool pulls it like this. Start a new session (or reload, where listed) after updating so the new skill text is loaded.

**Claude Code**

In the app (terminal CLI, desktop or IDE):
```
/plugin marketplace update arbo-skills
/reload-plugins
```
To get updates automatically: `/plugin` → **Marketplaces** → `arbo-skills` → **Enable auto-update** (it's off by default).

From the shell:
```
claude plugin marketplace update arbo-skills
claude plugin update arbo-skills@arbo-skills
```
Check what's installed with `claude plugin list`. If it still shows the old version, remove and reinstall: `claude plugin uninstall arbo-skills@arbo-skills`, then `claude plugin install arbo-skills@arbo-skills`.

**Codex**

In the app: open `/plugins`, pick `arbo-skills` and update it. If no update shows up, uninstall and install it again there, then start a new chat.

From the shell:
```
codex plugin marketplace upgrade
```
Then start a new Codex session.

**Hermes**

From the shell:
```
hermes skills check
hermes skills update
```
Add `--force` to `update` to overwrite skills you edited locally, or pass a skill name to update just that one. With a local clone in `skills.external_dirs`, run `git pull` in the clone instead.

In the app: `/reload-skills` re-scans the skills folder in a running session (use it after the shell update), and `/skills` searches, inspects and installs skills.

## Rules for editing

- Skills are self-contained: no references to CK source files or repo paths. Readers only have the skill and the MCP tools.
- One skill per folder, folder name = `name` in the `SKILL.md` frontmatter. A new folder under `skills/` is picked up by every tool automatically; no manifest change needed.

## Upload zips (Claude web and desktop chat)

```bash
python build_zips.py
```

Writes `dist/<skill>.zip` for every skill (or pass skill names to build only those). `dist/` is not committed.
