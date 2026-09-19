# Reproducing the complete prospective expansion analysis

## Complete saved-record analysis package

The local archive `results/remote/paper2-offline-evidence-v4.zip` contains
702 payload files plus its manifest, 24,089,944 bytes, SHA256
`89fc8480bcab4a793903c8ad68696b8ec9aa0fcc79c50db6f68dbd8fb8e25e24`.
It includes all eight complete model batches (1,328 executions), the prepared
databases, source, annotations, replay reports and paper artifacts. Extract
into a new directory and run:

```sh
python -I scripts/verify_paper2_offline_artifact.py --output-dir reanalysis
```

The actual isolated Windows Python 3.12.14 run completed 17 checks. Its
receipt is `research/evidence/paper2_offline_artifact_v4.json`. A deliberately
altered extracted prediction was rejected, and the original bytes were
restored. Earlier package attempts are retained with their three explicitly
guarded legacy-report schema adaptations. See `artifact_README.md` for scope,
licensing and exact exclusions from provenance comparisons.

This recomputes saved-record analyses, not model inference, independent answer
judgments or native MCP mutation executions. The package is local and has not
been published as a public download. After explicit user approval, the same
archive was transferred to the designated research server. An actual Linux
Python 3.13.5 isolated run completed all 17 checks with exit code zero in
8.911 seconds. Its returned JSON report equals the Windows report after JSON
parsing; byte hashes differ because the platform text writers use different
line endings. The receipt retains both hashes and the transfer outcome.

## Individual analyses and review PDF

The recorded nine-page review PDF and offline-v4 ZIP predate the annotation
sensitivity extension below. They remain immutable historical artifacts;
their verification receipts do not cover the extended manuscript or analysis.

To check the reorganized manuscript's four result tables against the retained
evidence, run `python scripts/check_paper2_manuscript_tables.py`. To rebuild
the review PDF with ReportLab and pypdf installed, run:

```sh
python scripts/build_review_pdf.py --paper research/paper2 \
  --output output/pdf/paper2-scope-coverage-review.pdf --date 2026-09-20
```

The builder labels this as an incomplete review draft and includes the eleven
bibliographic records. Rendering is not evidence of publication readiness.

This entry covers manuscript section 4 and the integrated 420-run answer
analysis, followed by the section 5.2 generation-budget control. The detailed
preceding manuscript is preserved verbatim in `study_record.md`; its sections
10.8–10.10 supply the former numbering. The offline-v4 package above covers
its recorded 17 saved-record checks; the later annotation sensitivity is a
separate repository analysis. Earlier studies retain their scripts and
evidence references in `claim_to_evidence.md`.

## Annotation sensitivity extension

From the repository root, with the original expansion ZIP and committed
evidence present, run the following into a previously nonexistent output:

```sh
python scripts/analyze_expansion_annotation_bounds_v1.py \
  --output annotation-bounds-recomputed.json
python -m pytest tests/test_expansion_annotation_bounds.py -q
```

The analysis itself uses only the Python standard library. It verifies the
original raw ZIP and episode bytes, frozen cards and annotations, and
recomputes the original paired scores. It then groups identical final text
within each question across checkpoints and prompts. A hypothetical label
flip affects every occurrence in that group, while missing finals stay
unsuccessful. It reports exact per-checkpoint envelopes for at most zero
through five changed judgments, minimum changes to a tie and sign reversal,
and hypothetical witness groups. These are not discovered mistakes or error
probabilities. Per-checkpoint extrema need not be jointly attainable.

A separate all-70-task envelope fixes the 49 scored tasks and relaxes binary
labels on 21 ambiguous tasks, tying identical text and keeping absent answers
at zero. It does not assert that all endpoint assignments arise from coherent
SQL interpretations. No labels, ambiguity mask or primary scores change.
The recorded output is
`research/evidence/vakra_expansion_annotation_bounds_v1.json`; its hashes tie
the report to the source code and inputs. Three tests check exhaustive small
cases, repeated judgments and missing-answer constraints. The actual report
finds zero conflicts among 15 repeated groups (31 executions), and tie/sign
reversal thresholds of 4/5, 1/2 and 2/3 judgments for Qwen3, Qwen2.5 and
Qwen30B respectively. This supplements the eight-answer Disney sensitivity,
without supplying independent semantic adjudication.

## Inputs

- Raw artifact: `results/remote/vakra-expansion-v2-complete.zip`, 6,097,663
  bytes, 517 members; SHA256
  `2e59af3255513bea2933f61822ad39131fb33f8de59ad5b1b5b2e10be7c572f5`.
- Frozen deployment: `results/deploy/vakra-expansion-v2.zip`; SHA256
  `b254562e1969a6bff4299bee152777dc86d29f2489a93455956ef97766ef0961`.
