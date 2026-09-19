# Archived retail composition audit, v1

Frozen before extracting composition occurrences or inspecting cancellation
payloads. This is a source-selected descriptive audit, not preregistration of
a novel hypothesis: the native payment-change/cancellation mechanism is already
known from the completed diagnostic census. Earlier repository-wide work read
archive structure, task/trial coverage and reward totals. This audit additionally
inspected field names only before freezing this protocol.

## Population and provenance

Include all four `data/tau2/results/final/*_retail_*.json` files in the existing
tau2 repository snapshot, with the exact SHA-256 values in the accompanying
registration. Each contains 114 tasks and 456 simulations. Inventory equality
is required, not just verification of selected files. The snapshot revision is
`b7ea9074c1cba482b30687fecdb5c8425fd6f619`; recorded execution revisions are
reported separately. Their runtime is not assumed equal to the current native
census runtime. Archive bytes and registration are checked before extraction.

## Fixed extraction and measurements

1. Enumerate every simulation; require unique simulation IDs and unique
   `(task_id, trial)` within each file. Report canonical simulation duplicates
   across files separately; do not pool model runs as independent tasks.
2. Read assistant tool calls only. Associate a result by tool-call ID within
   the same simulation and require its message to follow the call. Reused IDs,
   missing results and multiple results are recorded as unresolvable; never
   silently choose one. A tool error is retained, not discarded.
3. Extract every `modify_pending_order_payment` and `cancel_pending_order`
   call, including failures. For each cancellation, record all earlier
   payment-change calls with an identical `order_id`. A qualifying observed
   composition additionally requires a change result before the cancellation
   call, both `error == false`, parseable JSON order objects with matching IDs,
   pending status after change and cancelled status after cancellation. Report
   same-message calls without established result-before-call ordering separately.
4. For every cancellation result that is a parseable matching cancelled order,
   independently compute signed payment-minus-refund totals per payment method
   using Decimal. Missing/invalid histories, unknown transaction types and
   negative or nonfinite unsigned amounts are unscorable, not successful.
   Report exact zero/nonzero totals, entry counts, tool error flags and the
   archive's original reward without changing that reward.
5. Preserve each selected call/result and source message indices in an
   inspectable output. Report per-file and total denominators: simulations,
   calls, matched results, ordering candidates, qualifying compositions,
   scored cancellation payloads and nonzero-net payloads. Report distinct tasks
   alongside occurrences. Analyze zero occurrences as a legitimate outcome.

## Claim boundaries

Tool-return payloads are observations, not independent persisted-state
snapshots. Nonzero ledgers in them do not prove external payment effects or
the historical runtime's final database state. The archived reward is not an
accounting invariant and is not relabelled. No policy authorization judgement,
new model execution, native replay or benchmark-score revision is included.
This audit cannot infer population failure prevalence outside its four fixed
files. Native-current and historical-archive evidence stay separate even if
their payload patterns match. If no qualifying composition is found, the
native counterexample remains a constructed/source-selected diagnostic.
