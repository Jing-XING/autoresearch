# Frozen test-split transfer and tied-source sensitivity

Registered on 2026-09-19 before collecting target outputs. This follows the
complete negative small-split development study and does not replace it.
The experiment evaluates a fixed instruction contrast and its sensitivity to
source choice; it is not a proposal for a new retrieval algorithm.

All 40 official telecom test identities at tau2-bench commit
`b7ea9074c1cba482b30687fecdb5c8425fd6f619` are included. The 74-record
Qwen3 train-source bank, cutoff eight, compact curator prompts, stored lessons,
current task policy, quoted-memory wrapper and official evaluator are fixed.
The bank SHA256 is `52928f597ba4f0baa9d8794130f674ba47038e43eca4fca6654abda4c8b04875`.
No target outcomes, task evaluation predicates or later source continuations
are inputs to source selection or the target model.

Each target has at least three exact top ties under the existing ticket-word
TF-IDF retriever. The control chooses the smallest source record identifier,
exactly as in development. Two alternatives exclude that choice, rank the
remaining tied records by SHA256 of the fixed seed
`memory-tie-sensitivity-20260919:` plus source record identifier, and select
the first and second respectively. All three choices retain the same top
similarity score. The selection uses neither target identity nor outcomes.
Every curated condition and checkpoint receives the same source choice.
Storage-order invariance and control equivalence have actual unit tests.

For each of Qwen3-4B-Instruct-2507 and Qwen2.5-7B-Instruct, collect one
no-memory baseline and full-metadata/boundary-aware memories under each of
the three source choices. This is 40 × 2 × (1 + 2 × 3) = 560 executions.
The baseline is collected once, not copied into three purportedly independent
runs. Generation remains greedy with the shared opening tool-call marker,
512 new tokens, 60 official message steps and five environment errors.
No template, parser, retry or stopping-policy improvement is introduced.
Exceptions are retained as unsuccessful in the primary comparison, with
their raw output, failure type and observed executed prefix preserved.

The primary contrast is boundary-aware minus full-metadata official success
for the original tie rule, separately by target checkpoint. The two alternative
rules are prespecified sensitivity comparisons. Report all 40 paired wins,
losses and ties; compare each memory condition with its checkpoint's common
no-memory baseline; report tokens, curation costs and generation time separately.
Report source reuse and differences by visible-ticket group. All target
conditions are repeated measurements, not additional task identities.

The pre-inference selection audit yields five selected sources per tie rule,
used by 13, 3, 8, 1 and 15 targets. Across rules there are fifteen distinct
sources. This induces substantial shared-memory dependence. Three tie rules
are not independent model seeds or a representative source-bank sample.
No population significance, superiority over strong memory methods, or
benchmark state of the art is inferred from this controlled instruction study.
Human-independent memory-faithfulness annotation is not currently available.

The original 200-episode development results informed the need for this
sensitivity study and are explicitly disclosed. These 40 tasks were not used
to choose the prompt contrast or tie seed. Their public availability does not
establish absence from model pretraining, nor does identity separation prove
independent task families. Further modifications after these results would
require a new experiment and could not reuse this batch as untouched evidence.

## Analysis implementation before target outcomes

`scripts/analyze_memory_tie_transfer.py` requires the complete 28-worker grid,
the exact deployment archive and registration, all 560 registered statuses,
official reward/termination agreement, unchanged task/model/runtime hashes,
and the registered source choice in actual model-call records. It strips only
the exact stored lesson and fixed wrapper from each first input, then compares
the remaining policy/task messages and ordered tools across conditions and
checkpoints. Errors stay in the denominator. It reports all three paired
instruction contrasts separately, common-baseline contrasts, visible-ticket
groups, source reuse and costs; it does not pool the three source choices as
independent tasks or select the best choice after seeing results.

On the already completed development artifacts, the first-input check matched
all 80 full/boundary inputs to 40 no-memory controls and rejected all 80
deliberately altered lesson strings. This checks the input-comparison routine
on real previous records; the full new-grid analyzer has only been compiled
and cannot be called validated on test40 results before those results exist.
