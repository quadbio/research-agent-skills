# {name}: project rules for agents

<!-- 60-120 lines. Point to documents instead of copying them: this file is loaded into every session.
     Delete any section that has nothing to say. Unsure items are marked "(to confirm)". Written {date}. -->

<One paragraph: what the project is, the data, the main questions, where it stands.>

## Trust order

When sources disagree: (1) code, configs and data manifests; (2) this file; (3) workflow READMEs; (4) `README.md`;
(5) external docs and papers. Every fact has one owner: point at it rather than restating it.

## Start here

| Question | Read |
|---|---|
| What the project is and where it stands | `README.md` |
| Latest work and open threads | `handover/INDEX.md`, then the newest `HANDOVER.md` |
| Code: packages, modules, entry points | `CODE_MAP.md` |
| Environments: which one for what, main packages | `ENVIRONMENTS.md` |
| <pipeline / results / decisions> | `<path>` |

## Layout

```
{name}/
  AGENTS.md          this file (the one instruction file for Claude Code and Codex)
  CODE_MAP.md        packages, modules, scripts; ENVIRONMENTS.md  environments
  <folder>/          <what lives here>
  handover/          agent task records: INDEX.md + one folder per task
  .claude/worktrees/ one git worktree per task, git-ignored (see Workflow)
```

## Code

<Two to five lines: where shared code lives (the package), where entry points live, how parameters are passed
(configs), and the rule that new reusable code goes into the package with tests. Details in `CODE_MAP.md`.>

## Environments

<One line per environment: name, used for. Packages, versions and how to run them: `ENVIRONMENTS.md`, the only
source; copies elsewhere are stale.>

## Commands

| Task | Command |
|---|---|
| Run tests | `<command>` |
| Lint / pre-commit | `<command>` |
| Run the pipeline / a step | `<command>` |
| Submit jobs | `<command or skill>` |

## Workflow

- One task = one git worktree (`.claude/worktrees/<name>`, from `claude --worktree <name>`) = one branch; never
  commit on the main branch.
  Check `git worktree list` (and open pull requests) for overlapping work first. Outputs go to the results tree
  and the task's `handover/` folder, never into the worktree.
- Commit as you go; push and open a pull request when the task is validated; merge only after the user approves.
- **Ask the user before:** overwriting or deleting data, established results or manifested inputs (show a dry run);
  merging; <project-specific items>.
- When a biological or statistical choice is unclear (annotation, threshold, metric, reference, interpretation),
  ask with the evidence, the options and a recommendation before it becomes authoritative.

## Rules

- <Read-only data, other people's folders, collaborators' branches.>
- <Where outputs go; what must never be overwritten.>

## Traps and interpretation caveats

- <Traps that already caused wrong results: symptom, cause, fix.>
- <What the data can and cannot show: assay limits, model outputs vs measurements, references that are not ground truth.>

## Hosts and compute

- <Where interactive work runs, where heavy jobs run, how to reach the cluster.>
