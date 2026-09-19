# Passive lineage instrument: scope and limits

`autolab/tool_evidence_ledger.py` consumes an initial public preview, tool
names and actual call/response pairs. It has no database path, reference
answer, user-query parser or model access. It does not change agent behavior.
This is an analysis instrument, not yet a proposed controller or novel method.

The ledger records each handle's cardinality, direct preview/getter coverage,
explicit filter chain and sort order. A new branch inherits only its actual
input handle's predicates. Unknown transformations intentionally discard
known lineage. A successful switch to a different universe invalidates old
handles. Error flags, explicit validation-error text and error objects cannot
add evidence. Full-column getters are recognized only by the pinned upstream
`get_{column}s` convention and the exposed tool-name set; returned length must
match the handle cardinality before marking the direct column observation
complete. These claims assume the recorded upstream tool semantics are sound.

Six unit tests exercise incomplete previews, independent branches, errors
with false flags, unknown transformations, universe invalidation, empty
results and wrong-length getters. The entire local suite passes 53 tests
with eight optional tau dependency skips (61 discovered).

`scripts/audit_vakra_observed_lineage.py` processed all 48 raw episodes without
executing any tool. The 138 recorded results include 127 observed payloads
and eleven errors: ten flagged MCP errors and one additional validation-text
error with a false flag. This is a count of these traces, not a general error
rate. Each row in `vakra_coverage12_v1_observed_lineage.json` includes the source
hash and the ledger snapshot; the implementation hash is also recorded.

Direct checks on real traces confirm:

- Qwen2.5 reminder case 004's final handle inherits Estonia and Estonian
  restrictions, but not the percentage threshold applied on another branch.
- Qwen3 reminder case 002 has four rows and only a three-value language
  preview, without a full language getter on that handle.
- Qwen3 original case 002 had already obtained complete language and country
  code columns on its parent handle. Therefore a partial later preview does
  **not** prove that the whole history lacks enough information: aligned
  parent columns may support reconstruction of the filtered answer.

This last counterexample is essential. The instrument records direct
per-handle observations; it does not reason over all relationships among
previous columns. It cannot be used as a general semantic sufficiency score,
an automatic hallucination label, or a guarantee that the user request was
translated correctly. Answer correctness, direct coverage and full-history
identifiability remain distinct. Any intervention built on this instrument
requires a separately frozen protocol and real model comparison against the
already beneficial simple reminder and stronger executable baselines.
