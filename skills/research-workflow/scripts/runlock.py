#!/usr/bin/env python3
"""Run locks: one writer per output folder, so two runs can never write into the same place.

Every pipeline step, driver, job or agent that writes into an output folder claims it first:

  runlock.py run <outdir> [--label TEXT] -- <command ...>   claim, run, release (exit code of the command)
  runlock.py acquire <outdir> [--label TEXT]                 claim (exit 3 if held by a live run)
  runlock.py release <outdir>                                release a claim you hold
  runlock.py status <path>                                   show the claim on <path> or any folder above it
  runlock.py done <outdir> [--label TEXT]                    write .RUN_DONE (the step finished cleanly)

Python:   from runlock import claimed
          with claimed(outdir, label="step 3, sample A"):  ...write...

The claim is `<outdir>/.RUNLOCK`, created atomically (O_EXCL), holding host, pid, SLURM job id, user,
agent session and start time. A claim is live while its process exists (same host), or its SLURM job is
still in the queue. A stale claim (dead process, finished job) is taken over and the takeover logged in the
new lock. `.RUN_DONE` marks a finished run: drivers should skip steps whose folder has it, and a new run
into a folder with `.RUN_DONE` must use a new folder or be started with --force when the user decides to overwrite.

An agent PreToolUse hook can import holder() from this module to refuse commands that write into a claimed folder.
"""
import argparse
import contextlib
import datetime as dt
import json
import os
import socket
import subprocess
import sys

LOCK = ".RUNLOCK"
DONE = ".RUN_DONE"


def _me(label, pid=None):
    return {"host": socket.gethostname().split(".")[0], "pid": pid or os.getpid(),
            "slurm_job": os.environ.get("SLURM_JOB_ID", ""), "user": os.environ.get("USER", ""),
            "session": os.environ.get("CLAUDE_SESSION_NAME") or os.environ.get("CODEX_SESSION_ID", ""),
            "label": label or "", "started": dt.datetime.now().isoformat(timespec="seconds")}


def read(outdir):
    try:
        with open(os.path.join(outdir, LOCK)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def alive(info):
    """True / False when liveness can be decided here, None when it cannot (other host, no SLURM id)."""
    if not info:
        return False
    if info.get("slurm_job"):
        try:
            out = subprocess.run(["squeue", "-h", "-j", info["slurm_job"], "-o", "%T"], capture_output=True,
                                 text=True, timeout=20).stdout.strip()
            return bool(out)
        except (OSError, subprocess.TimeoutExpired):
            pass
    if info.get("host") == socket.gethostname().split(".")[0] and info.get("pid"):
        try:
            os.kill(int(info["pid"]), 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
    return None


def holder(path):
    """Nearest claim at or above `path`: (folder, info, alive) or None."""
    p = os.path.abspath(path)
    if not os.path.isdir(p):
        p = os.path.dirname(p)
    while True:
        info = read(p)
        if info:
            return p, info, alive(info)
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def describe(folder, info, live):
    state = {True: "LIVE", False: "stale", None: "unknown (other host)"}[live]
    return (f"{folder} is claimed ({state}) by {info.get('label') or 'a run'}: host {info.get('host')}, "
            f"pid {info.get('pid')}, SLURM {info.get('slurm_job') or '-'}, session {info.get('session') or '-'}, "
            f"since {info.get('started')}")


def acquire(outdir, label=None, force=False, pid=None):
    os.makedirs(outdir, exist_ok=True)
    if os.path.exists(os.path.join(outdir, DONE)) and not force:
        raise SystemExit(f"runlock: {outdir} holds a finished run ({DONE}); write to a new folder, "
                         "or rerun with --force only if the user decided to overwrite it")
    me = _me(label, pid)
    for _ in range(2):
        try:
            fd = os.open(os.path.join(outdir, LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, "w") as fh:
                json.dump(me, fh, indent=1)
            return me
        except FileExistsError:
            info = read(outdir)
            live = alive(info)
            if live is False:
                me["took_over_stale"] = info
                os.replace(os.path.join(outdir, LOCK), os.path.join(outdir, LOCK + ".stale"))
                continue
            print("runlock: " + describe(outdir, info or {}, live), file=sys.stderr)
            print("runlock: refusing to start a second run into the same folder. Wait for it, kill it on "
                  "purpose, or write to a new folder.", file=sys.stderr)
            raise SystemExit(3)
    raise SystemExit(3)


def release(outdir):
    with contextlib.suppress(FileNotFoundError):
        os.remove(os.path.join(outdir, LOCK))


@contextlib.contextmanager
def claimed(outdir, label=None, force=False, mark_done=True):
    acquire(outdir, label, force)
    try:
        yield outdir
        if mark_done:
            with open(os.path.join(outdir, DONE), "w") as fh:
                json.dump({**_me(label), "finished": dt.datetime.now().isoformat(timespec="seconds")}, fh, indent=1)
    finally:
        release(outdir)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("action", choices=["run", "acquire", "release", "status", "done"])
    p.add_argument("outdir")
    p.add_argument("--label")
    p.add_argument("--force", action="store_true")
    argv = sys.argv[1:]
    cmd = argv[argv.index("--") + 1:] if "--" in argv else []
    a = p.parse_args(argv[:argv.index("--")] if "--" in argv else argv)
    if a.action == "status":
        h = holder(a.outdir)
        print(describe(*h) if h else f"{a.outdir}: no claim")
        if os.path.exists(os.path.join(a.outdir, DONE)):
            print(f"{a.outdir}: finished run marker present ({DONE})")
        return 0
    if a.action == "acquire":
        acquire(a.outdir, a.label, a.force, pid=os.getppid())   # the calling shell holds it
        return 0
    if a.action == "release":
        release(a.outdir)
        return 0
    if a.action == "done":
        with open(os.path.join(a.outdir, DONE), "w") as fh:
            json.dump({**_me(a.label), "finished": dt.datetime.now().isoformat(timespec="seconds")}, fh, indent=1)
        return 0
    if not cmd:
        p.error("run needs a command after --")
    acquire(a.outdir, a.label or " ".join(cmd)[:120], a.force)
    try:
        rc = subprocess.call(cmd)
        if rc == 0:
            with open(os.path.join(a.outdir, DONE), "w") as fh:
                json.dump({**_me(a.label), "finished": dt.datetime.now().isoformat(timespec="seconds"),
                           "cmd": cmd}, fh, indent=1)
        return rc
    finally:
        release(a.outdir)


if __name__ == "__main__":
    sys.exit(main())
