---
name: research-workflow
description: How a research task is scoped, run, recorded and handed over so that the user and the next agent can follow it, even if the session dies halfway. Use at the start of any task that is more than a quick answer (an analysis, a pipeline change, a model run, a data or literature investigation), when resuming someone else's work, when finishing or pausing, when planning a compute run (pre-registration), when several runs or agents could write to the same place, and when delegating to subagents or to another coding agent (Claude Haiku/Sonnet/Opus, OpenAI Codex models). Covers scope, PLAN.md, PROGRESS.md, HANDOVER.md, the project handover index, run locks and briefs for other agents.
---

# Research workflow

Four habits make a task cheap, safe and easy to pick up:

| Step | File | Purpose |
|---|---|---|
| Scope the task | top of `PROGRESS.md` | the question, what is in and out of scope, when to stop |
| Plan compute | `PLAN.md` | pre-registration before any run that costs real compute |
| Record as you go | `PROGRESS.md` | live state: done, running, blocked, next |
| Hand over | `HANDOVER.md` | everything the next agent needs, nothing else |

They live in one folder per task: `<project>/handover/<YYYY-MM-DD>_<short-slug>/`, with one row per task in
`<project>/handover/INDEX.md`. Templates are in `${CLAUDE_PLUGIN_ROOT}/skills/research-workflow/templates/`; fill them in and delete sections that do not apply.
A project's own instructions (`AGENTS.md`, or a `CLAUDE.md`) win where they say something different. In a repo that
follows quadbio's `analysis-workflow`, the task directory `analysis/<topic>/<name>_vN/` is the task folder: keep
`PROGRESS.md`, `PLAN.md` and `HANDOVER.md` there and skip `handover/INDEX.md`.

## 1. Start: orient and scope

1. **Orient, briefly.** Read the project's instruction file, `handover/INDEX.md`, and the latest handover on the same
   topic. Read the user's project or lab map if their global instructions name one. Nothing else yet.
2. **Check that nobody else owns the work:** live agent sessions, INDEX rows marked `running`, running jobs,
   recent modification times in the folders you will touch. If someone does, message them instead of starting a copy.
3. **Scope before exploring.** Write at the top of `PROGRESS.md`:
   - the question, in one or two sentences, and what a finished answer looks like (checks that can be verified);
   - **in scope:** the folders, files and data you expect to need; **out of scope:** what you will not touch or read;
   - an **exploration budget** (e.g. "≤ 15 file reads before a first answer") and a **stop rule** (stop exploring
     once the question can be answered; do not read "for context").

   If the request has two readings, or the scope is unclear, ask now: one question costs less than a wrong
   exploration. Explore cheaply: grep and read slices, summaries instead of full output, subagents only for bulky
   reads with small answers.
4. Create the task folder, `PROGRESS.md` from the template, and the INDEX row with status `running`.

## 2. Plan compute (PLAN.md)

Required before training, sweeps, large re-scoring, or anything beyond a smoke test. Template: `templates/PLAN.md`.
Most wasted compute comes from many-arm sweeps run before the evaluation is trustworthy, oversized resource
requests and jobs that fail for known reasons. So:

1. **In silico first:** re-score existing outputs, ablate at inference, use external truth, simulate.
2. **Pre-register** question, decision metric, expected effect, decision rule and the action for each outcome. If no
   outcome changes what happens next, do not run.
3. **Effect vs noise:** effects below the known seed or replicate range are not run, or get ≥ 3 replicates from the start.
4. **One factor at a time;** single-factor controls go in the first submission.
5. **Validate a new scoring path** on a case with a known answer first.
6. **Smallest scale that answers** (subset pilot), then scale up only the arms that survive.
7. **Smoke-test and size** resources from measured use (peak memory × 1.3, realistic time). State expected cost.
8. **Kill and fix:** stop arms clearly below control early; a job type that fails twice gets a reproducer first.

The user approves a plan that needs anything on their ask-first list (their global instructions), or when the
project says plans need approval. Otherwise proceed and note it in PROGRESS.

## 3. While working (PROGRESS.md)

Update the status block and append a dated entry:
- at each milestone (a step done, a result in, a decision made);
- before and after each job submission (job IDs, where logs go);
- when blocked or waiting on the user (say exactly what you need);
- before anything that may end the session or compact the context;
- at least every hour of active work.

One to five lines per entry: paths, numbers and job IDs, not narrative. Results are observed facts with their file
path; interpretations are marked as such. Never rewrite earlier entries; append a correction that points to them.
If the scope changes, say so in an entry and update the scope block.

## 4. Finish or pause (HANDOVER.md)

Write `HANDOVER.md` when the task is done, when you stop for any reason, or when you hand part of it on. Then:
- set the INDEX row to `done`, `paused` or `blocked`, with one line on the outcome;
- update the project's living documents if the result changes them (README, results overview, known traps);
- record the cost of jobs you ran (requested vs used memory and time, GPU type);
- list every file you created outside the task folder, marked keep or delete; delete scratch files nothing needs.

Test the handover: could an agent with no memory of this session resume from it alone? If not, add what is missing.

## 5. Delegating to subagents and other agents

The top agent owns the result. Delegate to save cost or to get an independent view, never to avoid checking.
Model choice, briefs and the cross-check pattern: `references/delegation.md`. In short: cheap models read and
sweep, workhorse models implement from a written spec, the frontier model designs, interprets and reviews.
Every delegated task gets a brief (`templates/BRIEF.md`) with its scope and its own output folder. Read what
comes back and check at least one number or claim against the source before using it.

## 6. Parallel runs, drivers and agents: never two writers in one folder

The typical accident: an item is started by hand "to save time" while a driver loop still has it on its list.
When the driver reaches it, a second run writes into the same folder; the folder then mixes two runs and the
step has to be redone. Rules:

1. **One writer per output folder.** Every run claims its folder with `${CLAUDE_PLUGIN_ROOT}/skills/research-workflow/scripts/runlock.py`
   (`runlock.py run <outdir> -- <cmd>`, or `with claimed(outdir):` in Python). A second claim on a live folder fails
   with exit 3. Drivers claim per step, not once for the whole loop. Copy the script next to a pipeline's code
   when jobs on a cluster need it.
2. **Check before starting anything:** `runlock.py status <outdir>`, the job queue (`squeue -u $USER` on SLURM) or
   running processes (`ps -u $USER -o pid,etime,args`), INDEX rows marked `running`, newest mtimes in the folder.
3. **Take work out before doing it by hand:** remove the item from the driver's list (or stop the driver) first,
   and note it in PROGRESS. Never run the same item in two places.
4. **Finished means finished:** a completed step leaves `.RUN_DONE`; drivers skip it, and reruns go to a new folder
   (`<step>/<run_id>/`) unless the user decides to overwrite.
5. **Parallel subagents and jobs get disjoint output folders,** named in their briefs. Run names are never reused.
6. **If a collision happens anyway:** stop the duplicate, do not try to sort out which file came from which run,
   record it, and redo the step cleanly into a new folder.

## 7. Evidence rules for everything written here

- Observed result (with exact path), literature (with primary source), hypothesis: kept apart and labelled.
- Name the unit of replication and the n behind every comparison.
- Every filter or exclusion is listed with counts; filters that remove data need the user's OK.
- Unchecked items are written as such. "Not verified" is a valid and useful line.
