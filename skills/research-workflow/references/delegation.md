# Delegation: subagents, cheaper models and other coding agents

The top agent (the session the user talks to) scopes, briefs, verifies and reports. Others do bounded pieces.
Delegating never moves responsibility: anything reported to the user has been checked by the top agent.

## Choosing the model

Model names as of 2026-10; replace them when the vendors' line-ups change. Tiers matter more than names.

| Work | Claude | OpenAI Codex | Notes |
|---|---|---|---|
| Read many files or a long log, return a short answer | `haiku` | `gpt-6-luna` | ≤ 10 lines back; the reading stays in the subagent's context |
| Sweep and extract (which scripts read X, list all thresholds) | `haiku` | `gpt-6-luna` | ask for a table written to a file plus a 5-line summary |
| Implement from a written spec, with tests | `sonnet` | `gpt-6.1-sol` | the spec names files, functions, inputs, expected outputs |
| Simple, well-specified edits or plots from a template | `sonnet` | `gpt-5.6-terra` | fine when nothing needs judgement |
| Run pipeline steps and report outcomes | `sonnet` | `gpt-6.1-sol` | the brief names the run-lock folder and the kill rule |
| Design, statistics, interpretation, hard debugging | the top agent (`opus`) | `gpt-6-astra` | keep it in the top agent unless you want a second opinion |
| Independent review of a conclusion or of analysis code | the other vendor | `gpt-6-astra` | see "Cross-check" below |

The user's words set the tier: "cheap", "quick" or "rough" mean one tier down; "careful", "for the paper" or "we
decide on this" mean the frontier tier plus an independent cross-check. A model the user names always wins.
Cheaper models get narrower briefs and closer checks. A subagent costs its own start-up context, so use one only
when the reading is large and the answer small.

## How to delegate

- **Claude Code subagent:** the Agent tool with `model: haiku | sonnet | opus`, a brief from `templates/BRIEF.md`
  and its own output folder `<task folder>/<agent-name>/`. Run it in the background unless your next step needs it.
- **Codex from Claude Code:** the Codex plugin (`codex:rescue`), naming `--model` and `--effort` when a specific
  one is wanted; or the shell: `codex exec -m <model> -C <project> "read <folder>/BRIEF.md and do it"`.
- **Peer sessions:** message them; never resume or copy another session's subagents.
- **Codex as the top agent:** Codex reads `AGENTS.md` (or `CLAUDE.md` when `project_doc_fallback_filenames`
  includes it) and user skills from `~/.agents/skills/`, so the same instructions and skills can serve both.
  Hand work to Claude by writing a BRIEF.md into the task folder and telling the user which session takes it.

## Cross-check between two vendors

Use it when a result will drive a decision or go into a paper, and when the user asks for "careful".
1. Give the reviewer the question, the data paths and the code, but **not your conclusion**, so it cannot anchor on it.
2. Ask for its own answer, the numbers that support it, and what would change its mind.
3. Compare. Where you agree, report both. Where you disagree, find the cause (a different filter, unit or bug)
   before reporting, and record the disagreement in HANDOVER.

## Rules for every delegated task

- One brief, one scope, one output folder, one owner. Parallel agents never share a writable folder.
- Subagents do not submit jobs, push, delete or spawn further agents unless the brief allows it.
- The top agent checks at least one number or claim against the source, and notes in PROGRESS which model did what.
