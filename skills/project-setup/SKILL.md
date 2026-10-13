---
name: project-setup
description: Set up or repair a research project so every coding agent (Claude Code and OpenAI Codex) finds the same instructions - one AGENTS.md per project, CODE_MAP.md (packages, modules, entry points, code-health flags) and ENVIRONMENTS.md (each environment, its main packages, what it is for), a handover/ folder for task records, one git worktree per task under .claude/worktrees/, and pixi for new environments. Works on new folders and on existing projects, where it surveys the code and environments and fills the gaps from the project's own documents. Use when starting a project, when a project lacks these files or has competing CLAUDE.md/AGENTS.md files, when agents keep missing a project's rules, or when the user asks for "the AGENTS.md / handover structure".
---

# Project setup

The result, per project:

| File | Loaded | Holds |
|---|---|---|
| `AGENTS.md` | every session (keep it 60-120 lines) | purpose, trust order, start-here table, layout, commands, workflow, rules, traps and caveats |
| `CODE_MAP.md` | when working on code | packages and modules with their purpose, entry points, frozen code, code-health decisions |
| `ENVIRONMENTS.md` | when running code | every environment: location or manifest, main packages and versions, what it is for, how to run it |
| `handover/INDEX.md` | at the start of a task | one row per agent task folder |

**One instruction file, `AGENTS.md`, tracked in the repo.** Codex reads it natively. Claude Code (v2.1.277 or later)
reads it when there is no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` in the working folder or any folder
above it ([docs](https://code.claude.com/docs/en/memory#agents-md)); the user's own `~/.claude/CLAUDE.md` doesn't
count. Because it is tracked, every worktree carries it, and no agent settings are needed. A `CLAUDE.md` next to it
or above it makes Claude read only the `CLAUDE.md`, so the two drift apart: keep one file.

**Repos that follow quadbio's `analysis-workflow`** (their `.claude/settings.json` enables
`analysis-workflow@quadbio`, or they were made from `analysis_template`) already have `AGENTS.md` and
`.claude/worktrees/`, and keep task records in task directories instead of `handover/`. Follow those; don't add
`handover/`. Offer only `CODE_MAP.md` and `ENVIRONMENTS.md` there, and only if the user wants them. The survey
reports when a repo is one of these.

## 1. Survey (read only)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/setup_project.py" <project_dir> [--code-dir <dir>]
```

Reports git status, the code folder (default `code/`, else the project root), which of the files above exist, any
`CLAUDE.md` / `CLAUDE.local.md` / lowercase `agents.md` to convert and the files that mention them, worktrees, whether
`.claude/worktrees/` is ignored, and what it would create. Before changing anything, check for other agent sessions,
uncommitted work and running jobs in the project.

## 2. Create what is missing

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/setup_project.py" <project_dir> --go
```

Creates only missing files, never overwrites or deletes: `AGENTS.md` from the template (skipped when a `CLAUDE.md`
exists: convert that instead, step 5), `ENVIRONMENTS.md` and `CODE_MAP.md` from their templates **with a survey
draft appended** (`scripts/survey_envs.py`, `scripts/survey_code.py`), and `handover/INDEX.md`. Both survey scripts
can also be run on their own and print Markdown.

## 3. Fill the gaps from the project's own material (existing projects)

The drafts are mechanical; the agent turns them into a useful description. Scope this research (see the
`research-workflow` skill in this plugin): read the README, existing instruction files, handover and design
documents, workflow READMEs, configs, and what the user has told agents about the project, not the whole tree.
- **CODE_MAP.md:** write each package's and entry folder's purpose from docstrings and READMEs; name what each
  module owns; list frozen folders; for each survey flag (same function name in several modules, modules over
  800 lines, missing docstrings, more classes than functions) record a decision: consolidate, split, or keep, and why.
  Do not refactor during setup; propose it as a separate task.
- **ENVIRONMENTS.md:** for each environment the code uses, keep the location and main packages from the draft,
  write "used for" from the files that call it, add how to run it and how to recreate it (manifest or lockfile),
  and mark stale or unfound environments. It is the only source for environments; say so.
- **AGENTS.md:** fill every section from the template that has something to say: purpose, trust order, start-here
  table (pointing to documents, not copying them), layout, code and environment summaries (one line each, pointing
  to the two files), commands, workflow, rules, traps and interpretation caveats, hosts.
- **An existing AGENTS.md is not rewritten:** compare it with the template and propose the missing sections as a
  diff for the user to approve.
- Mark anything uncertain "(to confirm)", and remove the survey draft sections once their content is used.

## 4. Conventions to write into the project

- **Worktrees:** one task = one git worktree = one branch, under `.claude/worktrees/<name>`. The user starts the
  session with `claude --worktree <name>` from the main checkout, which creates it there; an agent adding one itself
  uses `git worktree add .claude/worktrees/<name> -b <branch>`. Keep `.claude/worktrees/` in `.gitignore`. Check
  `git worktree list` before starting; remove the worktree after merging (the branch history stays). Outputs go to the
  project's results tree and the task's `handover/` folder, never into a worktree, so removing it loses nothing.
  Existing layouts that bundle a worktree with job and output folders can stay; new tasks use this.
- **Environments: pixi for new ones.** A pixi environment is defined by `pixi.toml` plus an exact `pixi.lock`, both
  committed, so anyone reproduces it with `pixi install`. Existing conda/mamba environments stay in use and are
  listed in `ENVIRONMENTS.md`; replace one only as its own task. Do not build a pixi environment inside every
  worktree: run the main checkout's environment (e.g. `pixi run --manifest-path <main checkout>/pixi.toml ...`)
  or a small wrapper. On shared servers and clusters keep environments and the pixi cache out of home and
  backed-up storage (pixi's `detached-environments` setting and `PIXI_CACHE_DIR`).
- **The instruction file lives in the repo:** when the repo is the project root, `AGENTS.md` is tracked there and each
  worktree carries it. When the project folder sits above the repo, put `AGENTS.md` in the repo, not above it, so
  worktrees and both agents see it.

## 5. Convert CLAUDE.md / agents.md

One file, not two:
- `CLAUDE.md` and no `AGENTS.md`: rename it (`git mv` when tracked), content unchanged, then fill gaps as in step 3.
- Both exist: merge into `AGENTS.md`, then remove `CLAUDE.md`.
- A `CLAUDE.md` in a folder above the repo, or a `CLAUDE.local.md`, also stops Claude from reading `AGENTS.md`: move
  what it holds into `AGENTS.md` or the user's `~/.claude/CLAUDE.md`, with the user's OK.
- Lowercase `agents.md` is loaded by neither agent: rename it, or keep it as package documentation and point to it.
- Update the references the survey listed (links, provenance strings); leave archives and generated manifests.
  Do not commit other people's uncommitted work along with yours.

## 6. Register and verify

- If the user keeps a lab or project map (their global instructions say where), add one row for the project.
- **Claude:** start a new session in the project; it shows `AGENTS.md loaded: <path>`. If it doesn't, a `CLAUDE.md`
  or `CLAUDE.local.md` above it is in the way, or Claude Code is older than v2.1.277.
- **Codex:** ask a question only the new file answers, without letting it read files:
  `cd <project_dir> && codex exec -s read-only "Without running commands or reading files: according to your project
  instructions, <question>? Answer briefly, or NONE."` Repeat inside a worktree.
- Report what was created, what was filled from which source, what is marked "(to confirm)", and the verification results.
