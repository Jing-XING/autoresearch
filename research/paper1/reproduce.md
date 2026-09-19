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

## Structured NK-schema extension: analysis frozen before outcomes

The separate 140-curation and 160-target extension has its own complete-grid
analyzer, `scripts/analyze_nk_test40_v1.py`. During preparation of this
analysis, the designated server's two supervisor processes were verified
live, waiting for dependencies with zero workers and no outcome files. The
original protocol and deployed inference code are unchanged. This is an
NK-schema adaptation, not a reproduction of the full Negative Knowledge
method or an additional independent set of target tasks.

After both batches close successfully, retrieve the full raw directories,
the generated bank, and the original prepared inputs. From the repository
root, with the retained original and restarted deployment archives available,
run into a new output path:

```sh
python -m scripts.analyze_nk_test40_v1 \
  --target-root EXTRACTED_RUNS/tau-nk-test40-v2 \
  --curation-root EXTRACTED_CURATIONS/nk-prefix-curation-v2 \
  --prepared EXTRACTED_REVISION/nk-prefix-curation-v2/prepared \
  --bank EXTRACTED_BANKS/nk-prefix-curation-v2.json \
  --source-bank results/remote/tau-train74-qwen3-curation-v2/memory-banks/train-qwen3-cut8-v2.json \
  --output results/nk-test40-complete-analysis.json
```

The entry point verifies both original archives against the restart amendment
and deployed combined bundle. The 203 original curation members and 68
original target members are preserved byte-for-byte; each restart adds only
its supervisor. The curation restart has no separately recorded repeated
preflight; the target restart does. This provenance check does not establish
that either batch completed. The full target grid must close before the
entry point reads any curation text or target outcome.

The analyzer checks the prepared input bytes against the deployed archive,
revalidates every raw curation reply using the frozen schema, rebuilds the
70-source bank and compares its serialized content to the bank actually
used. Integer shard keys undergo their ordinary JSON string conversion;
no field, prediction or memory text is excluded from the comparison. All
four curation and eight target workers must finish successfully, with exact
registered coverage. Generation errors, invalid memories and target errors
remain in their original denominators. Empty experience retains the common
wrapper and is not described as a no-memory run.

For the 160 targets, the analyzer verifies code/model/runtime manifests,
task fingerprints across cells, saved official reward and termination,
recorded source choice, curation status and exact injected memory text.
First inputs and ordered tool schemas must match across treatments and
checkpoints after removing only the fixed memory wrapper. Runs failing
before generation are explicitly listed as lacking an observed first input.
This checks retained execution records; it does not rerun the evaluator or
independently establish semantic correctness of generated memories.

The report preserves all 40 paired outcomes per checkpoint, including both
kinds of ties, and the registered visible-ticket-group, group-equal and
leave-group-out descriptions. It reports curation validity, distinct memory
texts including empty text, source reuse and recorded generation costs.
Unobserved costs of generation errors remain missing rather than assumed
zero. Curation is charged once per bank; model loading and source collection
are excluded. Group weighting is not a population confidence interval, and
the program makes no comparison to the earlier no-memory or generic-curation
runs without a separate compatibility analysis.

Eight tests passed across `tests/test_nk_complete_analysis.py` and
`tests/test_nk_prefix_bank.py`. The new fixture contains 140 synthetic
curations and 160 synthetic targets, including invalid JSON at the output
ceiling, a curation generation error, a target error before generation and
13 targets receiving empty memory. Exhaustive coverage, known paired
counts, unequal-group weighting, raw bank reconstruction and changed-input,
reward, usage and extra-file rejection are checked. These fixtures contain
invented outcomes and are not experimental results. Validation evidence is
recorded in `research/evidence/nk_test40_analysis_integration_v1.json`.
