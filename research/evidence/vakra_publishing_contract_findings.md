# Publishing contract status: a second-domain witness

The named counterfactual class changes exactly one author contract flag from
string `0` to string `1`, preserving every other cell. All 23 released author
flags are `0`; admitting `1` is an explicit synthetic-world assumption.
This is a post-outcome development audit, not a held-out prevalence study.
It preserves identities, geography, titles, sales and joins, avoiding the
geographical defect in the preceding schema-only search.

Both contract-related tasks among the twenty publishing questions are
included, with all four existing sequential-executor model/prompt arms.
For each task all 23 flips are enumerated; nine and five respectively change
the requested title/sales answer. Eight baseline replays match completely.
Twenty-nine mutant replays find six witnesses, stopping at the first witness
per episode. One witness belongs to an originally correct answer, four to
incorrect answers, and one to an episode with no final answer. Two searches
find none; this is not a sufficiency certificate for other mutation classes.

The originally correct case is Qwen3/original, publishing task 7. It filters
`authors_contract != "Y"`, then fetches every title and every sales value.
The final answer includes all seventeen distinct correct title/sales pairs
with harmless authorship duplicates. However, the filter does not implement
the stated binary non-contract condition. Setting one later author's flag
to `1` removes *But Is It User Friendly?* from the required answer while
preserving the target episode's complete initial preview, ordered schemas,
and all three exact tool responses. Full retrieval of the output columns
therefore does not establish the correctness of the selection predicate.

Witness database SHA256:
`e41cfdb85f2131ae62391f13b9a8705012a75d88b9f78fe1601e4a880a610c98`.
Correct episode observation SHA256:
`0cc820efe2baec2fa152c62d9519e32ac6d52a6b4aec3efa4e2e14e58dca1e14`.
All earlier independent episodes are replayed to reconstruct schema order;
their data-dependent results may change. They are absent from the target
model's fresh two-message input. The claim concerns target-local evidence.

A separate CPU diagnostic replaces the first call with the existing
`select_data_equal_to(..., value="0")` tool. The unchanged full title/sales
getters now yield seventeen distinct pairs on the original and sixteen on
the mutant, both matching SQL. Thus the public interface can distinguish
the two worlds; the failure is not an impossibility claim about that API.
The evaluator supplied the repair. This is not a model-generated correction,
a neural continuation, or an observed success-rate improvement.

This follows established ideas in
[semantic SQL test-suite evaluation](https://aclanthology.org/2020.emnlp-main.29/),
which evaluates query behavior over multiple databases to reduce accidental
single-database agreement. That primary paper's abstract and introduction
were checked; its implementation was not reproduced. Our exact interactive
observation-preservation requirement is different from comparing a fixed
SQL program's denotations, but that distinction alone does not establish
a novel method. The evidence supplies a concrete diagnostic case beyond
the earlier official-language flag example.
