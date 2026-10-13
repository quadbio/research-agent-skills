# PLAN: <task title>

Written before any run. Approved by: <user, date / not needed because ...>

| | |
|---|---|
| Question | <one sentence> |
| Why in silico is not enough | <which existing output, ablation or external dataset was considered, and why it cannot answer> |
| Decision metric | <metric, data split, pipeline that computes it> |
| Known-answer check | <how the scoring path is validated first, or "existing, validated in ..."> |
| Reference / control | <fixed reference; single-factor controls included in the first submission> |
| Factor changed | <exactly one> |
| Expected effect | <size, and the known noise range (seeds / replicates) it is compared with> |
| Replicates | <seeds or biological units, and why that number> |
| Decision rule | <if metric ... then ...; else ...> |
| Action per outcome | <what we do in each case; if all outcomes lead to the same action, do not run> |
| Scale | <pilot size first; what must hold to scale up> |
| Kill rule | <when an arm is stopped early> |
| Expected cost | <arms × seeds; GPU-h; GB·h; sized from the measured use of an earlier run of this job type, or a smoke test> |
| Ask-first items | <A100 / > 24 h / > 64 GB / data-removing filter / none> |
