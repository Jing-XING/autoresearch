# Complete fixed-prompt replication: 240 executions, 60 task identities

All twelve workers exited with code zero. The complete archive has 291 files,
1,949,762 bytes, SHA-256
`3371716f13ecddd01f9261f6045cbe7440243f5254d8beb8248c19ad7afbd82f`.
The previously recovered 184 run files match the final archive byte-for-byte.
The batch took 1,740.05 seconds across three sequential four-worker waves.
No registered task was removed or rerun.

The execution auditor checks all 240 cases, task order, preparation hashes,
model weights, source/runtime consistency, fixed budgets, actual initial
prompts and schemas, and per-trace token/call accounting. All checks pass.
Original and reminder differ by the fixed suffix only within each pairing.

## Answer audit

All answers were read against the pre-output SQL cards and policy. Labels
are assistant-authored, not independent human annotation or official VAKRA
scores. The principal subtotal excludes the five preidentified ambiguous
tasks but retains all failures, reference conflicts and initialization
witnesses. It contains 55 task identities, not 220 independent samples.

| Domain | Model | Original | Reminder | Fixed SQL subtotal | Gains | Losses |
|---|---|---:|---:|---:|---:|---:|
| computer_student | Qwen3 | 4 | 4 | 17 | 0 | 0 |
| computer_student | Qwen2.5 | 4 | 4 | 17 | 0 | 0 |
| cars | Qwen3 | 10 | 15 | 18 | 5 | 0 |
| cars | Qwen2.5 | 9 | 9 | 18 | 1 | 1 |
| book_publishing_company | Qwen3 | 15 | 13 | 20 | 0 | 2 |
| book_publishing_company | Qwen2.5 | 6 | 8 | 20 | 3 | 1 |
| Combined | Qwen3 | 29 | 32 | 55 | 5 | 2 |
| Combined | Qwen2.5 | 19 | 21 | 55 | 4 | 2 |

These are descriptive fixed-interpretation counts. The JSON field
`clear_interpretation_n` denotes this frozen subtotal; it does not establish
that every included natural-language question is unambiguous. In particular,
publishing task 19's phrase "highest employee" also admits an employee-ID
reading. This concern was recognized after reading model answers and is
disclosed without changing the preregistered denominator or labels. Under
the frozen highest-job-level reading all four answers fail. Field glossaries
used offline were not supplied to the agent, so these counts do not isolate
reasoning ability from missing domain semantics.

The reminder improves Qwen3 on five car queries but loses two publishing
answers: it mismatches the highest price with a book title and replaces a
complete title/sales list with three rows and an ellipsis. Qwen2.5 gains the
CEO question under the independently checked SQL interpretation; the released
reference instead asks its program for the CFO. Reference compatibility and
semantic answer correctness therefore differ on this case.

## Execution and cost

| Model/prompt | Final answers / 60 | Protocol limit | Step limit | Model calls | Input tokens | Output tokens | Generation seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3 original | 60 | 0 | 0 | 229 | 2,817,759 | 30,036 | 1,401.22 |
| Qwen3 reminder | 60 | 0 | 0 | 207 | 2,464,139 | 26,916 | 1,233.76 |
| Qwen2.5 original | 51 | 8 | 1 | 277 | 3,078,581 | 28,105 | 1,466.80 |
| Qwen2.5 reminder | 49 | 10 | 1 | 265 | 3,079,813 | 26,820 | 1,434.08 |

No episode terminates for input length or a model exception. Five final
generations reach the 512-token ceiling, including all three produced car-name
enumerations. A final response remains distinct from a complete or correct
answer. Generation time is not energy consumption or isolated deployment latency.

There are 128 protocol-error events: 99 local multiple-call rejections,
19 unknown tool names and ten incomplete tool-call blocks. These are events,
not independent failed episodes. A complete CPU diagnostic replays the first
multiple-call rejection in each of 32 affected episodes, preserving the
recorded prefix and using unchanged arguments. Thirteen batches execute
without a tool error; 32 of 93 calls across the other batches fail. Neither
call executability nor these replays establish answer correctness or the
outcome of a batch-enabled agent. The current single-call adapter is a
material experimental limitation and is not the default official agent.
The unchanged upstream system prompt itself requests one call per iteration;
multiple emitted calls therefore also violate the instruction. Runtime
permissiveness must be tested separately, not assumed to explain all failure.

## Reproduction and scope

Run `analyze_vakra_crossdomain.py`, `prepare_vakra_crossdomain_review.py`,
the explicitly authored label-recording scripts, and
`summarize_vakra_crossdomain_answers.py` against the verified raw archive.
The summaries validate raw hashes and the unchanged pre-output policy/cards.
Outputs are created exclusively to preserve earlier artifacts. The rejected
batch diagnostic requires the prepared local VAKRA runtimes and MCP environment.

Selection favored the three smallest previously unused databases; the data
are public training queries, not guaranteed absent from model pretraining.
The two checkpoints share the Qwen family. Report every domain; do not select
the favorable car result as a universal method improvement. A new controller,
independent architecture, stronger executable baselines and appropriate
uncertainty remain necessary for a submission-ready paper. The study does
not establish a new algorithm or complete any of the five-paper goal.
