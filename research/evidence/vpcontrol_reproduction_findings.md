# VP-CONTROL frozen-record arithmetic audit

Checked 2026-09-19. This is prior-work verification, not a new paper result.

Primary paper: [Engineering Reliable Commit Gates for Agentic AI](https://arxiv.org/html/2609.10969v1).
Author release: [Figshare version 1](https://doi.org/10.6084/m9.figshare.33511441.v1).
The full audit ZIP is 23,832,588 bytes with SHA-256
`d96621f7dae9467312d8edf6b0a6bdc9ef711149499e4c2ebcc7fa3a3e4c9be1`.
Its official MD5 and ZIP CRC check passed. No code from the archive was executed.

Our standard-library script `scripts/audit_vpcontrol_archive.py` streamed all
5,760 main-stage materialized rows, checked 259,200 plan records for unsafe /
execution and cost-component consistency, and recomputed 1,188 table cells
for 33 strategies across train, calibration and test. All checked arithmetic
matches. There are 24/8/16 disjoint templates and 2,880/960/1,920 rows in those
splits. This is not independent regeneration of the raw model verdicts or
simulation outcomes. Confidence intervals and calibration validity were not
tested by this script. Full output: `vpcontrol_frozen_arithmetic_audit_v1.json`.

## What the records say

On the 1,920 test proposals, the risk-target 0.01 and 0.02 portfolios both
execute zero actions and defer 1,919 proposals; the remaining proposal follows
the no-action path. Their zero unsafe counts therefore do not establish useful
autonomous coverage. The 0.05 portfolio executes 637 proposals, of which 36
are unsafe: 1.875% of all proposals or 5.651% of executed proposals. These
are different estimands; the latter is not a violation of the paper's former
target. This is a denominator clarification, not a claimed defect.

The author's `coverage` is safe task success without deferral, not simply the
execution rate. A safely blocked already-completed task can contribute to
coverage. Likewise `safe_task_success` can be true for an initially satisfied
state without execution. Consequently coverage need not be below execution
rate, and must not be relabelled as accepted-action frequency.

The frozen fitted policies show that the first lambda candidate has calibration
point risk 0.016667 and approximate upper bound 0.036986, with effective sample
size 331.4. The 0.01 and 0.02 searches reject this first candidate and use the
explicit all-defer fallback. These are observed calibration diagnostics, not
evidence that all possible controllers must defer at those targets.

## Contribution decisions

The inspected code already contains source-diverse verification, memoization
of identical verifier/source/seed calls, context-dependent plan selection,
cost-matched and risk-matched controls, and a transaction-time guard. Generic
source deduplication, verifier voting, cost-aware gating and idempotent recovery
are therefore insufficient as independent P03/P05 contributions.

`cluster_risk_ucb` uses a clipped estimated ICC and an effective-sample Wilson
bound. The paper explicitly calls this approximate. Replacing it with a known
conservative cluster bound is not by itself a novel method. The 8 calibration
templates limit claims about template-population risk; row count alone does
not resolve that limitation. A separate paper on selective risk already
addresses clustering, refitting and ties:
[Valid Per-Field Selective Risk Control for Document Extraction](https://arxiv.org/abs/2608.14639).
Sections 3--5 have now been inspected. The paper distinguishes expected risk
from PAC certification, uses separate score/threshold fitting and discusses
cluster and tie effects. Its document-level guarantee targets a macro
functional, not micro field risk; it also discloses score-refitting concerns
for some implemented tiers. No independent reproduction has been performed.
These overlaps further rule out presenting a generic clustering correction
or fitting split as a new agent-verification method.

The useful next scientific question must exceed these known mechanisms and
must be evaluated beyond this already-public frozen dataset. This audit does
not establish such a question, does not count as a completed paper, and is
not incorporated into the two existing manuscripts as our original experiment.
