# Fixed-prompt executor sensitivity, complete 240-episode audit

This post-outcome control changes only the execution policy: accept a valid
multi-call generation and execute its calls in order, while keeping twenty
model attempts, twenty total tool attempts, the original single-call task
instruction, 512 output tokens and 32768 input tokens. It is not a new method,
an independent task replication, or the official hosted VAKRA agent.

All twelve workers exited zero; all 240 registered episodes are retained.
Archive: `results/remote/vakra-permissive-v1.zip`, 2006768 bytes, 294 members,
SHA256 `170148fc8f6500ed15925d6dd20cf7d9230a1d67741098df5a225650849a4521`.
Batch wall duration was 1630.0477 seconds. A model download overlapped part of
the run, so elapsed-time comparisons are not an isolated speed experiment.

The pairing audit verifies identical questions, database preparations,
ordered schemas, initial previews, model files, packages and first model
inputs. All 240 first replies are identical. Thirty-seven episodes diverge
only after model inputs change; no differing reply with the same logical
input was found before divergence. Tool-call IDs are ignored in this logical
comparison because the separately checked native templates do not render
them. Final text is identical in 213 pairs. Those answer labels are reused;
all 27 changed final answers were reviewed against the unchanged SQL cards.
Grounding labels are not inherited from text equality.

| Model / prompt | Strict final answers | Sequential final answers | Strict SQL-compatible | Sequential SQL-compatible |
|---|---:|---:|---:|---:|
| Qwen3 / original | 60/60 | 60/60 | 29/55 | 29/55 |
| Qwen3 / reminder | 60/60 | 60/60 | 32/55 | 32/55 |
| Qwen2.5 / original | 51/60 | 56/60 | 19/55 | 19/55 |
| Qwen2.5 / reminder | 49/60 | 56/60 | 21/55 | 22/55 |

The denominator 55 excludes only the five ambiguities identified before
outputs were inspected. It is a frozen SQL-interpretation subtotal, not a
claim that every included question is unambiguous. All sixty tasks remain
in execution reporting. In particular, books16 permits a competing grouped
advance interpretation and books19 has a highest-ID/job-level ambiguity;
neither is retrospectively removed. Labels are assistant-authored,
not independent human or official VAKRA scores.

Qwen2.5 produces twelve more final answers but only one net additional
SQL-compatible answer across the two prompts. Original prompt gains books15
(eight to three publishers) and loses cars10 (21.7 to unrestricted 24.8).
Reminder gains cars4 (no final answer to USA). Returning a final answer after
recovering from protocol errors is therefore not synonymous with solving
the task. The unchanged aggregate for the original prompt hides a gain and
a regression.

Under sequential execution, Qwen3 reminder remains 4/17 on student, 15/18 on
cars and 13/20 on books, versus original 4/17, 10/18 and 15/20. Qwen2.5
reminder is 4/17, 10/18 and 8/20, versus original 4/17, 8/18 and 7/20.
Both models have five wins and two losses across the 55 paired questions.
This remains a small, inspected-task descriptive comparison, not evidence
of a generally effective new controller.

Qwen2.5 protocol errors fall from 127 to 31, but tool attempts rise from 315
to 455; model attempts fall from 542 to 498. Input tokens fall from 6158394
to 5693901 and output tokens from 54925 to 53818. Different resource dimensions
move in opposite directions, so no unqualified efficiency claim is justified.
Eight sequential Qwen2.5 episodes still have no final answer, including
protocol, step and tool-budget terminations. Qwen3 remains at sixty final
answers per prompt and its score does not improve.

All summary counts, task pairing and annotation hashes were checked by the
committed analysis scripts against the complete raw archive. The recovered
template audit confirms supplied tool names are rendered for all three model
families. Generic one-or-more-functions wording plus a per-iteration
single-call instruction is not itself proof of a contradictory prompt.
