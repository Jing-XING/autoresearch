# Price-association control: no new correct-answer witness

All eighty existing car episodes from the two Qwen checkpoints and two
sequential-executor prompt conditions were replayed. The declared synthetic
world class swaps the prices of two existing cars, preserving every other
cell, all positive price values and their multiset, row counts, declared keys
and foreign keys. This avoids the earlier geography-changing intervention,
but admissibility still depends on allowing price-car associations to vary.
It does not assert anything about historical market prices.

For each of the twenty known tasks, a fixed seeded proposal stream generates
at most 2,048 price pairs. The first eight answer-changing swaps are retained,
or fewer if the proposal limit is reached. Candidates use only the database
and previously fixed SQL; no trajectory is inspected to choose a swap. The
bounded pool contains 99 distinct task-specific mutant databases.

All eighty original replays match. Across 332 mutant replays, ten episodes
have an answer-changing, full-target-observation-preserving witness; search
stops at the first witness for an episode. **All ten already had incorrect
answers under the fixed interpretation.** There is no new witness among the
43 SQL-compatible correct-answer episodes. The remaining labels are 27
incorrect, two absent answers and eight ambiguous. The ten witnesses cover six task indices
(003, 009, 010, 014, 016, 018) and include wrong absence claims, a partial
weight list, and aggregation on an unrestricted population.

This is a negative result for extending the correct-but-unsupported cases
with this particular mutation class. It is useful evidence against reporting
all witnesses as failures of otherwise correct agents. Failure to find a
witness is not a sufficiency certificate: the grammar changes only prices,
samples at most 2,048 pairs and retains at most eight per task. Seven tasks
have no answer-changing candidate at all under the sampled price class.
The 80 repeated executions are not 80 independent tasks, and 10/80 is not a
general unsupported-answer prevalence estimate.

Reproduce with `scripts/audit_vakra_price_swaps.py`, which invokes the unchanged
full-observation replay in `scripts/audit_vakra_mutation_search.py`. Evidence:
`vakra_cars_price_swap_candidates_v1.json`, `vakra_cars_price_swap_audit_v1.json`,
and the earlier `vakra_permissive_v1_answer_annotations.json`. All original
and changed database hashes and individual replay outcomes are retained.
