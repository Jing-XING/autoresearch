# Bounded schema-only mutation search: completed development diagnostic

The search checks forty recorded episodes on ten known world tasks. It
excludes the any-five question because a changed eligible set need not
invalidate an allowed answer, and the already identified ambiguous
highest-capital question. These exclusions are fixed in the candidate file
before replay. Existing answer labels and model scores are unchanged.

The generator uses evaluator-side SQL, including explicit removal of audit
columns not requested by the question. It does not read model output or
correctness labels to propose changes. It tries at most 2,048 seeded draws
per task and retains the first eight answer-changing changes, where
available. Operations replace a cell with an existing same-column value or
swap two values. Declared primary/unique/foreign-key columns are excluded.
The implementation only promises those declared constraints, not unrecorded
domain semantics. No keys, records or schema are added or deleted.

Fifty-eight modified database copies are generated. Every original episode
replays successfully through the unchanged real MCP server, including its
worker registration history. Across 141 mutant replays, seventeen episodes
have at least one answer-changing mutation preserving the complete target
initial peek, ordered schemas and every tool-result content/error flag.
Search stops at the first witness for an episode. The other twenty-three
episodes have no witness in this bounded search, which means **unknown**.

| Search outcome | Previously correct | Previously incorrect | No final answer |
|---|---:|---:|---:|
| Schema-only witness | 4 | 3 | 10 |
| No witness found | 15 | 5 | 3 |

The raw 17/40 count is **not an ungrounded-answer rate**. Ten witnesses concern
episodes with no final answer. More seriously, all four witnesses paired
with a previously correct answer involve geography: two change a Japanese
city's District to England, and two move Rwanda into Baltic Countries.
The corresponding agents used country/region membership knowledge to choose
their scope. These mutations satisfy the declared database constraints but
conflict with ordinary geographical invariants implicit in the questions.
They cannot establish natural-language reasoning failure without a separate,
explicit admissible-world contract. The initial SQL cards were valid on the
original database; that does not establish their equivalence to the question
over every schema-valid counterfactual.

The same issue appears in a non-final episode whose mutant makes Luanda the
capital of Andorra. The Capital relationship is not declared as a foreign key
in this schema. A successful foreign-key check therefore cannot substitute
for checking actual domain relationships.

Conversely, the automatic search fails to recover the previously validated
Spanish-official mutation for Qwen3 reminder task 3. Its first eight retained
candidates alter life expectancy, capital or country name. This is a concrete
demonstration of search incompleteness, not evidence against the separately
verified full-history witness.

## Consequences for the manuscript

Retain this experiment as a failed broad audit design and an admissibility
diagnostic. Do not promote a schema-only positive into a grounding-failure
label, or a search-negative into a certificate. A refined admissibility
contract and candidate generator would constitute a new development variant
and must preserve these original findings. Evaluation on independent tasks
is still needed. The classical determinacy principle and prior trace-based
checking are discussed in `trace_determinacy_prior_art.md`.

## Reproduction

`prepare_vakra_mutation_search.py` produces the candidate artifact using only
the fixed database and SQL interpretation cards. `audit_vakra_mutation_search.py`
verifies the original runtime/database hashes, creates separate database
copies, checks the target SQL answers, and replays the original and mutant
histories with two concurrent MCP child processes. The original database and
every mutant are hash-checked after execution. Per-episode reports and logs
are retained under `results/vakra-world-mutation-search-v1`; the complete
summary is `vakra_world_mutation_search_v1.json`. Four focused mutation tests
passed, and the real replay audit completed with zero original mismatches.
