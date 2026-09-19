# Independent database replication of the fixed simple prompt

Frozen 2026-09-19 before downloading the selected task inputs, references or
databases and before observing any model outcome on these domains.

This tests transfer of the already fixed coverage reminder. It does not test
a new method and is not an official VAKRA submission. The world development
results are excluded from this replication's performance subtotal.

Selection is resource based, not outcome based: among the pinned dataset's
33 public capability-1 training input domains, exclude world and take the
three smallest SQLite files by declared byte size, breaking ties by path.
The complete 613-entry database tree at revision
1388b9f1aaed887a73957eba651a6c2034010476 has no next page. This rule selects
computer_student (45056 bytes), cars (135168), and book_publishing_company
(184320). All task inputs and answers in these domains are uninspected at
registration. Selecting small databases limits generalization to large data.

Use the first min(20, available input count) tasks in each domain's released
order, retaining every selected task and failure. Compare the unchanged
original prompt against the exact coverage_check suffix from revision
vakra-v3/commit 40ebd5f. Use the same two checkpoints, native greedy template,
20 model-call attempts, 512 new tokens and 32768 input-token ceiling. Do not
adjust the prompt, replace difficult tasks, or silently repair tool schemas.
No passive-ledger message is added. The ledger remains offline instrumentation.

Preparation may derive the prescribed initial table/join from reference code,
as in the official setup. Neither reference programs nor answers enter the
model runtime. Before GPU execution, audit reference compatibility and input
coverage. Infrastructure failures do not justify dropping the domain; record
them and resolve compatible setup errors before a frozen run, or preserve
unsupported cases explicitly. Record exact runtime changes if any are needed.

All registered outcomes and model-call usage are reported. Answer evaluation
must disclose its interpretation, ambiguities and annotation method. Reference
replay success is not agent success. Official VAKRA scoring requires its actual
documented judge pipeline; absent that pipeline, report a named offline audit
without calling it an official score. Do not tune a judge on the prompt's gains.

Database-level results are primary descriptive units; paired task effects and
uncertainty are secondary and must retain the clustered structure. Three
selected databases cannot establish broad enterprise-agent generalization.
Any new controller or executable baseline needs a separate protocol and must
not borrow the replication's independence after outcomes inform its design.
