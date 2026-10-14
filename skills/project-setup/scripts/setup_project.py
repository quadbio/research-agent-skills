#!/usr/bin/env python3
"""Survey a project folder and create the agent scaffolding that is missing.

    setup_project.py <project_dir> [--name NAME] [--code-dir DIR] [--go]

Without --go it only reports (dry run). With --go it creates, never overwrites or deletes:
  AGENTS.md            from templates/AGENTS.md, if missing and no CLAUDE.md holds instructions to convert
  CLAUDE.md            from templates/CLAUDE.md (only `@AGENTS.md`), if missing, AGENTS.md exists or is created,
                       and no .claude/CLAUDE.md already loads it
  ENVIRONMENTS.md      template + a survey draft (survey_envs.py on the code folder), if missing
  CODE_MAP.md          template + a survey draft (survey_code.py on the code folder), if missing
  handover/INDEX.md    from templates/INDEX.md, if missing
It also reports a CLAUDE.md that holds instructions instead of importing AGENTS.md or whose import resolves to the
wrong file, a lowercase agents.md, the files
that mention them, git worktrees, and whether .claude/worktrees/ is ignored. The drafts are a starting point: the
agent fills the gaps from the project's own documents.
"""
import argparse
import datetime as dt
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import survey_code  # noqa: E402
import survey_envs  # noqa: E402

TEMPLATES = os.path.join(HERE, "..", "templates")
SKIP_DIRS = {".git", "node_modules", ".snakemake", "__pycache__", ".pixi", "results", "data"}
DRAFT_HEADER = "\n\n---\n\n## Survey draft (generated; keep what is correct, then delete this section)\n\n"


def render(template, name):
    with open(os.path.join(TEMPLATES, template)) as fh:
        return fh.read().replace("{name}", name).replace("{date}", dt.date.today().isoformat())


def git(path, *args):
    try:
        out = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def exists_exact(root, rel):
    """rel exists under root with exactly this case (macOS file systems ignore case: AGENTS.md is not agents.md)."""
    d, name = os.path.split(os.path.join(root, rel))
    try:
        return name in os.listdir(d)
    except OSError:
        return False


def guess_code_dir(root):
    """The folder that holds the code: code/ when it exists, else the project root."""
    code = os.path.join(root, "code")
    return code if os.path.isdir(code) else root


def references_to(root, filename, max_depth=4, limit=30):
    """Text files under root that mention filename (skips data/results/.git); stops after `limit` hits."""
    hits, pat = [], re.compile(re.escape(filename))
    base = root.rstrip(os.sep).count(os.sep)
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith("_archive")]
        if d.count(os.sep) - base >= max_depth:
            dirs[:] = []
        for f in files:
            if not f.endswith((".md", ".py", ".R", ".sh", ".smk", ".yaml", ".yml", ".txt")) or f == filename:
                continue
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) < 2_000_000 and pat.search(open(p, errors="ignore").read()):
                    hits.append(os.path.relpath(p, root))
            except OSError:
                continue
            if len(hits) >= limit:
                return hits
    return hits


def env_draft(code_dir, name):
    manifests, refs, imports = survey_envs.scan_project(code_dir, 5)
    return render("ENVIRONMENTS.md", name) + DRAFT_HEADER + survey_envs.render(code_dir, manifests, refs, imports) + "\n"


def code_draft(code_dir, name):
    return render("CODE_MAP.md", name) + DRAFT_HEADER + survey_code.render(code_dir, *survey_code.survey(code_dir, 5)) + "\n"


CLAUDE_FILES = ("CLAUDE.md", os.path.join(".claude", "CLAUDE.md"))
LOADS_AGENTS = ("import", "import+", "symlink")      # kinds through which Claude Code loads the project's AGENTS.md


