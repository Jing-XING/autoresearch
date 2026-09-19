# Reproducing the complete prospective expansion analysis

This entry covers manuscript sections 10.8–10.9 and the integrated 420-run
answer analysis. It is not yet a single portable reproduction of every study
in this working manuscript. Earlier studies retain their own scripts and
evidence references in `claim_to_evidence.md`.

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

The label materialization script records an already performed qualitative
review and imports the earlier 300 labels only after source-hash checks.
Executing that script does not produce a second independent assessment.
No failed run, missing answer, ambiguous task's execution cost, or output-limit
case is silently removed. The separate larger-output experiment is a distinct
registered artifact and must not be substituted for the 512-token primary run.
