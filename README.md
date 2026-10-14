# research-agent-skills

A Claude Code plugin with three skills for research projects where coding agents write code, run compute and pick
up each other's work. They hold habits that apply to any project and language: how to write and change research
code, how a task is scoped, recorded and handed over, and how a project is set up so every agent finds its rules.
Nothing in them is specific to a dataset, a cluster or one person.

| Part | What it does |
| --- | --- |
| `skills/analysis-code/` | Writing and changing research code: think before coding, one owner per operation, small pure functions, correctness traps that silently give wrong results (drops in joins, pooled metrics, ignored seeds), verify before reporting. |
| `skills/research-workflow/` | Running a task so the next agent can resume it: scope and stop rule, a pre-registered `PLAN.md` before compute, `PROGRESS.md` while working, `HANDOVER.md` at the end, briefs for subagents and Codex, and `runlock.py` (one writer per output folder). |
| `skills/project-setup/` | Setting up or repairing a project: one `AGENTS.md` for Claude Code and Codex, with a `CLAUDE.md` that imports it, `CODE_MAP.md` and `ENVIRONMENTS.md` drafted by survey scripts, a `handover/` index, one worktree per task, pixi for new environments. |

The skills are loaded on demand; there are no hooks. They work alongside the other
[quadbio plugins](https://github.com/quadbio/claude-plugins): in repos that follow `analysis-workflow`, its
conventions (task directories, `AGENTS.md`, working objects) win, and these skills say so. Cluster specifics belong
to `euler-hpc`, figures to `sci-figures`.

## Use

Ask in plain words; the skill descriptions decide when each loads.

- "Add a function that …", "refactor this", "review this script": `analysis-code`.
- "Start a task on …", "plan the sweep", "resume the work from yesterday", "hand this over": `research-workflow`.
- "Set up this project for agents", "we have an AGENTS.md and a CLAUDE.md, clean that up": `project-setup`.

`runlock.py` also works on its own, e.g. in a job script:

```bash
python3 runlock.py run <outdir> -- <command>   # claim the folder, run, write .RUN_DONE, release
python3 runlock.py status <outdir>             # who holds it
```

## Install

Once per machine, from the [quadbio marketplace](https://github.com/quadbio/claude-plugins).

## Develop

```bash
claude plugin validate .
claude --plugin-dir .        # try the skills from this checkout
python3 skills/project-setup/scripts/setup_project.py <some project>   # dry run, writes nothing
```

## Release

Bump `version` in `.claude-plugin/plugin.json` and merge: the marketplace follows `main`, and users update when the
version changes.

## License

MIT
