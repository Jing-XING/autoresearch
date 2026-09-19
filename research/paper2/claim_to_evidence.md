# Working manuscript claim-to-evidence record

This is an incomplete development manuscript, not a completed paper.

| Claim | Evidence | Limit |
|---|---|---|
| Eight initial episodes contain incomplete language lists, wrong aggregation scope and one OOM. | `../evidence/vakra_native_first4_v1_audit.md`, corresponding summary and hashed archive | Selected first four public training queries, two Qwen checkpoints; not prevalence. |
| The matched reminder study includes all 48 episodes with common resources and initial observations. | `../evidence/vakra_coverage12_v1_summary.json`, `../../scripts/analyze_vakra_coverage_control.py` | Twenty calls, 512 new tokens, 32768 input ceiling; the first eight episodes cannot replace this fresh control. |
| On eleven interpretable tasks, SQL-compatible answers change from 3 to 9 and 4 to 6. | `../evidence/vakra_coverage12_v1_answer_annotations.json`, `vakra_coverage12_v1_answer_audit_summary.json` | Assistant qualitative audit, not official VAKRA score or independent human labels. |
| The ambiguous highest-capital task is retained separately. | Frozen `../evidence/vakra_world12_semantic_audit_cards.json`, all four annotations | Numeric city-ID ordering does not resolve the original natural-language ambiguity. |
| Qwen3 still omits Uzbek; Qwen2.5 regresses on official-English countries. | Reminder cases 002 and 000 respectively, with full annotations and source hashes | Development counterexamples, no broad causal attribution. |
| Some gains coincide with min/max and selective retrieval instead of large full getters. | `../evidence/vakra_coverage12_v1_observed_lineage.json` and raw traces | Descriptive mechanism, not a randomized mediation analysis. |
| Qwen3's answer gains do not reduce total token processing or generation time. | Complete execution summary and `../evidence/vakra_coverage12_v1_results.md` | Attempts include input-limit rejections; generation usage excludes them. |
| A passive ledger tracks actual handle lineage and direct column observations. | `../../autolab/tool_evidence_ledger.py`, six tests, complete 48-episode replay | Not a query-semantic verifier; earlier parent columns can make a later partial preview sufficient in the full history. |
| The fixed prompt transfers unevenly across three additional databases. | `../evidence/vakra_crossdomain_v1_answer_summary.json`, all 240 annotations and execution hashes | Small-database convenience selection; fixed SQL interpretations, assistant labels, related Qwen checkpoints. |
| Combined replication subtotals are 29/55 to 32/55 and 19/55 to 21/55. | Complete answer summary and plotting source-data JSON | Five ambiguity exclusions frozen before outcomes; highest-employee wording additionally flagged after outcomes without denominator change. |
| Local single-call enforcement rejects some executable batches. | `../evidence/vakra_crossdomain_v1_rejected_batch_audit.json` | 13/32 first-rejected batches executable; no model continuation or retrospective rescore; execution does not imply semantic correctness. |
| A correct Andorra answer is not identified by the target episode's full tool observations. | `../evidence/vakra_full_history_witness.json`, `../../scripts/audit_vakra_full_history_witness.py` | One post-hoc database-copy intervention; earlier independent task output differs and is absent from the fresh target model input. |
| Two student tasks' prescribed initial relations omit answer-relevant information. | `../evidence/vakra_initial_scope_counterfactuals.json` and `vakra_cross_universe_visibility.json` | Each mutation changes 14/27 other initial relations; not unrestricted API impossibility. |

| A broad schema-only search produces misleading candidates under implicit geographical constraints. | `../evidence/vakra_world_mutation_search_v1.json`, corresponding findings | 17/40 SQL-relative witnesses; all four previously correct-answer cases need geographical admissibility review, and ten cases have no final answer. |
| A single-status-flip control recovers the known complete-history witness. | `../evidence/vakra_world_binary_status_audit_v1.json`, corresponding findings | Post-outcome positive control on two known tasks; no independent prevalence estimate or complete verifier. |

Not established: a novel controller, held-out method benefit, an automatic
semantic sufficiency score, broad cross-database generalization, superiority over
executable processing, or journal/conference submission readiness.
# Executor sensitivity addition, 2026-09-19

The full permissive archive contains 240 episodes and twelve successful worker
exits. `vakra_executor_pairing_v1.json` verifies all initial inputs and 240
first replies. `vakra_permissive_v1_answer_annotations.json` records 213
identical-text label transfers and 27 fresh changed-answer reviews.
`vakra_permissive_v1_answer_summary.json` supports the frozen SQL subtotal
table in section 7. It is not official VAKRA scoring. Qwen2.5 gains twelve
final responses but only one net correct answer; Qwen3 scores are unchanged.

