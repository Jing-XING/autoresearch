# Memory study: analysis readiness and retained results

The manuscript remains incomplete. The 200-episode development study and
its source analyses are retained; the 560-episode registered test study is
still running. Do not analyze its current partial results as a complete
study or treat the checks below as evidence of its eventual outcome.

## Restart provenance

The registration identifies `tau-memory-test40-ties-v1`; its worker manifests
retain that scientific identifier. The actual supervisor batch is
`tau-memory-test40-ties-v2`, using `tau-memory-test40-ties-code-v3.zip`.
The recorded infrastructure amendment predates target generation. The old
flat deployment receipt points to the preceding archive and must not be
silently edited to fit the new archive.

`scripts/prepare_memory_restart_analysis_receipt.py` checks the original and
new archives, the combined deployment bundle, the original registration and
both deployment records. All 53 original archive members are byte-identical;
the only added file is the separately hashed restart supervisor. The new
54-member archive has SHA256
`249d705c1ad71ad7d1434a1bc3ec393894965f6fd8ede4dfca1d87f642788cf9`.
The derived receipt is
`research/evidence/memory_test40_restart_analysis_provenance_v1.json`.
It records static lineage, not completion of the running study.

## Complete-grid analysis command

After all 28 workers terminate successfully and the full raw archive is
retrieved and hash-verified, run from the repository root, replacing
`EXTRACTED_BATCH_ROOT` with the extracted directory containing the actual
`grid_manifest.json`. The shown output path must not already exist.

```sh
python -m scripts.analyze_memory_tie_transfer \
  --root EXTRACTED_BATCH_ROOT \
  --registration research/evidence/memory_test40_tie_registration_v1.json \
  --bank results/remote/tau-train74-qwen3-curation-v2/memory-banks/train-qwen3-cut8-v2.json \
  --code-zip results/deploy/tau-memory-test40-ties-code-v3.zip \
  --deployment research/evidence/memory_test40_restart_analysis_provenance_v1.json \
  --output results/memory-test40-complete-analysis.json
```

The analyzer checks exact task/worker coverage, original registered source
choices, deployment and runtime identities, the official saved reward and
termination fields, and the first model inputs after removing only the
registered lesson wrapper. Target exceptions remain unsuccessful in the
40-task denominator. Extra case artifacts, a saved simulation conflicting
with a null-error status, unexpected workers and incomplete grids are rejected.

Runs failing before any model call have no first input to compare. Their
identities and errors are now explicitly listed instead of being described
as verified input matches. Duplicate-content reports likewise state whether
model I/O was actually observed in every paired run; equal empty records
alone are not evidence of repeated model behavior.

The primary endpoint stays boundary-aware minus full-metadata under the
original record-ID tie rule, separately for each checkpoint. Both alternative
rules remain sensitivity analyses. Gains, losses, joint successes and joint
nonsuccesses partition every comparison. Equal-ticket-group and leave-group-
out descriptions retain the previously frozen definitions. No new bootstrap,
population significance test, best-tie selection or changed success label
has been added.

## Executed analysis checks

```sh
python -m pytest tests/test_memory_tie_full_grid.py tests/test_memory_tie_sensitivity.py tests/test_memory_transfer_analysis.py -q
```

Ten tests passed before inspecting any test40 outcome. The new integration
fixture writes 560 synthetic statuses over 28 synthetic workers, including
one error before generation. It exercises the entire analyzer, then rejects
missing records, an extra episode, conflicting simulation/status fields,
an unmatched batch, a changed target input and an extra worker. Its known
outcomes yield ten paired gains, ten losses and ten of each tie for the
primary contrasts. These are software validation fixtures, not experimental
results or execution of the official tau2 evaluator. Actual full-grid
validation remains pending until the registered experiment closes.
