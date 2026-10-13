---
name: analysis-code
description: How to write and change research code so it stays small, correct and easy to follow - think before coding, simplest solution, surgical changes, one owner per function, functional style with few classes, and verification before reporting. Use before adding a function, script, notebook, plot helper or pipeline step (Python, R, notebooks, Snakemake/Nextflow, SLURM job scripts, deep-learning training code); when refactoring, deduplicating or moving code or results; when writing tests; and when reviewing code written by another agent or a student.
---

# Analysis code

A project's own instruction file adds its path resolver, owners and traps, and wins where it is stricter. In repos
that follow quadbio's `analysis-workflow`, its rules on paths, task directories, working objects and environments
win over §4 and §6 here.

## 1. Think before coding

- State your assumptions. If a request has several readings, name them and ask instead of picking one silently.
  If something is unclear, stop and say what is unclear.
- If a simpler approach exists, say so, and push back when warranted.
- Turn the task into checks before writing code: "fix the bug" = a test that reproduces it, then passes;
  "refactor" = identical outputs before and after; "add X" = a test or known-answer case for X.
- For multi-step work, write a short plan with a check per step.

## 2. Search before writing: one owner per operation

- **Search for the owner** of the operation: `rg -n "<operation>|<plot type>"` over the live tree (skip archives and
  legacy folders). If an owner exists, call it or extend it in place. Write a second implementation only when the
  inputs, coordinate system or estimand really differ, and say so in its docstring.
- **The library is the owner when one exists:** pandas, numpy, scipy, statsmodels, scikit-learn, matplotlib, h5py,
  hashlib, and their equivalents in R. No home-grown multiple-testing correction, z-score, bootstrap or file hashing.
  Wrap a library call only to encode a project contract (a path, a palette, a filter). When replacing your own code
  with a library call, check that the numbers match first. Example trap: `Series.transform(false_discovery_control)`
  without a groupby runs element-wise and silently returns q = p.
- **Duplication:** the second copy of a block is the signal to extract a function into the shared module, not to
  paste it again. Copies of notebooks per sample, species or condition become one parameterised script.

## 3. Shape of the code: small functions, few classes

- **Functions do one thing,** with explicit inputs and outputs and a name that says what they return. Aim for
  functions that fit on a screen; split when a function needs section comments.
- **Prefer pure functions:** data in, data out, no hidden global state. Keep reading, writing and plotting at the
  edges (a thin script or rule), and computation in functions that can be tested without files.
- **Classes only for real state or a real interface** (a model, a dataset that caches, a resource that must be
  closed). Plain data is a dict, `dataclass` or `NamedTuple`; one implementation needs no base class; no
  inheritance hierarchies "for later".
- **Minimum code that solves the problem:** no features, options or configurability nobody asked for, no
  abstraction for a single caller, no error handling for impossible cases. If 200 lines could be 50, write 50.
- **Surgical changes:** touch only what the task needs and match the local style. Mention unrelated dead code or
  problems; do not fix them uninvited. Remove only the imports and helpers your own change made unused.
- Docstrings state the contract (inputs, units, output, side effects), not the history.

## 4. Paths, names and outputs

- Never hardcode a host path. Resolve the project root at runtime (the project's paths module or an environment
  variable) and take tools and environments from config. SLURM `#SBATCH` lines are the one exception.
- Code never writes beside itself. Outputs go to the project's results tree, never into raw-data folders, and
  never to a path derived from the current working directory.
- Category names, colours and orders come from project config; resolve names at read boundaries.
- Moving code or results: repoint every reader in the same change, then delete the old path. No compatibility
  symlinks. Regenerate the project's output manifest if it has one.
- Notebooks: `NN_verb_object.ipynb`; no `Copy1` or `Untitled`; outputs stripped in git (nbstripout).
- Every output folder a run writes is claimed with `${CLAUDE_PLUGIN_ROOT}/skills/research-workflow/scripts/runlock.py` (one writer per folder; see the
  `research-workflow` skill).

## 5. Correctness traps that cause wrong results

- **Silent drops:** report counts for every filter, join and dropna. A join that loses rows is a bug until shown
  otherwise. Never gate accumulation with a per-batch count threshold: rare groups vanish.
- **Division by zero:** guard every `x / array` where the array can hold zeros.
- **Pooled metrics:** report per-group metrics (per species, cell type, donor). A pooled correlation can be inflated
  by between-group differences (Simpson's paradox).
- **Matrices that look raw:** check what a matrix holds (counts, normalised, corrected) before normalising or
  plotting. Name the matrix, transform and filter in every embedding or heatmap.
- **Regex for gene families:** take gene sets (mitochondrial, ribosomal) from config or annotation, not from a
  name prefix; naming differs between species and annotations.
- **Early-stop reads:** do not stop reading after N rows when later filtering removes some; read, filter, then sample.
- **Caches:** key a cache by everything that changes it, and state which parameters invalidate it.
- **Seeds:** check that replicates really differ (a seed can be silently ignored, e.g. when initialising from a checkpoint).

## 6. Jobs and environments

- Validate every runtime input at submission time, not at minute 40 of the job.
- Job logs include the job ID in their name; print host, GPU and `git log -1` at the top of every job.
- GPU code asserts the GPU is available and logs the device; never fall back to CPU silently.
- **New environments use pixi:** `pixi.toml` plus the exact `pixi.lock`, both committed, so the environment can be
  reproduced anywhere with `pixi install`. Existing conda/mamba environments stay usable; replacing one is its own
  task. Run worktrees with the main checkout's environment instead of building one per worktree; keep
  environments and caches out of home and backed-up storage on shared machines. List every environment in the
  project's `ENVIRONMENTS.md` (`project-setup` skill).
- Environments are self-contained: no user site-packages (`PYTHONNOUSERSITE=1`), no packages borrowed from other
  environments, `pip check` and `pip freeze` recorded. Caches go to scratch, never home.

## 7. Look at data and output in small pieces

Everything printed into an agent's context is paid for on every later turn, and a wall of output hides the
number that matters. Compute in a script; let only summaries in.

- **Data:** shape, columns, dtypes and null counts before content, then at most a few rows (`.head()`,
  `.describe()`, `value_counts().head(10)`). Never print a whole table, array or dict of unknown size.
- **Results:** write them to a file in the results tree and report its path plus the few numbers that answer the
  question. Save plots to disk; look at one only when a decision depends on seeing it.
- **AnnData:** open it read-only and print the summary, not the contents:
  `python -c "import anndata as ad; print(ad.read_h5ad('x.h5ad', backed='r'))"`.
- **Notebooks:** read the code cells only; outputs and embedded images can cost tens of thousands of tokens:
  `jupyter nbconvert --to script --stdout nb.ipynb` or
  `jq -r '.cells[] | select(.cell_type=="code") | .source | join("")' nb.ipynb`.
- **Long commands and job logs:** send output to a log, then read the exit code, the tail and the errors:
  `cmd > out.log 2>&1; echo "exit=$?"; tail -n 20 out.log; grep -n -i -m 20 -E "error|traceback|warn" out.log`.
  Use quiet flags where they exist (`pip install -q`, `pytest -q --tb=short`, `git diff --stat` first).

## 8. Verify, then report

- Run the checks from §1 and the project's own checks (config validation, path checks, test suite).
- New metric or scoring path: a known-answer case first (planted signal, a published number, an identity).
- Report what you ran and what it showed. If you could not run something, say so.

## 9. Git

Commit on your own branch, early and small; never commit to the main branch; ask before pushing. No logs, data or
notebook outputs in git. New options keep old defaults, so old configs reproduce old runs.
