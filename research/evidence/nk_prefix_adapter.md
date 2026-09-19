# NK-schema comparator: implementation and scope

Prepared on 2026-09-19 before inspecting any outcome of the registered
40-task test extension. No new model inference or target episode is reported
in this note. The existing 560-episode registration and deployed code remain
unchanged. This preparation is not a complete new target-run registration.

## Why this comparator

The existing three-sentence curator is a simple prompt control. The released
[Negative Knowledge implementation](https://github.com/hch-wang/Negative_Knowledge/tree/015ac48da8a9ebd2420ffee0f4f84bd5d1d8bbb9)
provides a stronger structured representation: six top-level fields, five
closed-vocabulary failure dimensions, and bounded recommendation text. Its
single-round ScienceAgentBench prompt and Python validator were inspected
locally. The MIT notice is preserved in
`../licenses/negative_knowledge_MIT.txt`.

Our new module preserves those fields, vocabularies and four character limits.
The paired conditions differ only by the same boundary instruction used in
the initial study. Both receive identical visible policy, ticket, observed
messages, reward and execution metadata. Strict parsing records malformed
JSON, duplicate keys, wrong identities, invalid taxonomy, excess fields,
oversize text and output-ceiling hits. It does not repair model responses.

This is **NK-schema adaptation**, not full NK or its paper's reproduced
baseline. We replace scientific code/log files and the upstream tool-driven
Anthropic curator with a single local-model prompt over a telecom prefix;
we use cross-task transfer, not the single-round prompt's same-task retry.
We do not implement iterative cross-round synthesis or explicit downstream
adoption/rejection. Unknown causes are permitted rather than manufacturing
a diagnosis. These changes must remain visible in any results table.

## Observed eligibility and comparison consequences

All 74 visible cut-8 records were inspected by code. Seventy carry zero
recorded reward (69 external cuts and one original unsuccessful termination).
Four carry reward one and are ineligible for this negative-record comparator:
`09060edd04ee056725e696c1`, `28685250e103b91dab68f65e`,
`5d91821ff9e2f95b6a8924fc`, and `74d18ca8b1298cd881dfd617`.
Selection uses the visible label, never future source success or a target
reward. Zero does not assert that the source strategy was ineffective.

The resulting 140 input packets cover both conditions for every eligible
record. The 1,024-token ceiling permits the structured object; the old
three-sentence experiment used 256. Therefore this adaptation must not be
presented as a token-matched comparison with the old memories. Both new arms
share the ceiling, and realized input/output costs must be reported.

A future transfer comparison must freeze the common 70-source retrieval pool
before curation quality or target results are opened. If a retrieved source's
curation is invalid, retain that source choice and inject no memory; do not
retrieve another source or delete the target from the denominator. Report
invalid curation separately. The representation contrast is between the two
new arms; comparison with the old 74-source bank also changes eligibility.
Target execution has not yet been implemented for this preparation, and no
effect is claimed. Generation is now implemented and queued as described below.

## Other baseline fidelity constraints

[AWM, Section 2.3](https://arxiv.org/html/2409.07429v1), uses canonical examples
offline and admits evaluator-approved successful trajectories online. A
top-1 lesson from arbitrary zero-reward prefixes would change that method.
Its complete workflow integration must also be distinguished from our
retrieval rule. It remains a separate end-to-end comparison candidate.

[Li and Zhu, Sections 3.3 and 4.5](https://arxiv.org/html/2608.17684v1), already
study matched acquisition and an AWM action-envelope incompatibility. This
reinforces the need to verify a port's execution interface before interpreting
its utility. We have read their protocol, not reproduced their results.

## Executed checks

Four local tests pass: paired evidence identity and immutability; hidden-field
and positive-record rejection; strict invalid-output retention; and preparation
without reading sibling label files or overwriting artifacts. The preparation
ran over all 74 real visible records. It makes no network or model calls.
Hash receipts are recorded in `nk_prefix_preparation_v1.json`.

## Frozen execution and retained failures

The independent `nk-prefix-curation-v1` deployment passed eight tests on the
actual remote Python environment and validated all 140 prepared packets
without loading a model. Supervisor PID 10949 was launched and its live
`/proc/10949/cmdline` was inspected. It waits for the existing 560-episode
memory batch to terminate successfully and for all GPUs to be idle. The
curator weights must match the eleven file hashes from the previous Qwen3
curation. There are four disjoint source shards, a two-hour execution limit,
no automatic generation retries and no target inference in this batch.

The bank assembly code now requires all four shards, all registered source
and condition pairs, identical runtime configuration, the frozen checkpoint
and code hashes, and input equality with the prepared packets. It revalidates
raw replies before creating memory entries. All invalid/error entries remain
in the retrieval pool. An invalid selected memory becomes an empty experience
under the unchanged common wrapper; this is not byte-identical to the
no-memory control, which lacks that wrapper. A synthetic four-shard fixture
with every generation failing still builds a four-source bank, while a missing
output fails assembly. This is a CPU software test, not a model experiment.
Thirteen local tests pass in total; bank assembly has not run on real new
curation outputs, which do not yet exist.

Before any new curation output, retrieval choices were frozen for the same
40 official test tickets using the eligible pool. They select five records
with reuse counts 13, 3, 8, 1 and 15. Only one target's selected source identity
differs from the old 74-source rule: the successful airplane-mode source is
replaced. TF-IDF weights also change when the pool changes. This makes the
two new arms mutually comparable on source choice, not equivalent to the old
bank. The receipt is `nk_prefix_target_selection_v1.json`; it freezes source
selection, not a complete target execution protocol. Target outcomes remain
unseen and no performance claim follows from these counts.

The source-choice artifact was regenerated byte-for-byte with
`python -m scripts.freeze_nk_prefix_target_selection --output NEW_PATH`.
Its SHA-256 is
`425fbd67713028e1bd5063eaa7d5cd05edf16c55cefd5eaaf8e62caba29665b9`.
