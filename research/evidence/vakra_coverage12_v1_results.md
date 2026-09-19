# Matched VAKRA prompt control: complete development results

All 48 registered episodes finished; four workers exited zero. This does not
mean all questions were answered correctly. The frozen protocol is
`vakra_coverage_control_protocol.md`. Two Qwen checkpoints, one world database,
twelve public training inputs, two prompts; no outcome-based reruns.

## Execution and answer audit

| Checkpoint | Prompt | Final response / 12 | Input ceiling / 12 | Protocol limit / 12 | SQL-compatible answer / 11 clear-interpretation tasks |
|---|---|---:|---:|---:|---:|
| Qwen3-4B-Instruct-2507 | Original | 6 | 6 | 0 | 3 |
| Qwen3-4B-Instruct-2507 | Coverage reminder | 10 | 2 | 0 | 9 |
| Qwen2.5-7B-Instruct | Original | 9 | 2 | 1 | 4 |
| Qwen2.5-7B-Instruct | Coverage reminder | 9 | 2 | 1 | 6 |

The last column is **assistant-authored qualitative annotation**, not the
official VAKRA score or independent human evaluation. Frozen SQL audit cards
preceded these outcomes. The task asking for the country with the "highest
capital" is ambiguous: the released answer orders a numeric city identifier.
It remains in all execution counts and is reported separately for reference
compatibility. Only Qwen2.5 with the reminder matches that interpretation;
its actual successful branch still omits the official-language restriction.
The "most crowded city" question is interpreted as maximum population, as in
the reference, and its head-of-state answer concerns the historical database.
Absence of an answer counts as failure in the eleven-task subtotal.

Within those eleven tasks, the reminder has six gains and no losses for Qwen3,
three gains and one loss for Qwen2.5. These are development comparisons over
eleven paired task identities, not independent samples for every episode.
The first four tasks informed the reminder. No significance test is offered
as confirmatory evidence and the prompt is not a novel method.

## Mechanisms and counterexamples

Qwen3 replaces several unfiltered getters with server-side min/max followed
by equality filtering. This allows the most-populated-city, smallest-country
and smallest-city questions to proceed within the input ceiling. It still
omits Uzbek from a four-row Turkmenistan handle after seeing a three-value
preview. The reminder therefore does not eliminate the originally observed
coverage error. Its highest-life-expectancy answer is correct, but the trace
only observes three of four language rows: correctness alone does not certify
that no additional official language exists in the unobserved row.

Qwen2.5 fixes the England count, the Turkmenistan language set and the
most-populated-city answer. It regresses on the five-English-countries task:
after only a contains-English filter it lists Aruba and Netherlands Antilles,
which fail the database's official-English condition. Its Baltic-language
answer follows only Estonia, discarding a previous percentage-filtered branch
and missing Lithuania. These are predicate/lineage failures despite successful
tool responses. They motivate testing actual scope tracking, not assuming
that a stronger warning has solved the problem.

MCP error flags are also incomplete diagnostics. Qwen3 original case 007
receives the text `Input validation error: 'City_Population'` with
`isError=false`. The execution analyzer reports both flagged errors and
explicit validation-error payloads; the categories overlap and are not added.
Original/reminder flagged counts are Qwen3 0/0 and Qwen2.5 8/2. Validation-text
counts are Qwen3 1/0 and Qwen2.5 8/2.

## Resource accounting

| Checkpoint | Prompt | Model-call attempts | Input tokens processed | Output tokens | Generation seconds |
|---|---|---:|---:|---:|---:|
| Qwen3 | Original | 51 | 831487 | 4463 | 299.21 |
| Qwen3 | Reminder | 52 | 879648 | 5808 | 353.06 |
| Qwen2.5 | Original | 53 | 730693 | 6710 | 359.01 |
| Qwen2.5 | Reminder | 46 | 593751 | 4777 | 265.58 |

Batch wall time was 390.01 seconds with four concurrent workers. Call attempts
include over-budget rejections; token totals describe completed generation
calls. A rejected over-budget input is recorded in the trace but has no
generated tokens. Generation time is not
energy use. Qwen3's improvement did not reduce total processed tokens or
generation time, so a blanket efficiency claim would be incorrect.

## Provenance and reproduction

Raw archive: `results/remote/vakra-coverage12-v1.zip`, 1001286 bytes, 67 files,
SHA256 `7b566b93add4f5c23ce594ae5a16b24a0d621e65586f3aa9fee1641db39f5a84`.
All archive paths were checked before extraction into a new directory. The
first transfer rejected a transcribed hash mismatch without creating a file;
the corrected transfer passed. No episode data were modified.

Run `scripts/analyze_vakra_coverage_control.py` with the extracted
`runs/vakra-coverage12-v1` root and a fresh output path. It verifies checkpoints,
runtime, task order, actual initial prompts, tools and observations across the
matched conditions. `vakra_coverage12_v1_summary.json` records every response,
termination and raw-file hash. Qualitative labels and their reasons are in
`vakra_coverage12_v1_answer_annotations.json`; the corresponding
`scripts/summarize_vakra_semantic_audit.py` validates all 48 raw hashes and
reproduces `vakra_coverage12_v1_answer_audit_summary.json`.

These results justify retaining the reminder as a strong simple control and
studying the remaining scope/coverage failures. They do not establish a new
method, generalization to another database, or a submission-ready paper.
