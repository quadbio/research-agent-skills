#!/usr/bin/env python3
"""Survey a project folder and create the agent scaffolding that is missing.

    setup_project.py <project_dir> [--name NAME] [--code-dir DIR] [--codex-marker] [--go]

Without --go it only reports (dry run). With --go it creates, never overwrites or deletes:
  CLAUDE.md            from templates/CLAUDE.md, if the folder has neither CLAUDE.md nor AGENTS.md
  ENVIRONMENTS.md      template + a survey draft (survey_envs.py on the code folder), if missing
  CODE_MAP.md          template + a survey draft (survey_code.py on the code folder), if missing
  handover/INDEX.md    from templates/INDEX.md, if missing
  .agent_project_root  only with --codex-marker (Codex project_root_markers), added to .git/info/exclude
It also reports AGENTS.md / agents.md files to convert, the files that mention them, git worktrees, and whether
Codex reads CLAUDE.md. The drafts are a starting point: the agent fills the gaps from the project's own documents.
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


def codex_reads_claude_md():
    cfg = os.path.expanduser("~/.codex/config.toml")
    if not os.path.exists(cfg):
        return None
    m = re.search(r"^project_doc_fallback_filenames\s*=\s*\[(.*?)\]", open(cfg).read(), re.M)
    return bool(m and "CLAUDE.md" in m.group(1))


def env_draft(code_dir, name):
    manifests, refs, imports = survey_envs.scan_project(code_dir, 5)
    return render("ENVIRONMENTS.md", name) + DRAFT_HEADER + survey_envs.render(code_dir, manifests, refs, imports) + "\n"


def code_draft(code_dir, name):
    return render("CODE_MAP.md", name) + DRAFT_HEADER + survey_code.render(code_dir, *survey_code.survey(code_dir, 5)) + "\n"


def plan_files(root, name, code_dir, codex_marker):
    """[(relative path, producer)] for every scaffolding file that is missing."""
    def exists(rel):
        return os.path.exists(os.path.join(root, rel))
    plan = []
    if exists("AGENTS.md") and not exists("CLAUDE.md"):
        print("skip:  CLAUDE.md template, because AGENTS.md exists: rename it to CLAUDE.md instead (SKILL.md step 5)")
    elif not exists("CLAUDE.md"):
        plan.append(("CLAUDE.md", lambda: render("CLAUDE.md", name)))
    if not exists("ENVIRONMENTS.md"):
        plan.append(("ENVIRONMENTS.md", lambda: env_draft(code_dir, name)))
    if not exists("CODE_MAP.md"):
        plan.append(("CODE_MAP.md", lambda: code_draft(code_dir, name)))
    if not exists(os.path.join("handover", "INDEX.md")):
        plan.append((os.path.join("handover", "INDEX.md"), lambda: render("INDEX.md", name)))
    if codex_marker and not exists(".agent_project_root"):
        plan.append((".agent_project_root", lambda: ""))
    return plan


def write_new(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "x") as fh:          # "x": never overwrite
        fh.write(text)


def exclude_marker(root, go):
    excl = os.path.join(root, ".git", "info", "exclude")
    if os.path.exists(excl) and ".agent_project_root" in open(excl).read().split():
        return
    print(f"{'add' if go else 'would add'} .agent_project_root to .git/info/exclude")
    if go:
        os.makedirs(os.path.dirname(excl), exist_ok=True)
        with open(excl, "a") as fh:
            fh.write(".agent_project_root\n")


def report(root, code_dir, groot):
    where = "repo root" if groot == root else (f"inside repo {groot}" if groot else "not a git repo")
    print(f"git: {where}; code folder: {os.path.relpath(code_dir, root)}")
    for f in ("README.md", "CLAUDE.md", "AGENTS.md", "agents.md", "ENVIRONMENTS.md", "CODE_MAP.md", "handover/INDEX.md"):
        print(f"  {'found ' if os.path.exists(os.path.join(root, f)) else 'absent'}  {f}")
    wt = git(code_dir, "worktree", "list")
    if wt and len(wt.splitlines()) > 1:
        print(f"worktrees of {os.path.relpath(code_dir, root)}:")
        for line in wt.splitlines():
            print(f"  {line}")


def uses_analysis_workflow(root):
    p = os.path.join(root, ".claude", "settings.json")
    return os.path.exists(p) and "analysis-workflow@quadbio" in open(p, errors="ignore").read()


def report_legacy(root):
    for legacy in ("AGENTS.md", "agents.md"):
        if os.path.exists(os.path.join(root, legacy)):
            refs = references_to(root, legacy)
            print(f"\nconvert: {legacy} -> CLAUDE.md (SKILL.md step 5); files that mention it ({len(refs)}):")
            for r in refs:
                print(f"  {r}")
    c = codex_reads_claude_md()
    print("\ncodex: " + {True: "reads CLAUDE.md (project_doc_fallback_filenames)",
                         False: "does NOT read CLAUDE.md: add project_doc_fallback_filenames = [\"CLAUDE.md\"] to ~/.codex/config.toml",
                         None: "no ~/.codex/config.toml on this machine"}[c])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir")
    ap.add_argument("--name")
    ap.add_argument("--code-dir")
    ap.add_argument("--codex-marker", action="store_true")
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
        print("note: this repo enables analysis-workflow@quadbio: keep its AGENTS.md, task directories and "
              "worktrees (SKILL.md, before step 1); create only CODE_MAP.md / ENVIRONMENTS.md if the user wants them")
    report(root, code_dir, groot)
    plan = plan_files(root, name, code_dir, a.codex_marker)
    for rel, produce in plan:
        print(f"{'create' if a.go else 'would create'}: {rel}")
        if a.go:
            write_new(root, rel, produce())
    if a.codex_marker and groot == root:
        exclude_marker(root, a.go)
    if not plan:
        print("nothing to create")
    report_legacy(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
