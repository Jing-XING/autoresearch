# Offline evidence artifact for the recovery-interface study

This accompanies an **incomplete working manuscript**. It supports byte-level
inspection and offline reanalysis. It is not a new experiment, a reproduction
of published model scores, or a certificate of publication readiness.

## One-command reanalysis

Use Python 3.10 or later, with no additional packages, GPU or network access.
Obtain `paper3-offline-evidence-v2.zip`, its SHA-256 from the accompanying
`paper3_offline_artifact_receipt_v2.json`, and
`scripts/verify_paper3_offline_artifact.py` from this repository. Run:

```text
python scripts/verify_paper3_offline_artifact.py paper3-offline-evidence-v2.zip --sha256 HASH_FROM_RECEIPT --output paper3-reanalysis.json
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

Other probe reports and their saved raw MCP records are byte-verified and
available for inspection, but their framework execution, dependency identity
and assertion logic are **not reexecuted by this command**. See each report's
exact source revision, package versions, fixture choices and limitations.
The verifier's successful exit must not be described as replication of every
manuscript result. It does not import or trust the original measurement
functions for the three reanalyzed study components.

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
