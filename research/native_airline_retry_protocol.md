# Native cancellation retry census

Registered 19 September 2026 before execution. This extends the completed
two-profile compensation study with a census of the pinned native airline
database, without accessing agent task solutions or running models.

The population is every reservation in tau2-bench commit
`b7ea9074c1cba482b30687fecdb5c8425fd6f619`,
`data/tau2/domains/airline/db.json`. Read-only input inspection found 2,000
reservations, all with one payment-history entry and an unset status. This
is a homogeneous public fixture population, not 2,000 independent agent tasks
or a representative sample of real payment systems.

For each original reservation, reset that reservation to its original value
before each of three diagnostic policies. Use unchanged native tool methods:

1. Single cancellation: call cancel_reservation once, save final state.
2. Bounded blind retry: call cancellation three times in total. After each
   native return, impose an acknowledgement exception in the experiment
   harness. Record each returned native payload before the imposed exception.
3. Read before retry: call cancellation once, impose the same acknowledgement
   exception, then call the native get_reservation_details. If status is
   cancelled and the Decimal-valued payment ledger sums to zero, stop. Otherwise
   record an unmet contract; do not invent another fallback policy.

These are direct native calls. They do not exercise MCP, a recovery framework,
a remote payment service, concurrent writers, or an autonomous model. The
experimenter-supplied observer has authoritative synchronous access by
construction. It is a diagnostic upper-bound control, not a new algorithm.

Record every target's initial state, each cancellation payload/final state,
observed read payload, imposed errors, native call counts and state hashes.
Record whether the narrow cancellation contract holds, full target-state
equality to single cancellation, number of ledger entries, signed ledger net,
and separately summed positive and negative amounts. Gross ledger entries
are not external charges or refunds. Never infer financial loss from them.

Source inspection predicts payment-history doubling on each cancellation,
while signed net remains zero after the first cancellation. Therefore strict
state idempotence and satisfaction of the narrow status/net contract need not
agree. Test this prediction over the full population, retaining every failure.
No task success rate, statistical significance or framework ranking is planned.

Save an immutable JSONL with all 2,000 records plus summary/runtime/source
hashes. Independently validate against the original input database by computing
the expected append-negation transformation and checking each state field,
population coverage, payload/final equality and method counts. Verify the
shared database is restored to its initial state after all target resets.
Retain partial attempts if execution fails; no output file is overwritten.
