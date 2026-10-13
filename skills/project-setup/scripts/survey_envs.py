#!/usr/bin/env python3
"""Draft an ENVIRONMENTS.md section: which environments a project uses, what is in them, who uses them.

    survey_envs.py <project_dir> [--max-depth 5]

Finds (1) environment manifests in the project (pixi.toml, environment.yml, requirements*.txt, pyproject.toml,
renv.lock), and (2) environment prefixes the code names (".../envs/<name>/...", conda/mamba activate or run -n <name>).
For each prefix that exists, reads the installed packages from conda-meta/*.json and *.dist-info folders (nothing
is executed) and reports the main ones: those the project imports, plus common scientific packages. Prints
Markdown to stdout; the agent fills in "Used for" and checks the rest.
"""
import argparse
import glob
import json
import os
import re
import sys

SKIP_DIRS = {'.git', '.ipynb_checkpoints', '.pixi', '.snakemake', '.tmux_runtime', '__pycache__', 'data', 'log', 'logs', 'node_modules', 'output', 'outputs', 'results', 'scratch', 'slurm_logs', 'tmp', 'wandb', 'work', 'worktrees'}
CODE_EXT = (".py", ".R", ".r", ".sh", ".smk", ".ipynb", ".yaml", ".yml", ".toml", ".cfg", ".json", ".md")
MANIFESTS = ("pixi.toml", "environment.yml", "environment.yaml", "renv.lock", "pyproject.toml")
KEY_PACKAGES = {"python", "r-base", "numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "matplotlib", "seaborn",
                "anndata", "scanpy", "mudata", "muon", "spatialdata", "squidpy", "scvi-tools", "pytorch", "torch",
                "pytorch-lightning", "lightning", "jax", "tensorflow", "keras", "pycistopic", "scenicplus", "crested",
                "chrombpnet", "snapatac2", "pysam", "pybigwig", "pyranges", "bioconductor-deseq2", "r-seurat",
                "snakemake", "nextflow", "jupyterlab", "cellrank", "harmonypy", "ott-jax", "hydra-core", "wandb"}
IMPORT_TO_DIST = {"sklearn": "scikit-learn", "scvi": "scvi-tools", "yaml": "pyyaml", "torch": "pytorch",
                  "pyBigWig": "pybigwig", "lightning": "lightning", "ott": "ott-jax", "hydra": "hydra-core",
                  "Bio": "biopython", "cv2": "opencv", "skimage": "scikit-image", "snapatac2": "snapatac2"}
ENV_PATH_RE = re.compile(r"(/(?:[\w.+-]{1,80}/){1,15}envs/[\w.+-]{1,80})")   # bounded: no backtracking on long strings
ENV_NAME_RE = re.compile(r"""(?:conda|mamba|micromamba)\s+(?:activate|run\s+-n|run\s+--name)\s+([A-Za-z0-9_.+-]+)""")
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)


def walk_files(root, max_depth):
    """Yield code/text files under root, skipping data, results, VCS and caches."""
    base = root.rstrip(os.sep).count(os.sep)
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(("_archive", "archive"))]
        if d.count(os.sep) - base >= max_depth:
            dirs[:] = []
        for f in files:
            if f.endswith(CODE_EXT) or f.startswith("requirements") or f in MANIFESTS:
                yield os.path.join(d, f)


def read_text(path, limit=3_000_000):
    """File text; for notebooks only the code-cell sources (outputs hold large base64 images)."""
    try:
        if os.path.getsize(path) > (20_000_000 if path.endswith(".ipynb") else limit):
            return ""
        text = open(path, errors="ignore").read()
    except OSError:
        return ""
    if path.endswith(".ipynb"):
        try:
            cells = json.loads(text).get("cells", [])
            return "\n".join("".join(c.get("source", [])) for c in cells if c.get("cell_type") == "code")
        except (ValueError, AttributeError):
            return ""
    return text


def known_prefixes():
    """Conda environment prefixes registered for this user (~/.conda/environments.txt), by env name."""
    reg = os.path.expanduser("~/.conda/environments.txt")
    out = {}
    for line in read_text(reg).splitlines():
        p = line.strip()
        if p:
            out.setdefault(os.path.basename(p), p)
    return out