- Exact model/preparation reference manifests and fixed SQL cards in
  `research/evidence`, plus the earlier Qwen reference manifests from
  `results/remote/vakra-permissive-v1`. The grid analyzer validates these
  dependencies; it does not download or infer missing versions.
- All 420 labels and reasons:
  `research/evidence/vakra_expansion_complete_annotations_v1.json`.
  These are one assistant's unblinded labels, not independent human scoring.
- The previously disclosed eight-answer Disney alternative interpretation is
  retained in `vakra_expansion_disney_review_sensitivity_v1.json`.

Extract the raw archive under `results/remote/vakra-expansion-v2-complete`.
Keep the `runs/vakra-expansion-v2` prefix. The following commands use Python
standard-library dependencies and never invoke a model or native MCP tools:

```sh
python scripts/analyze_vakra_registered_grid.py \
  --root results/remote/vakra-expansion-v2-complete/runs/vakra-expansion-v2 \
  --archive results/deploy/vakra-expansion-v2.zip --kind expansion \
  --output execution-recomputed.json

python scripts/summarize_vakra_registered_answers.py \
  --root results/remote/vakra-expansion-v2-complete/runs/vakra-expansion-v2 \
  --summary research/evidence/vakra_expansion_complete_grid_v1.json \
  --annotations research/evidence/vakra_expansion_complete_annotations_v1.json \
  --output answers-recomputed.json

python -m unittest tests.test_exact_paired_bootstrap
```

Output files must not exist. The exact-bootstrap calculation is in
`scripts/analyze_expansion_complete_sensitivity_v1.py`; its committed result
contains every rational probability. Running its `main` entry point requires
a fresh checkout without the existing output receipt, since it intentionally
refuses to overwrite evidence. Its pure `exact_bootstrap` function can be
imported without writes. The distribution preserves each domain's task count
and each original/reminder pair; it does not resample checkpoints as tasks.

The uncertainty program now accepts `--output NEW_REPORT.json`, so an isolated
reproduction need not remove the original receipt. The budget-comparison and
SmolLM3 answer-summary programs have the same optional argument. Their
calculations are unchanged; the existing-output refusal remains in force.

The label materialization script records an already performed qualitative
review and imports the earlier 300 labels only after source-hash checks.
Executing that script does not produce a second independent assessment.
No failed run, missing answer, ambiguous task's execution cost, or output-limit
case is silently removed. The separate larger-output experiment is a distinct
registered artifact and must not be substituted for the 512-token primary run.

## Twelve-run generation-budget comparison

The completed additional archive is
`results/remote/vakra-output-budget-v2-complete.zip`, 259852 bytes, 49 members,
SHA256 `9ad8955cdf0c368412e1e57f1f2ae2b74aedbd4d63f1d79f956e4cf6f71f63d7`.
Its deployment archive is `results/deploy/vakra-output-budget-v2.zip`, SHA256
`7dea81ad419844bdb3f14c6386e5e6491eb64b0dc06af2e1f34afc86b8e851bd`.
Extract the result under the archive basename, retaining its
`runs/vakra-output-budget-v2` prefix. Keep the completed primary expansion
archive, cards and annotations above available at their declared paths.

`scripts/analyze_vakra_output_budget_complete_v1.py` verifies input identity,
configuration/source hashes, tool histories, token-ID prefixes and all twelve
complete responses. It records the already performed assistant review; it
does not generate new independent labels. It also compares the four positive
hockey name multisets directly with the fixed SQL cards. The output is
`research/evidence/vakra_output_budget_complete_analysis_v1.json`.
For regeneration, use an isolated reproduction copy without that generated
receipt; the entry point refuses to overwrite an existing receipt. Run
`python -m unittest tests.test_budget_complete_names` for the format and
multiset checks. No model inference is needed for this analysis.


## Annotation sensitivity added after offline artifact v4

The core v4 archive and its seventeen Windows/Linux checks predate the
annotation-sensitivity extension. They must not be cited as verification of
this extension. Its separate receipt is
`research/evidence/paper2_annotation_sensitivity_receipt_v1.json`.
From the repository root, with the pinned expansion archive and committed
cards, annotations and summaries available, run:

```bash
python scripts/analyze_expansion_annotation_bounds_v1.py --output annotation-recomputed.json
python scripts/check_paper2_manuscript_tables.py
```

The first output path must be new. Compare its parsed JSON with
`research/evidence/vakra_expansion_annotation_bounds_v1.json`; byte-identical
line endings are not required for JSON-value comparison. The program verifies
all 420 raw records, preserves exact task/text identity and missing-answer
constraints, and recomputes the hypothetical label-flip and ambiguity bounds.
It does not create new judgments or provide independent semantic adjudication.
The second program checks eighteen result rows, the executed reminder and the
unchanged historical study record; it is an editorial consistency check.
