# Scope and coverage study: offline research artifact

This artifact preserves the eight complete model-execution batches discussed
in the manuscript: 8, 48, 240, 240, 240, 120, 420 and 12 records. These 1,328
executions include repeated tasks and are not 1,328 independent examples.
The supplied checker reanalyses saved outputs with Python's standard library.
It does not generate model predictions, independently label answers or rerun
the native MCP counterfactual experiments.

## Quick start

Extract the outer ZIP into a new directory. With Python 3.11 or later, run
from that directory:

```sh
python -I scripts/verify_paper2_offline_artifact.py --output-dir reanalysis
```

The checker first verifies every payload's size and SHA256, then extracts the
eight immutable raw archives beside their ZIPs. Existing extractions must
match exactly. The output directory must be new; original evidence is never
overwritten. No network, model weights, API key, GPU, package installation or
access to the original research workspace is needed for this command.

The final `reanalysis/report.json` lists every completed check. Separate
stdout, stderr and JSON reports show where a failed check stopped. Run again
with a new output-directory name to retain both analyses. Do not run under
Python's optimization flag: the historical scientific auditors use assertions.

## What is recomputed

The checker reconstructs execution groups from all eight batches, checks
worker completion and raw task coverage, and validates the saved answer
labels against raw hashes and frozen interpretation masks. It reruns the
matched executor comparison, larger-checkpoint and prospective-expansion
auditors, expansion answer aggregation, exact paired-bootstrap and disclosed
Disney-label sensitivity, the twelve output-budget comparisons, and the
four numerical result tables. The SmolLM3 aggregation uses its saved labels.

The first eight-run and 48-run execution reports are compared on their full
rows, grouped outcomes and input hashes. Later analysis reports are compared
as JSON, except declared analysis-script fingerprints and machine-local
analysis-source path dictionaries. Those exclusions do not remove any score,
prediction, task identity, failure, interval or raw-input hash. The manifest
separately hashes the current analysis programs themselves. Three historical
programs gained an optional new-output-path argument; their calculations were
unchanged and their original result receipts remain included.

The original strict-executor report predates two later schema fields. Before
comparison, the verifier explicitly checks that the new `call_policy` is
`single` and every new `tool_budget_rejections` field is zero, then adds only
those neutral fields to the in-memory old report. All original fields remain
compared. The saved original report is not changed. An initial portability
attempt exposed this schema difference and failed rather than ignoring it.
The older 120-run capacity report also predates partial-domain audit fields.
Their exact whole-grid values (`closed_domain=null`,
`closed_domain_complete=false`, `audited_episodes=120`) are required. Its new
scope duration is independently computed from the preserved worker start and
finish timestamps before comparison. The new analyzer fingerprint is treated
as provenance, and the packaged script itself is hash-checked. A second
portability attempt failed on these additions; all original report fields
were unchanged in the comparison.
Its answer summary likewise predates `review_scope=full_registered_grid` and
`complete_batch=true`; both are required before adapting the old schema in
memory. A third attempt stopped on those missing markers. An explicit field
comparison found only these additions and analysis provenance differences;
the expansion, budget and uncertainty programs also completed separately.

This is record reanalysis. Exact annotation-to-record linkage does not establish
that a qualitative annotation is correct. The cards and complete final texts
are included to make those judgments reviewable. The saved annotation is one
assistant's unblinded review, not an independent human evaluation.

## Included materials and boundaries

- Complete raw archives of the eight model batches and the selected cookbook
  acquisition control, rather than only successful examples.
- Frozen deployment archives for those model configurations and budgets.
- The paper, detailed study record, bibliography, review PDF, cards, labels,
  execution summaries, uncertainty reports and native replay reports.
- Analysis and execution source, preparation manifests, questions, eight
  prepared databases, the relevant upstream source snapshot and licenses.
- Exact model-file manifests and revisions; model weights are not redistributed.

The native replay scripts and their saved outputs are included, but the quick
start does not launch the native MCP server or independently reestablish the
database-intervention witnesses. Those scripts require the corresponding MCP,
database and dataframe dependencies recorded in the preparation/runtime logs.
Some historical scripts use fixed output paths; run them only in a separate
reproduction copy and preserve the included reports. Likewise, launching a
model experiment requires adapting its explicitly recorded research-server
paths to the new machine and downloading the pinned model files. No such
reexecution is claimed by the offline check.

## Provenance and licensing

VAKRA server source is pinned at commit
`c9e82dfe46aee016d2bfe3a0c8fed652760e4c0c`, and the dataset at revision
`1388b9f1aaed887a73957eba651a6c2034010476`. The upstream dataset card and
license are included at `results/third_party/vakra-data/README.md` and
`results/third_party/vakra/LICENSE`. They identify CC BY-NC-SA 4.0; that
upstream material and derived task content retain those terms. The bundle
does not relicense upstream data, model output, code or model weights.
Prepared runtime copies retain their upstream license files. See the dataset
card for source attribution and the source files for their notices.

Raw records preserve the original experimental metadata, including server
paths, timestamps, checkpoint fingerprints and failed executions. No `.env`,
private key, browser state, local virtual environment or model-weight directory
is included. The manifest enumerates the complete intended payload.

The artifact is supporting material for a research manuscript. Successful
reanalysis does not establish publication readiness or guarantee acceptance.
