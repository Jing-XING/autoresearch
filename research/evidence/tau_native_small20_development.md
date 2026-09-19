# Public telecom development batch: complete trace audit

These are development observations, not confirmatory evidence for a proposed
method. No held-out test tasks were run. The first four tasks repeat an earlier
formatting control and are not additional independent observations.

## Provenance

Official Sierra tau2 source/data commit
`b7ea9074c1cba482b30687fecdb5c8425fd6f619`; source manifest SHA256
`d07cc342f43894f866d1fd151fdd1ed996976cb194299e2d87913bc5bc8ee349`.
Twenty official telecom `small` tasks in original order, solo protocol, two
open-weight models, deterministic greedy decoding, seed 20260919, maximum 512
generated tokens per call, 60 orchestration steps, and five environment errors.
The supplied `<tool_call>` opening marker is a formatting baseline shared by
both models. It is not a proposed method or a full grammar constraint.

All four workers exited zero. The raw 141-file archive has 8,089,469 bytes and
SHA256 `772fbb8d4beeeb1b528faeb1b29cb3bed109b049269aaa9cc92f9bbeb723b880`.
It is retained at `results/remote/tau-native-small20-prefix-v1.zip` and extracted
under the corresponding directory. The manifest, per-model weight hashes,
native prompts, actual completion token IDs, official simulations, and
supervisor script are included. This batch used the v2 adapter archive.

## Complete outcomes

| Model | Official successes | Agent-stop episodes | Step-limit episodes | Environment-error-limit episodes | Run/protocol exceptions |
|---|---:|---:|---:|---:|---:|
| Qwen3-4B-Instruct-2507 | 13/20 | 19 | 1 | 0 | 0 |
| Qwen2.5-7B-Instruct | 7/20 | 14 | 5 | 1 | 0 |

An environment-error-limit episode is a real unsuccessful agent episode, not
a missing result. All 40 registered tasks remain in the denominator. The
models' different success fractions on this development set do not establish
a general model ranking.

`tau_native_small20_prefix_v1_summary.json` validates manifest compatibility,
prompt hashes, task identity, recorded rewards, and coverage. An independent
offline audit (`tau_native_small20_prefix_v1_state_audit.json`) reconstructs
every completed generation/tool-result group using the official strict replay
and evaluators. Hidden assertions are used only in this offline audit; they
were never given to the agent. Tasks with ACTION criteria are scored using the
official action evaluator as well as environment assertions.

The audit found exactly 20 episodes that ever met their task criteria, matching
the 20 official successes. There were zero success-to-failure reversals and
zero episodes that met the criteria at the end but received an official zero.
Thus missing termination after a completed repair does **not** explain the
failures in this public batch, although it explained losses in the earlier
synthetic SQL memory pilot. The remaining failures require task-level analysis.

Several failures repeatedly called network/MMS diagnostics. Repetition alone
does not prove waste: an identical diagnostic after a state-changing action
can provide new evidence. Entity binding, incorrect arguments, and unresolved
faults must be distinguished before proposing a controller.

## Policy-invariant cutoff preparation

`autolab.trajectory_cutoffs` constructs offline prefixes after complete
generation/result groups. It does not rerun a budget-conditioned policy. The
original policy/ticket and observed history stay unchanged. At a cutoff before
the recorded end, the observed benchmark reward is zero and the stop origin
is explicitly an external generation cutoff. Future outcomes are written into
separate evaluator-only label files, never curator-visible inputs.

| Model | Generation cutoff | Prefixes ending before the full recorded end | Of these, later recorded successes |
|---|---:|---:|---:|
| Qwen3 | 4 | 20 | 13 |
| Qwen3 | 8 | 14 | 7 |
| Qwen3 | 16 | 8 | 3 |
| Qwen2.5 | 4 | 20 | 7 |
| Qwen2.5 | 8 | 16 | 4 |
| Qwen2.5 | 16 | 11 | 1 |

There are 120 prefix records but only 20 task identities, each evaluated by two
models. These prefixes are correlated, not 120 independent tasks. Later
success does not prove that every earlier action was correct. Neither this
table nor survival prediction identifies the downstream utility of memory.
Actual memory interventions and independent target tasks are still required.

## Consequence

Do not pursue a public-benchmark explanation based on the synthetic pilot's
missing-submit phenomenon. Retain externally interrupted experience as a
testable research question, separating terminal failure, external cutoff,
protocol errors, and observed state evidence. The complete official train
split is being collected under the same fixed adapter to support the next
experiment; the official test split remains untouched.
