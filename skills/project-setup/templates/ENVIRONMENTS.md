# Environments: {name}

The only source for which environment to use for what. New environments use pixi (`pixi.toml` + `pixi.lock`,
committed); existing conda/mamba environments stay listed here until replaced. Written {date}; check versions with the survey script or
`<prefix>/bin/python -m pip show <package>` before relying on them.

| Environment | Location / manifest | Used for | Run with |
|---|---|---|---|
| <name> | `<prefix or pixi.toml>` | <analyses, steps> | `<command>` |

## Details per environment

<For each: main packages with versions, what it is for and not for, how to recreate it (manifest or lockfile),
known problems. The survey draft below lists what the code uses; keep what is correct, then delete the draft.>
