# Prospective output-budget sensitivity

Registered before observing any output of `vakra-expansion-v1`. The unchanged
primary expansion remains 70 tasks, three Qwen checkpoints, two prompts,
sequential execution, twenty model/tool attempts, 512 output tokens per call
and 32,768 input tokens. Twenty-one interpretation ambiguities were marked
before inference; no length-based exclusion is added.

The offline answer-length audit with the pinned Qwen30B tokenizer flags exactly
two tasks under the rule that each of three explicit answer serializations
exceeds 512 tokens: cookbook task 001 (791 names, 5,047–5,406 tokens) and
ice_hockey_draft task 000 (129 names, 646–649 tokens). These measurements are
not a lower bound on every semantically equivalent answer. They do identify
a resource confound in literal complete-list evaluation before any results.

After the primary run, run all three models and both prompts on both flagged
tasks with maximum new tokens 8,192, retaining the original input limit,
twenty-call/step budgets, greedy decoding and exact model versions: twelve
additional target episodes. Do not select arms by success or change wording.
Preserve the primary results. Reproduce any preceding worker tool history
without model inference, then require exact equality of the target's initial
messages, ordered schemas and preview to the primary run before generation.
If pairing fails, retain the failure and do not label that run a matched
budget comparison. Source/reference answer cards are never model input.

Report answer correctness, completeness, input-limit/OOM/protocol events,
output token use and target-wise changes. The intervention changes the
maximum length of every target generation, not just the final response;
interpret it as output-budget sensitivity, not a causal effect of final-answer
space alone. No witness or repair method benefit follows from budget recovery.
This registration is not evidence that the twelve extra runs have executed.
