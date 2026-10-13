---
name: project-setup
description: Set up or repair a research project so every coding agent (Claude Code and OpenAI Codex) finds the same instructions - a CLAUDE.md per project, CODE_MAP.md (packages, modules, entry points, code-health flags) and ENVIRONMENTS.md (each environment, its main packages, what it is for), a handover/ folder for task records, one git worktree per task, pixi for new environments, and a check that both agents load the instructions. Works on new folders and on existing projects, where it surveys the code and environments and fills the gaps from the project's own documents. Use when starting a project, when a project lacks these files or has competing AGENTS.md/agents.md files, when agents keep missing a project's rules, or when the user asks for "the CLAUDE.md / handover structure".
---

# Project setup

The result, per project:

| File | Loaded | Holds |
|---|---|---|
| `CLAUDE.md` | every session (keep it 60-120 lines) | purpose, trust order, start-here table, layout, commands, workflow, rules, traps and caveats |
| `CODE_MAP.md` | when working on code | packages and modules with their purpose, entry points, frozen code, code-health decisions |
| `ENVIRONMENTS.md` | when running code | every environment: location or manifest, main packages and versions, what it is for, how to run it |
| `handover/INDEX.md` | at the start of a task | one row per agent task folder |

Claude loads `CLAUDE.md` from the start folder and every folder above it. Codex loads `AGENTS.md`, or `CLAUDE.md`
when `~/.codex/config.toml` has `project_doc_fallback_filenames = ["CLAUDE.md"]`, from the project root (by default
the nearest git root) down to the start folder.

**Repos that follow quadbio's `analysis-workflow`** (their `.claude/settings.json` enables
`analysis-workflow@quadbio`, or they were made from `analysis_template`) already have their own conventions:
`AGENTS.md`, task directories, `.claude/worktrees/`. Follow those; do not convert their `AGENTS.md`, add
`handover/` or move worktrees. Offer only `CODE_MAP.md` and `ENVIRONMENTS.md` there, and only if the user wants them.
The survey reports when a repo is one of these.

## 1. Survey (read only)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/setup_project.py" <project_dir> [--code-dir <dir>]
```

Reports git status, the code folder (default `code/`, else the project root), which of the files above and any
`AGENTS.md` / `agents.md` exist, worktrees, what it would create, and whether Codex reads `CLAUDE.md`. Before
changing anything, check for other agent sessions, uncommitted work and running jobs in the project.

## 2. Create what is missing

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/setup_project.py" <project_dir> --go
```

Creates only missing files, never overwrites or deletes: `CLAUDE.md` from the template (skipped when an
`AGENTS.md` exists: convert that instead, step 5), `ENVIRONMENTS.md` and `CODE_MAP.md` from their templates
**with a survey draft appended** (`scripts/survey_envs.py`, `scripts/survey_code.py`), and `handover/INDEX.md`.
Both survey scripts can also be run on their own and print Markdown.

## 3. Fill the gaps from the project's own material (existing projects)

The drafts are mechanical; the agent turns them into a useful description. Scope this research (see the
`research-workflow` skill in this plugin): read the README, existing instruction files, handover and design documents, workflow
READMEs, configs, and what the user has told agents about the project, not the whole tree.
- **CODE_MAP.md:** write each package's and entry folder's purpose from docstrings and READMEs; name what each
  module owns; list frozen folders; for each survey flag (same function name in several modules, modules over
  800 lines, missing docstrings, more classes than functions) record a decision: consolidate, split, or keep, and why.
  Do not refactor during setup; propose it as a separate task.
- **ENVIRONMENTS.md:** for each environment the code uses, keep the location and main packages from the draft,
  write "used for" from the files that call it, add how to run it and how to recreate it (manifest or lockfile),
  and mark stale or unfound environments. It is the only source for environments; say so.
- **CLAUDE.md:** fill every section from the template that has something to say: purpose, trust order, start-here
  table (pointing to documents, not copying them), layout, code and environment summaries (one line each, pointing
  to the two files), commands, workflow, rules, traps and interpretation caveats, hosts.
- **An existing CLAUDE.md is not rewritten:** compare it with the template and propose the missing sections as a
  diff for the user to approve.
- Mark anything uncertain "(to confirm)", and remove the survey draft sections once their content is used.

## 4. Conventions to write into the project

- **Worktrees:** one task = one git worktree = one branch, under `<project>/worktrees/<YYYY-MM-DD>_<slug>`;
  check `git worktree list` before starting; remove the worktree after merging (the branch history stays).
  Outputs go to the project's results tree and the task's `handover/` folder, never into a worktree, so removing it
  loses nothing. Existing layouts that bundle a worktree with job and output folders can stay; new tasks use this.
- **Environments: pixi for new ones.** A pixi environment is defined by `pixi.toml` plus an exact `pixi.lock`, both
  committed, so anyone reproduces it with `pixi install`. Existing conda/mamba environments stay in use and are
  listed in `ENVIRONMENTS.md`; replace one only as its own task. Do not build a pixi environment inside every
  worktree: run the main checkout's environment (e.g. `pixi run --manifest-path <main checkout>/pixi.toml ...`)
  or a small wrapper. On shared servers and clusters keep environments and the pixi cache out of home and
  backed-up storage (pixi's `detached-environments` setting and `PIXI_CACHE_DIR`).
- **One instruction file in every worktree:** track `CLAUDE.md` in the repo when the repo is the project root, so each
  worktree carries it. When the instruction file sits above the repo, Claude still finds it (parent folders), but
  Codex stops at the worktree's git root: see step 6.

## 5. Convert existing AGENTS.md / agents.md

One file, not two: a pointer file makes Codex read only the pointer.
- `AGENTS.md` and no `CLAUDE.md`: rename it (`git mv` when tracked), content unchanged, then fill gaps as in step 3.
- Both exist: merge into `CLAUDE.md`, then remove `AGENTS.md`.
- Lowercase `agents.md` is loaded by neither agent: rename it, or keep it as package documentation and point to it.
- Update the references the survey listed (links, provenance strings); leave archives and generated manifests.
  Do not commit other people's uncommitted work along with yours.

## 6. Codex settings

- `~/.codex/config.toml`: `project_doc_fallback_filenames = ["CLAUDE.md"]`, and `project_doc_max_bytes = 65536` when an
  instruction file exceeds Codex's 32 KiB default. Ask before changing the user's config; keep a backup.
- Instruction file above the git root (worktrees, nested repos): `project_root_markers = [".agent_project_root"]` plus
  the marker in the project root (`setup_project.py --codex-marker`, which also adds it to `.git/info/exclude`). This
  changes Codex everywhere: a folder with no marker above it reads only its own file, and on some clusters the upward
  search hits unreadable system folders and fails, so also put a marker at the top of each of the user's own trees
  (home, scratch, work) and test.

## 7. Register and verify

- If the user keeps a lab or project map (their global instructions say where), add one row for the project.
- **Codex:** ask a question only the new file answers, without letting it read files:
  `cd <project_dir> && codex exec -s read-only --skip-git-repo-check "Without running commands or reading files:
  according to your project instructions, <question>? Answer briefly, or NONE."` Repeat inside a worktree.
- **Claude:** loads `CLAUDE.md` at session start; check in a new session started in the project.
- Report what was created, what was filled from which source, what is marked "(to confirm)", and the verification results.