def scan_project(root, max_depth):
    """One pass over the project: manifests, env references (prefix -> files), imported top-level modules."""
    manifests, refs, imports, names = [], {}, set(), {}
    by_name = known_prefixes()
    for path in walk_files(root, max_depth):
        name = os.path.basename(path)
        rel = os.path.relpath(path, root)
        if name in MANIFESTS or (name.startswith("requirements") and name.endswith(".txt")):
            manifests.append(rel)
        if name == "pixi.toml":   # installed pixi environments live next to their manifest
            for prefix in glob.glob(os.path.join(os.path.dirname(path), ".pixi", "envs", "*")):
                refs.setdefault(prefix, set()).add(rel)
        text = read_text(path)
        if not text:
            continue
        for p in ENV_PATH_RE.findall(text):
            refs.setdefault(p, set()).add(rel)
        for n in ENV_NAME_RE.findall(text):
            names.setdefault(n, set()).add(rel)
        if path.endswith((".py", ".ipynb")):
            imports.update(IMPORT_RE.findall(text))
    resolve_names(names, refs, by_name)
    return sorted(manifests), refs, imports


def resolve_names(names, refs, by_name):
    """Attach env names (conda activate X) to a prefix: the conda registry, else an envs/ folder already seen."""
    roots = {os.path.dirname(p) for p in refs if p.startswith("/")} | {os.path.dirname(p) for p in by_name.values()}
    for n, users in names.items():
        prefix = by_name.get(n) or next((os.path.join(r, n) for r in sorted(roots) if os.path.isdir(os.path.join(r, n))), None)
        refs.setdefault(prefix or f"<conda env '{n}', prefix not found>", set()).update(users)


def installed_packages(prefix):
    """name -> version from conda-meta and pip dist-info; empty if the prefix does not exist."""
    pkgs = {}
    for meta in glob.glob(os.path.join(prefix, "conda-meta", "*.json")):
        try:
            d = json.load(open(meta))
            pkgs[d["name"].lower()] = d.get("version", "?")
        except (OSError, ValueError, KeyError):
            continue
    for info in glob.glob(os.path.join(prefix, "lib", "python3*", "site-packages", "*.dist-info")):
        m = re.match(r"(.+?)-([^-]+)\.dist-info$", os.path.basename(info))
        if m:
            pkgs.setdefault(m.group(1).lower().replace("_", "-"), m.group(2))
    return pkgs


def main_packages(pkgs, imports):
    wanted = set(KEY_PACKAGES) | {IMPORT_TO_DIST.get(i, i).lower().replace("_", "-") for i in imports}
    return {n: v for n, v in sorted(pkgs.items()) if n in wanted}


def run_command(prefix):
    """How to run code in an environment: pixi for pixi environments, the interpreter path otherwise."""
    if "/.pixi/envs/" in prefix:
        project, env = prefix.split("/.pixi/envs/")
        flag = "" if env == "default" else f" -e {env}"
        return f"pixi run{flag} --manifest-path {project}/pixi.toml <cmd>"
    return f"{prefix}/bin/python <script>  (or the project's wrapper)"


def env_label(prefix):
    parts = prefix.rstrip("/").split("/")
    return parts[-1] if "envs" not in parts[-3:-1] or parts[-1] != "default" else "/".join(parts[-4:])


def render(root, manifests, refs, imports):
    lines = [f"<!-- Draft generated by survey_envs.py for {root}. Check every row; fill in 'Used for'. -->", ""]
    lines += ["## Manifests in the project", ""]
    lines += [f"- `{m}`" for m in manifests] or ["- none found"]
    lines += ["", "## Environments the code uses", ""]
    if not refs:
        lines.append("No environment paths or names found in the code.")
    for prefix in sorted(refs, key=lambda p: (-len(refs[p]), p)):
        users = sorted(refs[prefix])
        pkgs = installed_packages(prefix) if prefix.startswith("/") else {}
        main = main_packages(pkgs, imports)
        lines += [f"### {env_label(prefix)}", "",
                  f"- Location: `{prefix}`" + ("" if os.path.isdir(prefix) else " (not found on this host)"),
                  f"- Run with: `{run_command(prefix)}`",
                  "- Used for: <to fill: which analyses or steps>",
                  f"- Used by ({len(users)} files): " + ", ".join(f"`{u}`" for u in users[:4]) + (" …" if len(users) > 4 else ""),
                  "- Main packages: " + (", ".join(f"{n} {v}" for n, v in main.items()) if main else
                                         ("<not readable here>" if not pkgs else "<none of the key packages>")), ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir")
    ap.add_argument("--max-depth", type=int, default=5)
    a = ap.parse_args()
    root = os.path.abspath(a.project_dir)
    manifests, refs, imports = scan_project(root, a.max_depth)
    print(render(root, manifests, refs, imports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
