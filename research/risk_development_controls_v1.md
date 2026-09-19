# Public risk-estimation development controls, v1

Frozen before computing any public-pool risk score. This is infrastructure for
research-agent experiments, not a new statistical method or a fifth paper.

## Inputs and controls

Use only twelve public development pools from AutoResearchExam revision
`7758e84af55f7666cbdcdd7192959f45b09827af`, verified against
`autoresearch_exam_public_assets_v1.json`. Public labels are intentionally available
for development in the original task. Do not fetch private graders or held-out data.

For each pool, budgets 50, 100, 200, 400 and sixteen seeds 2026091900 through
2026091915 give 768 pool-budget-seed combinations. Run three fixed controls on
each, for 2304 trials:

1. Uniform sampling without replacement, reporting mean observed negative log
   target probability.
2. Surrogate-only diagnostic: let h_i be the surrogate-probability weighted
   negative log target probability. Report mean h over the pool. Query the same
   labels but ignore their values. This deliberately weak diagnostic measures
   uncorrected proxy bias; it is not presented as a competitive label-efficient
   algorithm.
3. Standard difference estimator: mean h over the pool plus the sampled mean of
   (observed loss minus h). Coefficient one is fixed, with no clipping or fitting.

The third estimator is unbiased under uniform sampling, conditional on the fixed
pool. It is an established prediction-assisted control, not novel. Related modern
inference work includes Angelopoulos et al., *Prediction-powered inference*,
https://arxiv.org/abs/2301.09633. This experiment estimates a mean only and does not
implement their confidence intervals or claim a full reproduction of that paper.

## Coupling, failures, and aggregation

Every trial permutes rows using SeedSequence([seed, 7701]); the estimator receives
an independent default_rng(seed). All controls therefore buy identical rows per
pool-budget-seed. Record every query's permuted index, original index and label,
the permutation hash, exact risk, estimate, squared error and elapsed time.
Repeated queries are legal and consume budget, matching the public API. The
trusted controls themselves sample without replacement. No labels are passed in
the constructor. A fresh estimator instance and read-only array copies prevent
accidental state sharing; this is not a security boundary against hostile code.

Compute each method's median squared error over sixteen seeds, divide by the
uniform control's median error for that cell, then take the median of the 48 cell
ratios. Also preserve every cell and trial. A missing/duplicate trial aborts
aggregation. Exceptions, non-finite estimates, bad indices and elapsed time over
five seconds remain explicit failures, invalidating that method's cell and its
overall ratio rather than being dropped. A zero uniform median also invalidates
the ratio. No heuristic worst-case penalty is invented. These failure semantics
differ from the official grader.

## Runtime and interpretation

Execute on the designated Linux server, existing Python environment, with
OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1 and a 120-second outer
process bound. No GPU or model calls. Existing immutable GPU queues are untouched.
Keep source and protocol hashes, public input hashes, raw trials, stdout/stderr,
exit status and runtime versions. Do not overwrite a prior output directory.

This is a trusted in-process development evaluator, not an arbitrary candidate
sandbox. Time is checked after callbacks; a hung callback is only stopped by the
outer process timeout. It does not reproduce the official fresh source execution,
unprivileged read-only filesystem, exact permutation implementation, 4000 seeds,
private pools, grading reward transform or original pinned package environment.
Reported ratios are development diagnostics, not official scores. Sixteen seeds
are deliberately a small interface/control study, inadequate for a strong method
claim or reliable tail inference. No model-generated candidate is evaluated here.
