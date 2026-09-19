# Offline evidence artifact for the recovery-interface study

This accompanies an **incomplete working manuscript**. It supports byte-level
inspection and offline reanalysis. It is not a new experiment, a reproduction
of published model scores, or a certificate of publication readiness.

## Current review manuscript

The updated PDF is `output/pdf/paper3-recovery-interfaces-review-v3.pdf`.
It includes the historical retail screen and the three-question scientific
synthesis. Its twelve pages, seven tables and nine references were visually
checked; the source and output hashes are recorded in
`research/evidence/paper3_review_pdf_v3.json`. The prior manuscript is retained
as `research/paper3/study_record_v1.md`. Rebuild the current review PDF with:

```text
python scripts/build_review_pdf.py --paper research/paper3 --output output/pdf/paper3-recovery-interfaces-review-v3.pdf --date 2026-09-20
```

The integrated offline artifact described below retains its original v3
contents. It does not include the later historical screen, which has a
separate self-contained artifact, or the current revised manuscript/PDF.
The two artifact version numbers do not imply identical coverage.

## One-command reanalysis

Use Python 3.10 or later, with no additional packages, GPU or network access.
Obtain `paper3-offline-evidence-v3.zip`, its SHA-256 from the accompanying
`paper3_offline_artifact_receipt_v3.json`, and
`scripts/verify_paper3_offline_artifact.py` from this repository. Run:

```text
python scripts/verify_paper3_offline_artifact.py paper3-offline-evidence-v3.zip --sha256 HASH_FROM_RECEIPT --output paper3-reanalysis.json
```

The output path must not already exist. The verifier reads ZIP members without
extracting or executing their contents. The outer hash must come from the
separate receipt. Internal hashes alone are not authentication of an artifact.
Recorded Windows paths are resolved through a finite manifest mapping to
packaged files; the verifier never accesses those original machine paths.

The command independently recomputes these quantities from saved inputs:

- The complete 25-case native airline matrix, its eight saved WAL files,
  eight equal-state cross-client groups, and six equal-response/different-state
  normal-versus-copy pairs. This includes the unadapted mapping control.
- Every state transition and signed ledger net for the 2,000-reservation retry
  census, using the unchanged public starting database as input. It checks
  all 10,000 cancellation states, 2,000 read results, the 2/4/8 ledger pattern,
  and the final-state equivalence of single cancellation and the read policy.
- The original published ZIP's 280 JSON records, 1,272 aggregate occurrences,
  224 distinct canonical aggregates, the 35-file event-prefix chain and the
  conservative structured-status screen. Recorded success does not become
  verified external success through this analysis.
- All 543 native retail paths: 423 direct cancellations and 120 two-operation
  compositions. It reconstructs every eligible order/payment alternative from
  the initial database and checks each returned order, affected payment-method
  state, exact ledger entry and per-method signed net. It verifies the full
  pinned retail source archive without executing it. Whole-database restoration
  remains a runtime assertion with equal recorded hashes, not a separately
  archived final full database.

Other probe reports and their saved raw MCP records are byte-verified and
available for inspection, but their framework execution, dependency identity
and assertion logic are **not reexecuted by this command**. See each report's
exact source revision, package versions, fixture choices and limitations.
The verifier's successful exit must not be described as replication of every
manuscript result. It does not import or trust the original measurement
functions for the four reanalyzed study components. Retained v1/v2 packages
cover the earlier three components; their historical scope is unchanged.

## What the archive preserves

The manifest lists every member's length and SHA-256, the exact manuscript
snapshot, declared path aliases and the verifier source. Existing reports
are preserved byte-for-byte, including their original absolute path strings.
The package also retains the frozen retry protocol and experiment/validator
scripts for inspection. Full native reexecution additionally requires the
upstream sources and dependencies named in those reports; several original
launchers use the research machine's explicit Python paths and are not
portable launch commands. This artifact does not claim otherwise.

The airline source data are the public synthetic tau2 benchmark database,
at commit `b7ea9074c1cba482b30687fecdb5c8425fd6f619`, under the accompanying
upstream MIT license. These records are not data from real airline customers.
Source: <https://github.com/sierra-research/tau2-bench>.

The included original RAC ZIP is unmodified. Attribution: Kaviru Hapuarachchi,
*Kavirubc/react-agent-compensation: ACMCAIS26-AE-1*, version 1.1,
<https://doi.org/10.5281/zenodo.19753969>. The preserved Zenodo metadata
declares CC BY 4.0: <https://creativecommons.org/licenses/by/4.0/>. Files inside
the original archive retain their own notices. Our reanalysis reports and
packaging are separate additions, not changes to the authors' artifact.

## Interpretation boundaries

No credentials, model weights, private task data or external service access
are needed. Checkpoint-dependent Agent task performance is outside this
artifact. The injected failures are controlled software experiments; counts
of probes are not independent defect counts or estimates of deployment
prevalence. The native cancellation contract is cancelled status plus zero
signed ledger net, not restoration of every field or proof of an external
refund. The original archive screen examines explicit immediate structured
status only. It cannot rule out missing, textual or silent failures.

## Later native retail composition extension

The retained v2 artifact predates manuscript section 5.8; v3 includes this
extension and its integrated portable reanalysis. The separate
source package `results/deploy/native-retail-composition-v1.zip` contains all
302 pinned tau2 source files, public retail database/policy, upstream license,
source manifest, frozen protocol, probe and measurement tests. On the designated
server the existing Python environment executed, from the extracted package:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python scripts/probe_tau_retail_payment_cancel_v1.py --output run
```

The output directory must not exist. Python 3.13.5, pydantic 2.13.5, loguru
0.7.3 and litellm 1.82.6 were recorded; other tau2 dependencies are required.
This is not a clean-environment dependency installer. The actual launch had a
120-second outer subprocess limit and completed in about 4.57 seconds.

The separate nine-member raw result archive, deployment receipt and execution
logs are pinned in `native_retail_composition_reanalysis_v1.json`. The repository
script `scripts/verify_tau_retail_composition_v1.py` recomputes its selection,
ledger and affected-state results without running native tools. It currently
expects the original source-data paths in this workspace; unlike the earlier
artifact verifier, it is not yet a standalone relocated package entry point.
The integrated v3 entry point above removes that workspace-path dependency
for offline reanalysis. Existing report files are created exclusively. Do not overwrite them or
count another audit as a new native experiment.

## Published retail trajectory screen

The separate `results/remote/retail-archive-composition-v1.zip` package contains
the four complete historical retail JSON files, frozen extraction protocol,
registration, analysis and independent verifier, original extraction output,
Git tree response, provenance receipt and upstream license. Its external
receipt is `research/evidence/retail_archive_composition_package_v1.json`.
Extract into an empty directory, then run from that directory with standard
library Python:

```sh
python scripts/verify_retail_archive_composition_v1.py \
  --audit results/audits/retail-archive-composition-v1.json \
  --output verification-new.json
```

To regenerate the extraction, run `scripts/audit_retail_archive_composition_v1.py`
with `--output extraction-new.json`. Outputs must not already exist. The
registration preserves the original local CRLF bytes; the verifier independently
checks that newline-normalized contents match upstream Git objects. This is
an archive analysis, not replay of historical models/tools or an observation
of persisted final states. The earlier v3 integrated package and review PDF
do not cover this later manuscript section 6.2.
