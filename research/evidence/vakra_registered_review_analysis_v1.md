# Complete-grid review and aggregation

Prepared on 2026-09-19 while the capacity batch was still running. No capacity
or expansion answer was inspected when this aggregation implementation was
written. This note describes analysis plumbing, not new neural results.

The existing execution auditor first verifies the registered 120- or
420-episode grid, deployment archive, task identities, model/source hashes,
budgets and initial prompt pairing. `prepare_vakra_registered_review.py`
then emits complete answer packets and pending labels. Semantic correctness
still requires review against the previously frozen SQL cards; the scripts
do not turn string containment or final-response presence into correctness.

After the complete review, `summarize_vakra_registered_answers.py` checks the
execution-summary/card/policy hashes and every raw episode hash again. Its
shared module rejects missing or duplicate labels, unfinished reviews, changed
interpretation masks, stale sources and correct labels attached to absent
answers or incomplete executions. Failed episodes remain in the scored
denominator. Ambiguous tasks stay in execution, termination and cost totals.
It reports each model and domain separately, with task-paired gains, losses,
both-correct and both-unsuccessful identities. It does not add a significance
test, a grounding score or a new exclusion criterion.

The fixed primary denominators remain 55 of 60 tasks per capacity arm and
49 of 70 per expansion arm. Aggregate accuracy weights each scored task once.
Answer-length hits do not remove tasks. Conditional descriptive uncertainty
and any later sensitivity analysis must remain separately identified.

Five actual unit tests pass, covering failure retention, ambiguity-cost
retention, incomplete grids/reviews, changed masks/provenance and a false
correct label on a failed execution. An additional local regression applies
the module to the existing 240-episode sequential-executor review. The old
schema is normalized only by adding its known model list, sequential policy
and task indices from the frozen policy. All 16 grouped label/count results
and eight paired task partitions exactly match the earlier saved summary.
No old label is changed and no new outcome is generated. Full capacity and
expansion executions of the new command remain pending.

Commands, from the repository root:

```text
python -m unittest tests.test_vakra_review_summary -v
python scripts/summarize_vakra_registered_answers.py --root RAW_RUN_ROOT --summary VERIFIED_EXECUTION_SUMMARY --annotations COMPLETED_REVIEW --output NEW_ANSWER_SUMMARY
```

The output is descriptive assistant-authored evaluation, not an official
VAKRA score or independently adjudicated human annotation.
