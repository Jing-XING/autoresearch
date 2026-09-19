# Offline analysis supplement for the frozen eight-task pilot

This supplement implements the already registered state-flow and answer checks.
It is written before any neural pilot outcome is available: the designated
server's supervisor 18283 was observed waiting for dependencies with zero workers
and zero case files on 2026-09-20. It does not change the deployed worker, settings,
task selection, condition order or scientific endpoints. The separate forty-task
evaluation set is neither opened nor launched by this analysis.

## Integrity and scoring gate

The entry point is `scripts/analyze_hotpot_pilot_v1.py`. It requires the original
deployment ZIP and expanded registration receipt, verifies every payload hash,
and requires local replay modules and pinned upstream method sources to match
the deployed bytes. The smaller registration inside that ZIP must match the
supervisor's registration. A closed grid means `complete`, exactly four distinct
zero-exit workers, the exact 48 registered case paths and four worker manifests.
Partial, failed, extra or missing artifacts fail validation; they must be reported
as an incomplete pilot, not silently analyzed as a smaller sample.

For each episode the analyzer feeds its saved replies into the original worker
control flow and the pinned snapshot environment. Every requested input, role,
generation budget, returned reply, recorded error, message, observation, state,
termination and usage total must agree. Only episode wall-clock replay duration
is excluded, because replay does not invoke a model. Token IDs and token counts
are checked structurally; this does not retokenize, reload a checkpoint or
independently reproduce neural outputs. Recreated model exceptions reproduce the
saved class name and message without importing artifact-specified code.

This is a control-flow consistency check using the same worker implementation,
not an independent correctness proof. Scripted witnesses separately assert that
shared simulated search changes subsequent lookup and isolation restores the
baseline observation. Failed predictor calls, pre-generation actor errors,
malformed outputs and the native three-empty-prediction retry all remain visible.

Only after all 48 replays pass does the CLI open the pilot gold file, verify its
selection hash and score with the pinned official answer normalization/EM/F1.
It verifies the scorer's data manifest against the selection as well. It does
not read supporting-fact labels to modify an answer. No-answer and execution
failure episodes score zero in the original denominator of eight per arm/model;
an empty terminal answer is passed to the official scorer as registered.

## Descriptive outputs and attribution limits

Report each checkpoint separately, all three arms, exact EM counts, mean F1,
termination counts, actor/predictor attempts and tokens, recorded generation
seconds and total episode seconds. Report shared-minus-baseline and
isolated-minus-baseline paired EM gains/losses/ties and mean EM/F1 differences.
The eight-task development pilot does not support a confirmatory significance or
generalization claim; no p-value, model pooling or task replacement is added.
These elapsed times are sequential snapshot runtimes, not a parallel speedup.

Count state-field changes at completed simulations and retain per-episode values.
Failed simulations remain in full replayed traces rather than being counted as
completed simulation events. Distinguish complete authoritative trajectory
agreement, actor-visible authoritative observation-sequence agreement, message
history agreement and answer agreement. In particular, a shared simulation's
increment of the bookkeeping `steps` field alone is not evidence that the actor
received a different observation or answer.

Within each checkpoint, group all recorded calls by role, exact input messages
and generation limit. Report repeat counts, returned/error counts, decoded-text,
output-token-ID and input-token-count variants, with every call's location.
Equal-input disagreement is an observed reproducibility limitation, including
possible cross-device effects; it must not be labeled a state-isolation effect.
Groups with no returned replies cannot demonstrate deterministic generation.
Different input histories after divergence do not identify a controlled model
comparison. The report is descriptive; causal interpretation still requires
inspection of the first divergence and whether equal-input outputs agreed.

## Invocation after the batch closes

From the repository root (offline, no model loading):

```sh
python -m scripts.analyze_hotpot_pilot_v1 \
  --root EXTRACTED_HOTPOT_PILOT_ROOT \
  --archive results/deploy/hotpot-pilot-v1.zip \
  --receipt research/evidence/hotpot_pilot_registration_v1.json \
  --gold results/preparations/hotpot-snapshot-control-v1/pilot.gold.json \
  --output NEW_REPORT_PATH.json
```

The output is exclusive-create and records hashes for 48 cases, eight worker
metadata files and the grid manifest, plus the frozen archive, receipt, pilot
gold, scorer and analysis code. Runtime placement/package records are retained,
not assumed identical merely because checkpoints match. The 48-row integration
test uses scripted replies and explicitly invented test answers; its scores are
not experimental results. No actual pilot gold is opened by those tests.
