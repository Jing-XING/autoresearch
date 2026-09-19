# Research evidence units: a bounded feasibility pilot

Status: frozen development design, not a fifth paper or a new statistical
method. Written before preparing examples or observing model responses.

## Question and contribution gate

Can a local model distinguish duplicated experiment reports from two
estimators evaluated on a shared resample? The latter supplies a matched
comparison; collapsing all equal resample identifiers would erase an arm.
This is a prerequisite measurement task, not adaptive research performance.
An eventual study would need actual experimental decisions, diverse research
tasks and a contribution beyond standard grouping or provenance prompts.

GraphEcho already studies repeated origins, active evidence acquisition and
provenance controls. Its section 3.2 defines verdicts from distinct supporting
and refuting origins. That prior work precludes claiming novelty for simple
deduplication. Here the narrow design distinction is between a resample,
an estimator evaluation and a displayed report. Its usefulness remains to
be tested; a change of domain alone does not establish novelty.

## Fixed examples and retained provenance

Use only the already executed public risk diagnostic, archive SHA-256
`b9b07c7f46eccf90a366262f1ae55905d7afd3e53bb4c69e2330a61bf8555c3d`.
Choose selection block 0, budget 100, pools dev00/dev01/dev02, solely by
position. Do not rank or filter pools by estimator effects. All pools and
labels are public development material; none is claimed held out.

For seed index j, estimator A has saved error e0, and estimator B has error
e0+d. Display squared errors, retaining the exact saved floating-point
components separately. A and B are aliases for uniform and c=1 difference
estimation. These are measured error components from a prior calculation,
not newly executed estimators or an official benchmark score. No median or
mean superiority judgment is requested.

Each pool supplies these five views, fifteen examples in total:

| View | A seed indices | B seed indices | Copies of each evaluation |
|---|---|---|---|
| Small paired | 0..3 | 0..3 | 1 |
| Repeated paired | 0..3 | 0..3 | 3 |
| Larger paired | 0..11 | 0..11 | 1 |
| Disjoint | 0..11 | 12..23 | 1 |
| Partial overlap | 0..11 | 8..19 | 1 |

Each displayed report has a distinct display identifier. Replicated reports
retain the same evaluation identifier, arm, resample and value. Resample
identity denotes the same sampled label set within one pool and budget.
Distinct recorded seeds are distinct RNG invocations; this does not prove
independence of populations or real-world datasets. Order is fixed by an
opaque hash of example and report ID, not by outcome. IDs must not contain
view names or count labels. Different examples reset the model context.

Gold fields are unique evaluations for A and B, complete matched pairs,
redundant reports, and design class (paired/disjoint/partial). They are
structural quantities, not inferred scientific truth. Partial-overlap
examples must not be silently reduced to either wholly paired or wholly
independent data. Equal numerical scores alone do not identify duplicates.

## Planned model pilot

Use the previously pinned Qwen3-4B-Instruct-2507 and Qwen2.5-7B-Instruct,
fifteen examples each, thirty responses. One greedy call per example,
384 maximum generated tokens, 16,384 maximum input tokens, native template,
no tools or model-based retries. Display the full identity contract and all
reports. Request a single JSON object with the five gold fields. This is
explicitly a static structural audit, not a tool-using research-agent trial.
Do not launch before the existing Hotpot pilot closes successfully. Freeze
the eventual worker, package and model references before those model calls.

Score strict all-field correctness over all fifteen examples per checkpoint;
malformed, missing and generation-error responses remain incorrect. Also
report every field, each view and the three pool groups. For small versus
repeated paired, report exact correctness changes and count inflation.
Do not pool the thirty responses as thirty independent research tasks or
attach a deployed error-rate confidence interval. Repetition shares the
same observations; the other views change the evidence as specified.

A deterministic grouping baseline is expected to solve the declared schema;
that is a measurement sanity check, not a competing learned method. A
resample-only collapse is an intentionally wrong diagnostic control and
must not be attributed to GraphEcho. Successful structural parsing alone
cannot justify a method claim. If the models already solve this pilot, or
only a trivial schema explanation fixes it, do not expand it into a paper
without a further decision-level question and closest-work check.

## Source coverage

GraphEcho: https://arxiv.org/html/2609.17695v1, sections 3.1-3.4, 4 and 5
inspected for design overlap. No reproduction of its code, training or
reported results is claimed. The public risk diagnostic receipt and its
independent reanalysis remain the authority for the underlying observations.
