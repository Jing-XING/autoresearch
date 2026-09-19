# Claim-to-evidence record for the working manuscript

This manuscript is incomplete. A verified development observation is not an
independently confirmed result or a publication-level contribution.

| Claim | Evidence | Scope |
|---|---|---|
| Source collection covers 74 tasks for each of two models. | `../evidence/tau_train74_source_summary.json`; four hash-verified raw source archives. | 148 source episodes; one original protocol exception retained. |
| Some prefixes assigned zero completion reward have successful recorded continuations. | `../evidence/tau_train74_qwen3_state_audit.json`; source cutoff manifest; `figures/source_cutoff_observations_data.json`; `../evidence/memory_cutoff_satisfaction_join_v1.json`. | At cut8, two externally cut prefixes already satisfy state/action checks, eight more satisfy them later. Research-imposed cuts of the same fixed-policy run, not natural stopping failures or a causal effect of announcing a larger budget. |
| Compact curation has complete output coverage without 256-token ceiling hits. | `../evidence/memory_curation_v2_quality_audit.json`. | 222 compact outputs. This is structural completeness, not factual correctness. |
| All target tickets tie in the initial retriever audit; only four source records are selected. | `../evidence/memory_transfer_retrieval_audit.json`; actual first-call selection metadata in target logs. | Twenty development targets; v2 keeps v1 source identities/tickets and the retriever. |
| Fresh controls reproduce every old baseline input, tool schema and completion token sequence. | `../evidence/tau_memory_v2_control_reproducibility.json`; `../evidence/tau_memory_v2_none_summary.json`. | Forty repeated model-task combinations, not additional independent observations. |
| The complete grid does not demonstrate benefit from boundary-aware versus full-metadata curation. | `../evidence/tau_memory_small20_v2_analysis.json`; `figures/memory_transfer_development.json`. | Qwen3 zero wins/zero losses; Qwen2.5 zero wins/three losses. Twenty development tasks and four reused source memories. |
| No memory-treatment trajectory is observed to satisfy the task and then fail its recorded outcome. | Four `../evidence/tau_memory_v2_*_state_audit.json` files; `../evidence/tau_memory_v2_protocol_failure_audit.json`. | 155 completed trajectories and five valid histories preceding protocol exceptions; diagnostics do not revise rewards. |
| Some inspected lessons overstate causality, resolution or temporal scope. | `../evidence/selected_memory_grounding_audit.md`; quoted source observations in the frozen bank's raw memories. | Qualitative inspection of the four retrieved sources; no population error-rate or downstream causal attribution. |
| All fifteen test-selected source IDs and 45 lessons have been descriptively inspected. | `../evidence/memory_test40_selected_grounding_review_v1.json`; `../evidence/memory_test40_selected_grounding_validation_v1.json`. | Seventeen selected claim examples; one unblinded Codex reviewer, not exhaustive error rates or independent adjudication. Quotations and cited tool IDs checked programmatically. |
| Different source IDs can supply identical memory content. | `../evidence/memory_bank_content_diversity_v1.json`. | Fifteen target tasks share an identical alternative pair, yielding 60 paired repeat checks across two models and two conditions. Actual repeat outcomes pending. |

The following claims are **not established**: broad transfer gains from
boundary-aware instructions; superiority over Negative Knowledge, Grounding
Agent Memory or Agent Workflow Memory; effects on independent task families;
cross-environment replication; superiority at equal total experimental cost;
and readiness for a journal or conference submission.

## Registered test extension, not results

`memory_test40_tie_registration_v1.json` fixes all forty previously unused
telecom test identities, the unchanged 74-record source bank, two checkpoints,
two curated conditions and three exact-top-tie source choices, plus one
no-memory baseline per checkpoint: 560 executions. Five sources are reused
under each rule, fifteen distinct across rules. This is source-choice
sensitivity, not three independent source-population samples.

The deployment record reports 27 actual remote tests and 240 verified
condition/source selections over all forty tasks. A first preflight failed
because the official loader order differed from the registration; the second
immutable code revision restores the same registered order after checking
identity-set equality. No target inference preceded that repair. The queued
experiment has no completed results available for manuscript claims yet.
