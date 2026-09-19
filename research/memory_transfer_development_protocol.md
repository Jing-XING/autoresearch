# Controlled transfer of interrupted experience: development protocol

Status: implemented for development; no transfer result yet. This document
records decisions before the first public-task memory treatment run. It is
not a completed-paper claim or a confirmatory preregistration.

## Scientific question and boundaries

Does retaining the externally imposed stopping boundary when curating an
experience change its utility on a different tool-using task? The outcome of
interest is the target agent's official reward, not whether the curator writes
a plausible explanation. A zero reward at the source deadline is a valid
finite-budget outcome. It does not, without additional assumptions, identify
the outcome under continued execution or the merit of each previous action.

The first controlled experiment uses the complete official telecom train split
as the source and the small split as the development target. The current audit
checks 20/74/40 task IDs for small/train/test: every pair of splits is disjoint.
Hashes of the visible ticket plus the complete initial state are also unique
within and disjoint across these splits. This is an exact-identity check, not
a claim that different task families or templates are statistically unrelated.
No test outcomes have been collected or used for model selection.

Source trajectories use the same fixed policy regardless of an offline
cutoff. Cuts occur after a complete generation and its associated tool-result
group. They are not equivalent to changing an agent-visible budget prompt.
The first source pool uses Qwen3 trajectories at generation cutoff 8; the other
recorded model and cutoffs 4/16 are retained for subsequent development checks.
All eligible source records at this cutoff enter the pool; future reward does
not select the records. Original run exceptions remain explicitly accounted
for even when they do not yield a complete simulation suitable for prefixing.

## Conditions and what they identify

1. **No memory:** the official policy and visible ticket, with the same native
   formatting baseline used for every target condition.
2. **Raw:** the selected source ticket, observed history, boundary metadata and
   observed reward, without a curator. It omits the repeated source domain
   policy but retains all observed source actions/results.
3. **Outcome only:** a generic reusable lesson from the same observed history
   and finite-budget reward, with the stopping metadata omitted.
4. **Full metadata:** the same generic curator instruction, with the recorded
   stopping origin and generation counts supplied.
5. **Boundary aware:** the same data as full metadata, plus an explicit
   instruction to avoid attributing a deadline alone to strategy failure.

Full metadata versus outcome only changes available information. Boundary
aware versus full metadata changes the curator instruction. Neither contrast
identifies a latent psychological mechanism by itself. All curated arms use
the same curator checkpoint, greedy decoder and 256-token output ceiling;
actual output lengths and total curation/inference costs are reported. An
equal ceiling is not an exact length match. Raw memory can be much longer.

The generic reflection arms are **not** presented as an exact reproduction of
Reflexion. Reflexion's original protocol updates memory across repeated trials
of a task and includes a heuristic that triggers reflection after excessive
actions or repeated unchanged interactions. Our transfer experiment uses a
fixed source bank and different target tasks. The original method therefore
provides motivation and a future baseline specification, not an interchangeable
name for our prompt. [Original paper, methods and ALFWorld protocol](https://arxiv.org/html/2303.11366v4).

## Fixed retrieval and execution

Retrieve one source episode using TF-IDF cosine over source/target ticket
words. Numerals and mixed alphanumeric IDs are excluded from the vocabulary.
The source pool, document frequencies, tie break and selected source record
are shared across treatment arms. Generated memory text, future outcomes,
hidden task identifiers and evaluation criteria are not retrieval features.
All exact score ties are logged. This simple retriever is a control, not a
claimed contribution or an assumption of optimal retrieval. Limited ticket
diversity may produce many ties and must be reported rather than hidden.

The current official policy/ticket is preserved verbatim. A common wrapper
identifies prior experience as potentially inapplicable quoted data. Only the
lesson reaches the model; source IDs and condition labels remain in audit
metadata. All targets use the official transitions/evaluator, greedy decoding,
the supplied opening tool marker, 512 generated tokens per call, 60 message
steps and a maximum of five environment errors. The method does not access
hidden prefix assertion labels or future continuation labels.

## Analysis before any confirmatory study

The primary development comparison is task-paired official success between
boundary-aware and full-metadata curation, separately for each target model.
Report all five conditions, all task failures, and paired wins/losses. Inspect
changes in tool errors, selected entities, repeated observations, termination,
source/target tokens and source curation cost. Do not use a reduced successful
subset or equate syntactic validity with task completion.

The experiment initially has only 20 development task identities. Different
cutoffs, source models, or repeated deterministic runs of those tasks do not
increase the number of independent tasks. Before formal testing, freeze the
method, meaningful contrasts and task-family clustering; select appropriate
confidence intervals and account for multiple comparisons. A positive result
here is only a signal to investigate. A negative result may replace the
candidate. A credible paper requires independent evidence and comparison to
the closest methods beyond these prompt controls.

## Code and traceability

`trajectory_cutoffs` separates visible inputs from future labels.
`experience_curator` reads only the inputs directory.
`experience_memory_bank` verifies complete paired coverage, exact curation
inputs and source hashes, retains source exclusions, and rejects overlap.
The optional memory arguments to `tau2_native_baseline` record the exact bank
hash/condition; the native adapter logs selected record, score and ties without
exposing them to the model. Changes are deployed to an isolated revision;
running source workers retain their original code. Curation starts only after
all 74 selected source episodes are complete and the assigned GPUs are idle.
