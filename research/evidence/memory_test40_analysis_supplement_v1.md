# Pre-outcome memory tie sensitivity analysis supplement

Recorded 2026-09-19, while the test40 batch waits for the frozen VAKRA queues.
No test40 model outputs have been collected or inspected. This supplements
the descriptive analysis; it does not change tasks, source choices, prompts,
weights, inference budgets, or the primary boundary-minus-full comparison.

The original registration fixes 40 targets and three source choices at exact
retrieval ties. Each choice reuses five sources across target groups of sizes
13, 3, 8, 1 and 15. Thus 560 episodes are not 560 independently sampled tasks,
and the three deterministic tie rules are not random source-population draws.

After the complete-grid audit, `autolab/memory_tie_sensitivity.py` reports:

1. Boundary-minus-full success differences for every checkpoint and each
   of the three choices separately. The task-weighted value remains primary.
2. Equal-visible-ticket-group weighting as a secondary descriptive estimand.
   Giving each of five groups equal weight changes the target distribution;
   it is not a correction that supersedes the primary value.
3. Leave-one-visible-ticket-group-out differences. With only five shared
   groups, these diagnose concentration and are not confidence intervals or
   evidence of generalization to an unseen family population.
4. All three pairwise tie-rule comparisons within each curation condition,
   reporting changed outcomes, gains and losses. No best tie rule is selected.

Errors remain unsuccessful in every calculation. The single no-memory control
continues to be reported by the main analyzer and is not copied into new
independent observations. Ticket groups come from the frozen registration,
not labels chosen after observing success. The analysis fails on missing or
duplicate treatment cells and changed ticket groups.

Three CPU tests check unequal group weighting with retained errors, opposite
effects under different tie rules, and rejection of invalid grids. They pass.
These small fixtures verify arithmetic and input checks only; the full
560-episode analyzer has not yet been validated against completed new data.
The main result will record hashes of all three analysis source files.
