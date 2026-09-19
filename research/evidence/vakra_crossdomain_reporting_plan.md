# Reporting rules fixed before model-answer inspection

The registered experiment has 60 task identities and 240 executions. The
four executions of a task are paired observations, not four independent
questions. Database selection is deterministic and favors small databases;
it does not support inference to all VAKRA domains or arbitrary agent tasks.

Report every execution, including missing answers, protocol failures and
input-limit terminations. For each domain and checkpoint report both prompts,
their matched gains and losses, and actual resource use. Keep the five
preidentified ambiguous questions in execution totals and report their
interpretations separately. The principal SQL-interpretation subtotal has
55 questions per prompt and checkpoint: 17 student, 18 cars, 20 publishing.
Reference conflicts and the two conditional initialization witnesses remain
in this subtotal; also expose their outcomes separately without silently
changing its denominator.

Annotation is an assistant-authored qualitative audit, not independent human
validation or the official VAKRA judge. Every label must retain its reason,
task identifier, raw-artifact hash, and the frozen policy and SQL-card hashes.
Correctness requires satisfying the requested fields and completeness, not
merely containing an expected substring. A missing final answer cannot be
correct. Reference compatibility is a separate label. Ambiguous questions
receive no forced single semantic-correctness label.

Do not combine overlapping error counters, treat a final response as success,
or treat correct answers as mechanically established grounding. Report all
three domains rather than selecting the strongest result. Do not tune the
prompt or rerun failures within this batch. Any changed budget or method is
a new, separately recorded experiment.

Primary reporting is descriptive paired counts and percentage-point changes.
Avoid a confirmatory p-value claim from this convenience sample. If exploratory
uncertainty intervals are added later, state that they are conditional on
these tasks and preserve task-level pairing across both model families; do
not bootstrap the 240 executions as independent samples. Qwen3 and Qwen2.5
are two checkpoints in one model family, not independent architecture families.

No model final answers or outcome labels had been inspected when this file
was written. Only process state and completed-artifact counts were observed.
