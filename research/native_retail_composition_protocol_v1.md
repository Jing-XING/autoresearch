# Native retail payment-change/cancellation composition, v1

Freeze before executing any retail mutation. Source inspection motivates this
diagnostic: cancellation iterates every ledger entry, while changing payment
adds a payment and a refund. This is a source-derived hypothesis, not a blind
discovery trial, representative agent workload, or measurement of real refunds.

Pin tau2 b7ea9074c1cba482b30687fecdb5c8425fd6f619 and the existing canonical
source manifest. Execute all unchanged native source imports. Use the complete
public synthetic retail database (1000 orders, 423 initially pending), without
task instructions, benchmark reference answers, or models. The native retail
policy permits changing a pending payment while retaining pending status, and
permits subsequent pending-order cancellation. Simulated authorization for each
operation is assumed; this is a tool-level probe, not a dialogue-policy test.

Eligibility: initially pending orders with exactly one positive payment and a
known original payment method. Retain every excluded order with its reason.
For every eligible order execute one cancellation-only control. Then, independently
from the original state, execute payment change followed by cancellation for
every different stored payment method allowed by the native preconditions,
including enough balance for a new gift card. No selecting a favorable pair.
Record orders without eligible alternatives. Each composition has two native
calls; the state after the first is the payment-change control. No injected
errors or retry mechanisms. Exceptions remain recorded, stopping that path,
and invalidate successful-run reporting rather than removing the case.

Use decimal arithmetic to score the ledger, with payments positive and refunds
negative, grouped by payment method. The explicit cancellation contract requires
cancelled status, zero net ledger per method, and gift-card balances equal to
the initial balances plus the original payment amount for an original gift
card. Other gift cards should return to their initial balances. Permit 1e-6
numeric tolerance only for stored gift-card float rounding. Distinguish this
contract from status-only success and exact history restoration. Do not infer
an external credit-card refund or financial harm from synthetic ledger values.

Record full affected order and payment-method state before and after each call,
returned payloads, exceptions and contract components. Reset the affected order
and user before each path; verify the whole model database hash is restored at
the end. Count unique orders and order/alternative pairs separately because
several pairs share the same initial order. No independence-based confidence
intervals or real-world prevalence estimate from the exhaustive finite fixture.

Run on the designated Linux server using its existing environment, offline,
one numerical thread, with a 120-second outer process bound. Preserve exact
source/data/protocol hashes, raw records, runtime, stdout/stderr and exit status.
The purpose is to test whether ordinary native operation composition can meet
a status check while failing the declared ledger contract. This is distinct
from transport error handling and does not rank compensation frameworks.
