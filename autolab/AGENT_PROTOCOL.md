# Generic autoresearch protocol

This protocol separates **research decisions** from **experiment execution**.
The agent proposes one falsifiable change at a time; `autolab.runner` provides
the repeatable execution and measurement layer.

1. Read `research.json` and the task's fixed evaluator.
2. Establish a baseline without changing the task or evaluator.
3. Form one hypothesis and change only files listed in `editable_files`.
4. Commit the candidate change before running it.
5. Run one bounded command through `autolab.runner`.
6. Keep the commit only when the first (primary) metric improves (or the
   change is a justified simplification). Secondary metrics are diagnostics or
   constraints; they never override the primary objective. Otherwise reset to
   the previous commit.
7. Inspect the saved log and `results.jsonl` before proposing the next idea.

The runner never invents a metric, silently ignores a crash, or edits Git. That
keeps acceptance decisions visible and lets the same loop work for NLP, vision,
simulation, systems benchmarks, or scientific code.
