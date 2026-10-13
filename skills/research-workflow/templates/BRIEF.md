# BRIEF for <agent / model>: <short title>

From: <top agent session>, task folder `<path>`

**Goal.** <One sentence: what you must produce.>

**Context you need.** <Only what is required: the files to read (paths), the facts that matter, the
definitions. The receiving agent has none of this conversation.>

**Inputs.** <paths, read-only>

**Output.** Write only into `<task folder>/<agent-name>/`. Produce: <files, format>. Return to me:
<at most N lines: the answer, the key numbers, the paths of what you wrote>.

**Constraints.**
- Read anything; modify nothing outside your output folder.
- Do not submit jobs, push, delete, or spawn further agents unless this brief says so.
- Do not apply filters or thresholds that are not written here; report candidates instead.
- Say what you could not verify. If the brief is ambiguous, stop and ask rather than guess.

**Budget.** <time / tokens / compute limit>

**Done when.** <checks the result must pass>