## Publishing predicate counterexample

`vakra_publishing_contract_audit_v1.json` verifies the original and mutant
MCP transcripts for all four sequential model/prompt arms on two contract
queries. The correctly answered Qwen3 original task 007 retrieves every
requested output-column value but filters `authors_contract != 'Y'`.
Changing one author's contract from `'0'` to `'1'` changes the required
title/sales answer while leaving the full target tool observations identical.
The admitted binary status domain is explicit; all original observed values
are zero. This post-outcome synthetic-world test is not a prevalence estimate.

`vakra_publishing_contract_repair_v1.json` verifies an evaluator-authored
diagnostic: replacing the first filter with equality to `'0'` distinguishes
the worlds, and the same following getter calls return the correct 17 and 16
distinct title/sales pairs. This is real MCP execution, not a model-generated
repair or evidence of autonomous repair success.
No inference about novel-method benefit or population significance follows.

## Third-model performance floor

`vakra_smollm3_v1_execution_summary.json` validates all 240 executions,
model hashes and 120 identical first executor-paired replies. The literal
240-entry annotation file and joined answer summary support section 9:
221 final responses but six SQL-compatible answers among 220 scored
executions. Two qualified predictions are also excluded in a sensitivity
column. Sixty-six finals reach the length ceiling, which does not establish
that each was truncated. This is a known-task, resource-specific sensitivity
analysis, not a general model ranking or an independent confirmation study.

## Additional mutation negative result and pending extension

`vakra_cars_price_swap_audit_v1.json` and its candidate manifest retain all
80 original sequential car episodes. All baseline replays match; 332 mutant
replays over 99 task-specific databases find ten observation-preserving
witnesses, all for previously incorrect answers. None of 43 correct-answer
episodes obtains a witness under this bounded price-swap grammar. This does
not certify sufficiency and does not add a correct-answer counterexample.

`vakra_domain_expansion_registration_v1.json`, the setup audit and frozen SQL
cards register 70 public training tasks from four additional small domains,
three Qwen checkpoints and two fixed prompts: 420 executions. Twenty-one
task ambiguities are flagged before model outputs, leaving 49 primary scored
tasks per model/prompt. Registration is not a completed experiment or proof
of benchmark/pretraining independence. The 12 preregistered output-budget
replays additionally require exactly matching initial model input and previews.
Their deployment record reports 22 actual remote preflight tests, not neural
results. The completed cookbook slice now contributes the explicitly partial
result below; the remaining domains and budget rerun are not reported as complete.

## Conditional uncertainty

`vakra_prompt_conditional_uncertainty_v1.json` joins all three frozen annotation
files by task and preserves all six model/executor prompt comparisons during
10,000 within-domain task resamples. All six percentile intervals include zero.
Qwen3's leave-one-domain-out difference changes sign when cars is omitted.
These conditional descriptive intervals exclude model-seed, annotation and
unseen-domain uncertainty; no benchmark-population hypothesis test is claimed.

## Complete larger-checkpoint extension

`vakra_qwen30b_complete_grid_v1.json` verifies all 120 known-task executions,
all six successful worker exits and sixty matched initial prompt pairs.
`vakra_qwen30b_answer_annotations_v1.json` contains the complete single-assistant
review; the joined `vakra_qwen30b_answer_summary_v1.json` gives original/reminder
scores 35/55 and 38/55, with 58/60 and 60/60 final answers. The five pre-existing
ambiguous tasks per prompt remain excluded only from primary accuracy. All
failures and ambiguous executions remain in resource accounting.

`vakra_qwen30b_conditional_uncertainty_v1.json` records five gains, two losses,
48 ties and the conditional interval [-3.64, 14.55] percentage points. This
known-task checkpoint comparison is not a causal scaling study. Publishing
012 illustrates that a reference-compatible final price can coexist with an
incorrect aggregate-sales derivation; no answer label is a grounding score.

## Preserved infrastructure failure

The initial expansion failed before any task generation because a device
object could not be written to JSON. Downstream batches stopped before their
workers launched. `research_queue_startup_failure_v1.json` records the raw
archive, and `research_queue_restart_amendment_v2.json` links unchanged
registrations to new run identifiers and a metadata-only serialization fix.
`research_queue_restart_deployment_v2.json` verifies actual startup recovery.
Those operational checks add no task-answer result to this manuscript.

## Closed cookbook-domain result

