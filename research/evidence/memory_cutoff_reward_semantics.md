# Completion labels and state satisfaction in imposed cuts

The source bank is unchanged. `trajectory_cutoffs.make_record` retains the
recorded reward at an original termination and assigns zero to an externally
cut prefix. The latter is a research-imposed cutoff, not a natural failed
termination observed in the original rollout.

This convention follows the pinned tau2 evaluator's premature-termination
gate: `src/tau2/evaluator/evaluator.py`, in `evaluate_simulation`, returns
zero before state evaluation when the termination reason is neither agent
stop nor user stop. The inspected file SHA256 is
`10a87710931429d9abe80fe244cbe7fa0494333587a9c01522a233d64f94196a`.
State satisfaction therefore remains a separate diagnostic, not a reason
to alter the saved completion label or claim an evaluator defect.

`audit_memory_cutoff_satisfaction.py` actually joins all 222 source-cut
records to the prior strict prefix-state replay. It checks task identity,
simulation hashes, source-bank manifest identity and visible-payload hashes.
This is an analysis of previously computed evaluator labels, not a new replay.

| Cut | Externally cut | Already satisfied | Not satisfied, later recorded success |
|---|---:|---:|---:|
| 4 | 74 | 0 | 14 |
| 8 | 69 | 2 | 8 |
| 16 | 63 | 1 | 6 |

Every row reuses the same 74 source executions. At cut8, the two externally
cut but already satisfied records are `673a629dd5b18b47e8d55114` and
`92af1d18869a6a6f60a4f1a2`. Both later end successfully. Consequently the
previous count of ten successful continuations at cut8 contains two already
satisfied states and eight states not yet satisfied. It must not be described
as ten unresolved task states that become successful later.

The first of those records also belongs to the frozen test-selected source
set. Its visible final speed test is excellent, and all three compact lessons
give positive advice despite the completion label zero. That factual review
used only visible evidence; this subsequent state-label join is kept separate.
Neither analysis changes retrieval, memories, task selection or queued model
inputs. No new target result or instruction benefit follows from this audit.
