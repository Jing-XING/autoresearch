# RAC archival trace audit

Executed 2026-09-19 against the author's [Zenodo record 19753969](https://doi.org/10.5281/zenodo.19753969),
not the smaller current GitHub tree. The April 25, 2026 release is titled
`Kavirubc/react-agent-compensation: ACMCAIS26-AE-1`.

The downloaded ZIP has 13,843,052 bytes, 470 members, and SHA-256
`6faee4dedc04c242922d3b4fcf4bed5521e3b824d42ee1ad88c48be538d7cad4`.
Its official MD5 and all ZIP CRCs passed. The archive root is
`Kavirubc-react-agent-compensation-12e6678/`; this differs from the current
Git revision used in the software probes. The archive's recovery-manager
file also differs, so we do not silently assign the new-source execution
results to this older release. The adapter and interceptor files are byte
identical between these two checked releases.

`scripts/audit_rac_zenodo_archive.py` reads all 280 JSON members directly
from the ZIP. It executes no author code. The output
`rac_zenodo_archive_audit_v1.json` includes individual file hashes, schema
keys, record counts, repeated-record locations, and exact event-prefix checks.

## What the files establish

- There are 207 airline trace files, 60 REALM files, and 13 aggregate/progress
  files. These are file counts, not numbers of independent benchmark trials.
- Of the airline traces, 130 explicitly record a status: 110 `success` and
  20 `failed`. The remaining 77 have only a `steps` field; all have positive
  token counts. Their task success is not established by those token counts.
- Across the 13 aggregate/progress files, 1,272 record occurrences reduce to
  224 distinct canonical JSON records. This is exact content deduplication,
  not a claim that 224 independent executions occurred. The files include
  overlapping progress snapshots, two files with no result records, and repeated task grids.
- Thirty-five REALM files share the same recorded framework, task and start
  time. After ordering by event count, every shorter event list is an exact
  prefix of the next. Lengths span 24 to 3,866 events. Treating those files as
  35 independent trials would misrepresent the recorded execution history.
- The REALM collection is unequal across framework labels: 41 SagaLLM files,
  nine RAC files and ten files spread across four other labels. No pooled
  cross-framework success or token-efficiency comparison is computed here.

The aggregate records all contain `goal_satisfaction_rate=0.0`, while many
also record `success=true`. Without the corresponding evaluator semantics,
the zero field may be a default; it cannot be used to overturn the success
field. Likewise, `rollback_success=true` with an empty compensation-action
list does not prove that compensation was exercised. We preserve these
fields as recorded and avoid assigning an independent environment outcome.

## Error-status search: negative within its stated scope

Across all REALM event records, the audit checks for an event marked successful
whose immediate structured result explicitly sets `success=false`,
`isError=true`, or an error/failure status. JSON-encoded object strings are
decoded first. This bounded check finds **zero** contradictions.

That negative result must remain alongside the constructed RAC counterexamples.
The archive does not presently establish that the reproduced interface bug
occurred in these recorded runs. Textual errors, more deeply nested values,
silent no-ops and missing state are outside this check, and no compensation
postcondition was independently evaluated. The nine RAC compensation events
present in the collection are not a general sample of possible tool failures.

## Limits on reproducing the paper

The inspected [paper](https://arxiv.org/html/2605.03409v1), section 5,
reports repeated experiments and includes airline, retail and telecom
results. This archive contains an airline collection and selected REALM
material; it does not supply an immediately complete mapping to every reported
table row. Its progress and older/reference files should not be assumed to
be the exact final experimental sample.

The current GitHub `scripts/verify_traces.py`, read but not executed here,
infers a successful status for some legacy traces from positive token usage
and prefers successful files when multiple files share a task/framework key.
Those choices cannot establish an unbiased trial-level completion rate.
This is a limitation of that verification procedure; it does not establish
that the authors used it to compute the paper's published tables.

Decision: retain this archive as useful trace and provenance evidence, but
do not label the paper's performance independently reproduced. A replication
requires the actual trial identifiers, evaluator definitions, final sample
mapping and task-state checks. Existing CPU fixtures establish a narrower
software claim independently of the archival performance numbers.
