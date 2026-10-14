---
name: project-setup
description: Set up or repair a research project so every coding agent (Claude Code and OpenAI Codex) finds the same instructions - one AGENTS.md per project with a CLAUDE.md that imports it, CODE_MAP.md (packages, modules, entry points, code-health flags) and ENVIRONMENTS.md (each environment, its main packages, what it is for), a handover/ folder for task records, one git worktree per task under .claude/worktrees/, and pixi for new environments. Works on new folders and on existing projects, where it surveys the code and environments and fills the gaps from the project's own documents. Use when starting a project, when a project lacks these files or has competing CLAUDE.md/AGENTS.md files, when agents keep missing a project's rules, or when the user asks for "the AGENTS.md / handover structure".
---

# Project setup

The result, per project:

| File | Loaded | Holds |
|---|---|---|
| `AGENTS.md` | every session (keep it 60-120 lines) | purpose, trust order, start-here table, layout, commands, workflow, rules, traps and caveats |
| `CLAUDE.md` | every Claude Code session | a title and `@AGENTS.md`, nothing else |
| `CODE_MAP.md` | when working on code | packages and modules with their purpose, entry points, frozen code, code-health decisions |
| `ENVIRONMENTS.md` | when running code | every environment: location or manifest, main packages and versions, what it is for, how to run it |
| `handover/INDEX.md` | at the start of a task | one row per agent task folder |

**One instruction file, `AGENTS.md`, and a `CLAUDE.md` that imports it, both tracked in the repo.** Codex reads
`AGENTS.md` natively. Claude Code reads it on its own only when there is no `CLAUDE.md` or `CLAUDE.local.md` in the
working folder or any folder above it, and otherwise skips it without a sign
([docs](https://code.claude.com/docs/en/memory#when-claude-code-reads-agentsmd)). A `CLAUDE.md` holding only
`@AGENTS.md` keeps it loaded in every case, and never loads it twice. Instructions go in `AGENTS.md` only, so the two
files can't drift apart. Because both are tracked, every worktree carries them, and no agent settings are needed.

**Repos that follow quadbio's `analysis-workflow`** (their `.claude/settings.json` enables
`analysis-workflow@quadbio`, or they were made from `analysis_template`) already have `AGENTS.md`, a `CLAUDE.md`
that imports it, and `.claude/worktrees/`, and keep task records in task directories instead of `handover/`. Follow those; don't add
`handover/`. Offer only `CODE_MAP.md` and `ENVIRONMENTS.md` there, and only if the user wants them. The survey
reports when a repo is one of these.

## 1. Survey (read only)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/setup_project.py" <project_dir> [--code-dir <dir>]
```

Reports git status, the code folder (default `code/`, else the project root), which of the files above exist, a
`CLAUDE.md` that holds instructions instead of only importing `AGENTS.md` or a lowercase `agents.md` to convert and
the files that mention them, worktrees, whether `.claude/worktrees/` is ignored, and what it would create. Before changing anything, check for other agent sessions,
uncommitted work and running jobs in the project.

## 2. Create what is missing

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/setup_project.py" <project_dir> --go
```

Creates only missing files, never overwrites or deletes: `AGENTS.md` from the template (skipped when a `CLAUDE.md`
holds the instructions: convert that instead, step 5), `CLAUDE.md` with the import, `ENVIRONMENTS.md` and `CODE_MAP.md` from their templates **with a survey
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
- **The instruction files live in the repo:** when the repo is the project root, `AGENTS.md` and `CLAUDE.md` are
  tracked there and each worktree carries them. When the project folder sits above the repo, put both in the repo,
  not above it, so worktrees and both agents see them.

## 5. Convert CLAUDE.md / agents.md

Instructions in `AGENTS.md`, and a `CLAUDE.md` that only imports it:
- `CLAUDE.md` with instructions and no `AGENTS.md`: rename it to `AGENTS.md` (`git mv` when tracked), content
  unchanged, create a new `CLAUDE.md` from `templates/CLAUDE.md`, then fill gaps as in step 3.
- Both exist and `CLAUDE.md` holds instructions: merge them into `AGENTS.md`, then reduce `CLAUDE.md` to the title
  and `@AGENTS.md`.
- A `CLAUDE.md` that already holds only `@AGENTS.md` (as `analysis_template` ships it) is correct: keep it. So is a
  `CLAUDE.md` that is a symlink to `AGENTS.md`. To replace any symlinked `CLAUDE.md`, remove the link first
  (`git rm` when tracked), then create the file: writing to the link overwrites the file it points to.
- Imports resolve relative to the file that holds them: in `.claude/CLAUDE.md` the line is `@../AGENTS.md`, since
  `@AGENTS.md` there means `.claude/AGENTS.md`.
- A `.claude/CLAUDE.md` with instructions: merge them into `AGENTS.md` as well, and keep one importing `CLAUDE.md`.
- A `CLAUDE.local.md` or a `CLAUDE.md` in a folder above the repo needs no change: the import still loads `AGENTS.md`.
- Lowercase `agents.md` is loaded by neither agent: rename it, or keep it as package documentation and point to it.
- Update the references the survey listed (links, provenance strings) that point at instructions which moved; leave
  archives and generated manifests. Do not commit other people's uncommitted work along with yours.

## 6. Register and verify

- If the user keeps a lab or project map (their global instructions say where), add one row for the project.
- **Both agents:** ask a question only `AGENTS.md` answers, without letting them read files. Claude:
  `cd <project_dir> && claude -p "Without running commands or reading files: according to your project instructions,
  <question>? Answer briefly, or NONE."`; Codex: the same prompt with `codex exec -s read-only "..."`. Repeat inside
  a worktree. If Claude answers NONE, check that `CLAUDE.md` holds the `@AGENTS.md` line.
- Report what was created, what was filled from which source, what is marked "(to confirm)", and the verification results.
