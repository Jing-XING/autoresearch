# Retail refund-iterator intervention, v1

This is a follow-up causal control for P3's source-selected retail composition
diagnostic, not a fifth paper, new recovery algorithm, agent experiment or
blind discovery. Freeze this protocol and code before executing the new census.
The earlier 423 direct and 120 composed paths and their outcomes are already
known. The hypothesis is specifically about cancellation's iteration over an
unsigned payment/refund history, not an estimated deployment failure rate.

Use the same complete public synthetic database, pinned tau2 source revision
b7ea9074c1cba482b30687fecdb5c8425fd6f619, 423 initially eligible pending orders
and all 120 allowed order/alternative-payment pairs across 102 orders. Preserve
the original selection and exclusions, state reset, declared cancellation
contract and float tolerance. There are 543 paths per implementation. All
three implementations execute each path from exactly the same initial state:

1. Native: the unmodified cancellation method.
2. Payment-only: replace its history iterator with entries whose transaction
   type is payment; keep their original positive amounts. This is an explicitly
   constructed incomplete repair control, not a literature baseline.
3. Net-by-method: replace the iterator with one synthetic positive payment entry
   per instrument with a strictly positive outstanding signed balance. Compute
   that balance as payments minus refunds using decimal arithmetic. Omit zero
   balances and reject a negative balance before any mutation rather than
   claiming to repair an already over-refunded history.

For both interventions, change only the single For.iter AST expression in a
research copy of the original method. Reverting that expression must exactly
recover the original AST. Preserve native status/reason checks, refund-entry
creation, gift-balance updates, cancellation status and returned object.
Record both AST hashes and the transformed method text. Preserve all original
source files and the original class method. These are local diagnostic variants,
not modifications to the benchmark or claims of upstream-maintainer acceptance.

Run 1,629 paths and an expected 1,989 method calls (663 per implementation).
Exceptions remain records and invalidate completed-run reporting. For every
path retain initial affected state, every argument and return, post-call order
and payment-method states, and the original explicit contract measurements.
Check exact equality of each payment-change prefix across implementations and
of direct-cancellation results across implementations. The native arm must
match the earlier immutable census at the saved-state level. Retain any mismatch;
do not select matching records or rewrite the older census.

Primary diagnostic outputs: cancellation contract pass counts for the two path
types per implementation; final old/new instrument signed net; gift-balance
deviation from the unchanged cancellation target; and appended ledger length.
Expected mechanism (hypothesis, not measured result): native composed old-method
net -2A, payment-only -A, net-by-method zero. The gift-card discrepancy should
follow that same reduction where the original payment used a gift card. A
successful net-by-method intervention would localize this mechanism under the
declared synchronous fixture, not establish correctness for all histories,
concurrency, external settlement, approval policy or distributed atomicity.

Execute on the designated Linux host, CPU only, one numerical thread, with a
120-second outer bound and no network connections from the experiment process.
Preserve stdout/stderr, runtime, dependencies, hashes and exit status. Package
all resulting records for independent offline arithmetic/state comparison.
No model task, benchmark score, original archived run, user database or GPU
queue is altered. These paths share the same source mechanism and starting
orders; report finite paired counts without an independence-based confidence
interval or statistical significance claim.
