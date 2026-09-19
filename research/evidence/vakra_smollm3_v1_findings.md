# Complete third-model replication: SmolLM3-3B

This is an exploratory sensitivity result on the same 60 known public tasks,
not an independent test set or an official VAKRA score. All 240 registered
episodes were recovered; all twelve workers exited zero. Every final answer
was reviewed against the previously fixed SQL interpretation cards, with
absent answers scored incorrect. Five preidentified ambiguous tasks remain
in the execution totals and outside the 55-task SQL subtotal for each arm.

| Executor | Prompt | Final responses / 60 | SQL-compatible / 55 | Excluding qualified predictions | Final responses at 512-token ceiling |
|---|---|---:|---:|---:|---:|
| Single-call | Original | 54 | 0 | 0 | 12 |
| Single-call | Reminder | 58 | 1 | 0 | 21 |
| Sequential batches | Original | 54 | 1 | 1 | 15 |
| Sequential batches | Reminder | 55 | 4 | 3 | 18 |

The 221 final responses must not be interpreted as 221 solved tasks. Many
contain unexecuted tool plans, JSON-shaped proposals outside the native tool
envelope, or a procedure for calculating the answer. These do not supply the
requested answer. Across the four arms there are six correct annotations,
214 incorrect annotations and twenty ambiguous annotations. The remaining
19 executions terminate at a protocol-error limit (12), tool budget (5), or
step limit (2). No OOM, model error or input-budget termination is recorded.

Two correct annotations are explicitly qualified USA predictions on cars
task 004, one in each reminder arm. The text supplies the correct country
while suggesting future verification. The primary content-based rubric
credits the prediction without claiming observed evidence supports it. The
table also reports the sensitivity that removes both qualified predictions.
This prevents an unannounced confidence/grounding criterion from changing
the answer-correctness definition across models.

The other four correct outputs are the sequential-reminder answer to student
task 006, sequential-reminder answer to cars task 015, and both sequential
answers to cars task 017. No publishing output matches the fixed SQL answer.
The reminder has one paired win and no losses under single-call execution,
and three wins and no losses under sequential execution; these tiny counts
near the performance floor do not establish a robust prompt benefit.

The 120 executor-paired first replies are identical, as expected from the
unchanged first input and deterministic decoding. Sequential batches increase
executed tool calls from 49 to 307 and reduce protocol errors from 127 to 73
across the two prompts. That execution change is not sufficient for high
answer accuracy. A separate, unrelated two-turn infrastructure check had
already produced a valid native JSON tool call and the correct toy answer.
It establishes basic protocol operation, not benchmark competence.

Sixty-six final responses reach the 512-output-token ceiling. This is an
observed length flag, not proof that every such output was forcibly truncated;
the saved record does not retain the terminal token IDs. The fixed resource
budget and native no-thinking template are important constraints. This result
cannot rank the model generally, isolate a parameter-size effect, or serve as
strong independent confirmation of the scope-error hypothesis. The later
Qwen30B download overlaps part of this batch, so elapsed times are not an
isolated model-speed comparison.

## Reproduction and provenance

- Raw archive: `results/remote/vakra-smollm3-v1.zip`, 1,872,201 bytes,
  296 members, SHA-256
  `06bc88b55b5f97d4d81eac6f0d61e773d738a3bc0ad107e9a438c2f0d8802042`.
- Model: HuggingFaceTB/SmolLM3-3B revision
  `a07cc9a04f16550a088caea529712d1d335b0ac1`; all nine pinned files verified.
- Execution validation: `scripts/analyze_vakra_smollm3.py`, output
  `vakra_smollm3_v1_execution_summary.json` with per-artifact hashes.
- Review packets: `scripts/prepare_vakra_smollm3_review.py`; literal annotations
  produced by `scripts/record_vakra_smollm3_labels.py` after full-text review.
- Joined checks and counts: `scripts/summarize_vakra_smollm3.py`, output
  `vakra_smollm3_v1_answer_summary.json`. These are assistant-authored labels,
  not an independent human review. No hidden or discarded episodes.
