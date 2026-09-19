# Research-agent decision study: updated primary-source constraints

Read on 20 September 2026. These notes narrow a candidate, not establish a
fifth-paper contribution or reproduce any cited system.

- [AIRA2, v2](https://arxiv.org/html/2603.26499v2), sections 3.3 and 4.3.2:
  external evaluation fixes splits, withholds labels and separates search
  from final selection. Its ablation attributes observed degradation in its
  earlier setup to inconsistent evaluation rather than demonstrating a
  universal absence of adaptive overfitting. The paper explicitly leaves
  that future possibility open. Therefore a generic stable evaluator or
  noise-versus-overfitting observation is not a new contribution here.
- [What Fits (Into Few Tokens) Doesn't Overfit, v1](https://arxiv.org/html/2606.11045v1),
  abstract and introduction: the authors test short strategy prompts passed
  to fresh reproducers and one-bit ladder feedback. They also deliberately
  induce validation exploitation. Compression or a one-bit accept/reject
  signal cannot be presented as a new Agent research-control mechanism here.
  We have not checked their proofs or reproduced their numerical results.
- [Agentic Auto-Research is Fuzz Testing, v1](https://arxiv.org/html/2608.09855v1),
  sections 6-8: a position paper separates progress guidance from protected
  validation and proposes controlled comparisons with repeated sampling.
  Those proposals are not evidence that a particular controller works. A
  progress proxy plus a protected verdict is also not novel merely because
  implemented in this repository.
- [How Do Agents Fail on AutoResearch, v1](https://arxiv.org/html/2608.14905v1),
  sections 3 and the analysis/interpretation taxonomy: the authors inspect
  full artifacts and distinguish statistical misuse, missing baselines and
  unsupported conclusions. Their described human-calibrated annotation is
  not a procedure reproduced in our project. A new failure checklist alone
  would not distinguish the fifth candidate.

## Concrete question exposed by our existing public controls

The acquired public instruction for `label-efficient-risk-estimator` defines
a median-squared-error objective over 4,000 seeds, followed by a median of
normalized cell scores. Our earlier exact linear oracle minimizes expected
squared error. Its derivation and reported numbers are still valid, and its
original protocol explicitly states this restriction. It does not bound the
median objective, so it cannot alone justify abandoning coefficient search
under that objective. The previous research decision must retain this caveat.

`research/risk_median_objective_v1.md` freezes a paired two-block diagnostic
against the public scoring definition, before its output is observed. Both
blocks reuse public pools and compare established estimators; this is not
an Agent experiment, a protected new-pool evaluation, a benchmark defect or
a new estimation method. Actual results will determine whether the mismatch
changes the feasibility decision. A distinct agent-level hypothesis and
adaptive trajectories remain required before this slot becomes a paper.