def import_line(rel):
    """The import that loads the project's AGENTS.md from rel: imports resolve relative to the importing file, so
    CLAUDE.md needs @AGENTS.md and .claude/CLAUDE.md needs @../AGENTS.md."""
    return "@" + os.path.relpath("AGENTS.md", os.path.dirname(rel) or ".")


def claude_md_kind(root, rel):
    """What rel does for the project's AGENTS.md:
    None            absent
    "symlink"       a symlink to AGENTS.md (Claude reads the same file; never write through it)
    "import"        only an import of AGENTS.md, plus headings and blank lines
    "import+"       imports AGENTS.md and also holds instructions
    "wrong-import"  imports an AGENTS.md path that doesn't exist (e.g. @AGENTS.md inside .claude/)
    "instructions"  holds instructions and doesn't import AGENTS.md"""
    p = os.path.join(root, rel)
    if not exists_exact(root, rel):
        return None
    agents = os.path.realpath(os.path.join(root, "AGENTS.md"))
    if os.path.islink(p) and os.path.realpath(p) == agents:
        return "symlink"
    try:
        with open(p, errors="ignore") as fh:
            lines = [x.strip() for x in fh if x.strip() and not x.lstrip().startswith("#")]
    except OSError:                   # e.g. a dangling symlink
        return "instructions"
    imports, wrong, other = False, False, False
    for line in lines:
        target = line[1:].strip()
        if line.startswith("@") and os.path.realpath(os.path.join(os.path.dirname(p), target)) == agents:
            imports = True
        elif line.startswith("@") and os.path.basename(target) == "AGENTS.md" and \
                not os.path.exists(os.path.join(os.path.dirname(p), target)):
            wrong = True              # a path slip (missing file); an existing one brings in rules to migrate
        else:
            other = True
    if imports:                       # a second AGENTS.md import elsewhere is competing instructions too
        return "import+" if other or wrong else "import"
    return "wrong-import" if wrong and not other else "instructions"


def symlink_note(root, rel):
    """' (symlink to X)' for a symlinked file, else ''."""
    p = os.path.join(root, rel)
    return f" (symlink to {os.readlink(p)})" if os.path.islink(p) else ""


def plan_files(root, name, code_dir):
    """[(relative path, producer)] for every scaffolding file that is missing."""
    def exists(rel):
        return exists_exact(root, rel)
    plan = []
    kinds = [claude_md_kind(root, f) for f in CLAUDE_FILES]
    if not exists("AGENTS.md") and {"instructions", "import+"} & set(kinds):
        print("skip:  AGENTS.md template, because a CLAUDE.md holds the instructions: move them into AGENTS.md "
              "instead (SKILL.md step 5)")
    elif not exists("AGENTS.md") and exists("agents.md"):
        print("skip:  AGENTS.md template, because agents.md exists: rename it to AGENTS.md instead (SKILL.md step 5)")
    elif not exists("AGENTS.md"):
        plan.append(("AGENTS.md", lambda: render("AGENTS.md", name)))
    agents_md = exists("AGENTS.md") or any(rel == "AGENTS.md" for rel, _ in plan)
    if agents_md and kinds[0] is None and kinds[1] not in LOADS_AGENTS:
        plan.append(("CLAUDE.md", lambda: render("CLAUDE.md", name)))
    if not exists("ENVIRONMENTS.md"):
        plan.append(("ENVIRONMENTS.md", lambda: env_draft(code_dir, name)))
    if not exists("CODE_MAP.md"):
        plan.append(("CODE_MAP.md", lambda: code_draft(code_dir, name)))
    if not exists(os.path.join("handover", "INDEX.md")):
        plan.append((os.path.join("handover", "INDEX.md"), lambda: render("INDEX.md", name)))
    return plan


def write_new(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "x") as fh:          # "x": never overwrite
        fh.write(text)