`vakra_expansion_cookbook_closed_grid_v1.json` verifies all 120 executions,
six successful worker exits, immutable source/model identity and sixty matched
initial prompt pairs. It explicitly records `complete=false` for the full
420-episode batch and `closed_domain_complete=true` for cookbook. All finals
were read; `vakra_expansion_cookbook_annotations_v1.json` and the joined answer
summary retain four frozen ambiguous tasks and give original/reminder counts
9/16 to 8/16, 7/16 to 7/16, and 11/16 to 11/16. This is a single unblinded
assistant audit, not a grounding score, human agreement study or broad null
effect. All 120 finals, zero protocol errors and all resource use are retained.
The raw archive receipt records the exact 145-entry package and hashes.

`vakra_cookbook_helper_trace_v1.json` extracts the larger-checkpoint reminder
task 015: a successful `select_unique_values` call returns the agent-supplied
ten-name list unchanged; the final repeats it despite reference disagreement.
The native helper only deduplicates input. This post-outcome illustration
does not establish failure prevalence or impossibility under other tool
sequences. The cookbook retrieval handle is not a full-column observation.

## Executed cookbook acquisition control

`vakra_cookbook_acquisition_control_v1.json` records six real native MCP
replays of the selected task 015. All worker warmups, 90 preceding independent
episodes/224 tool calls, target initial previews, ordered schemas and selected
prefix responses match their recorded observations. From each model's existing
correct filter, an evaluator-authored keyset paginator obtains ten ingredients
in four additional calls, for six or seven target calls in total. The controller
uses no reference card or direct database read. The independent validator
recomputes its result from saved responses and read-only SQL; all six match.
`vakra_cookbook_acquisition_validation_v1.json` records the 18-entry raw archive.

The protocol explicitly discloses selection after answer review. This is one
question with six histories, an ordinary pagination control and no neural
continuation. It rules out retrieval impossibility within the call budget in
this example, not general interface limits, a cause of model behavior, or a
model repair-success rate. Four unit tests separately cover duplicates, budget
exhaustion, empty data and rejection of invalid/nonprogressing observations.

## Closed Disney-domain result and disclosed review sensitivity

`vakra_expansion_disney_closed_grid_v1.json` audits the second closed domain
slice: 120 records, six worker exits zero, sixty identical initial prompt
pairs and the unchanged registered sources/models. The complete 420 grid
is still marked incomplete. The byte-verified 145-entry raw package is
1,077,140 bytes, SHA256
`291b6889a529231078d1afe3bedb827509608dc993f1ccea01af629fd97a100a`.
`vakra_expansion_disney_raw_receipt_v1.json` links every derived artifact.

All full responses/absence were read by one unblinded assistant. The
annotations and answer summary retain frozen ambiguous tasks 001/014 and
give original/reminder requested-value counts 12/18 to 9/18, 5/18 to 7/18,
and 12/18 to 15/18 for Qwen3, Qwen2.5 and Qwen30B. Paired gains/losses are
1/4, 4/2 and 3/0. All 120 costs, six missing finals, twenty-six protocol
errors and two generation-ceiling finals remain recorded. Four missing
finals are ambiguous; two scored missing finals stay in the denominator.

`vakra_expansion_disney_review_sensitivity_v1.json` contains the full text
and immutable source identity of eight borderline responses and recomputes
all counts after changing those labels to incorrect together. Counts then
become 9/18 to 8/18, 5/18 to 6/18 and 10/18 to 14/18. This post-review
conservative reading preserves the three effect directions but is neither
a preregistered second metric nor independent adjudication. The audit
scores requested values, not all explanatory propositions or trace-level
identification. No pooled all-domain result, population superiority claim,
causal explanation or official VAKRA score follows from this partial grid.

## Closed genes domain of the registered expansion

`vakra_expansion_genes_closed_grid_v1.json` verifies sixty episodes, six
successful worker exits and thirty identical initial prompt pairs against
the unchanged deployment. The byte-verified raw archive has 85 entries,
534302 bytes and SHA256
`994a33d9cfeb6516798a109ae264cdac4c4f3796bd1044343e3d0d0214938ac0`.
`vakra_expansion_genes_raw_receipt_v1.json` links derived hashes. This is the
third closed domain, not completion of the full 420-episode experiment.

All sixty complete finals or absences were read. The annotations preserve
the pre-run ambiguous tasks 0,1,2,5,6,8,9: forty-two executions remain in cost
and termination reporting but outside answer accuracy. All eighteen scored
responses are incorrect under the frozen distinct-ID/count/complete-function
interpretations. Each model/prompt arm scores 0/3; there are no missing
scored finals. Across the full domain there are fifty-four finals, five
step limits, one protocol-error limit, ten protocol errors and no final
at the generation ceiling. The summary retains all six arms and costs.

The review is by one unblinded assistant, with no independent human
adjudication. The three-task zero floor does not establish prompt equivalence,
general ineffectiveness, a causal trace mechanism or a population failure rate.