def report(root, code_dir, groot):
    where = "repo root" if groot == root else (f"inside repo {groot}" if groot else "not a git repo")
    print(f"git: {where}; code folder: {os.path.relpath(code_dir, root)}")
    for f in ("README.md", "AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md", "agents.md",
              "ENVIRONMENTS.md", "CODE_MAP.md", "handover/INDEX.md"):
        kind = claude_md_kind(root, f) if f in CLAUDE_FILES else None
        note = {"symlink": " (symlink to AGENTS.md)", "import": " (imports AGENTS.md)",
                "import+": " (imports AGENTS.md, and holds instructions)",
                "wrong-import": " (imports an AGENTS.md that isn't the project's)",
                "instructions": " (holds instructions, no AGENTS.md import)"}.get(kind, "")
        if kind in ("import", "import+", "wrong-import", "instructions"):
            note += symlink_note(root, f)
        print(f"  {'found ' if exists_exact(root, f) else 'absent'}  {f}{note}")
    wt = git(code_dir, "worktree", "list")
    if wt and len(wt.splitlines()) > 1:
        print(f"worktrees of {os.path.relpath(code_dir, root)}:")
        for line in wt.splitlines():
            print(f"  {line}")


def uses_analysis_workflow(root):
    p = os.path.join(root, ".claude", "settings.json")
    return os.path.exists(p) and "analysis-workflow@quadbio" in open(p, errors="ignore").read()


def report_conversions(root, groot):
    for f in CLAUDE_FILES:
        if claude_md_kind(root, f) == "wrong-import":
            link = f"; it is a symlink to {os.readlink(os.path.join(root, f))}: remove the link first, don't write " \
                   "through it" if os.path.islink(os.path.join(root, f)) else ""
            print(f"\nfix: {f} imports an AGENTS.md path that doesn't exist: imports resolve relative to the "
                  f"importing file, so use {import_line(f)}{link} (SKILL.md step 5)")
    to_convert = [f for f in CLAUDE_FILES if claude_md_kind(root, f) in ("instructions", "import+")]
    if exists_exact(root, "agents.md"):
        to_convert.append("agents.md")
    for legacy in to_convert:
        refs = references_to(root, os.path.basename(legacy))
        what = "rename it to AGENTS.md" if legacy == "agents.md" else \
            f"move its instructions into AGENTS.md and leave only {import_line(legacy)}"
        if os.path.islink(os.path.join(root, legacy)):
            what += f"; it is a symlink to {os.readlink(os.path.join(root, legacy))}: remove the link first, " \
                    "don't write through it"
        print(f"\nconvert: {legacy}: {what} (SKILL.md step 5); files that mention it ({len(refs)}):")
        for r in refs:
            print(f"  {r}")
    if groot:
        ignored = subprocess.run(["git", "-C", groot, "check-ignore", "-q", ".claude/worktrees/x"]).returncode == 0
        if not ignored:
            print("\n.gitignore: add .claude/worktrees/ (where claude --worktree puts task worktrees)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir")
    ap.add_argument("--name")
    ap.add_argument("--code-dir")
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.project_dir)
    if not os.path.isdir(root):
        sys.exit(f"not a folder: {root}")
    name = a.name or os.path.basename(root)
    code_dir = os.path.abspath(a.code_dir) if a.code_dir else guess_code_dir(root)
    groot = git(root, "rev-parse", "--show-toplevel")
    print(f"== {root} ({'writing' if a.go else 'dry run'})")
    if uses_analysis_workflow(root):
        print("note: this repo enables analysis-workflow@quadbio: it keeps task records in task directories, so "
              "don't add handover/ (SKILL.md, before step 1); create only CODE_MAP.md / ENVIRONMENTS.md if the user wants them")
    report(root, code_dir, groot)
    plan = plan_files(root, name, code_dir)
    for rel, produce in plan:
        print(f"{'create' if a.go else 'would create'}: {rel}")
        if a.go:
            write_new(root, rel, produce())
    if not plan:
        print("nothing to create")
    report_conversions(root, groot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
