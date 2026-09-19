# Public risk diagnostic matched to the median-error objective

20 September 2026. Freeze before this calculation. Earlier 16-seed
development controls and exact expected-MSE moments have already been seen.
This is a post-development diagnostic, not an independent method evaluation.

The public task scores the median squared error over 4,000 seeds per
pool/budget cell, normalized by the uniform estimator's corresponding
median, then takes the median across cells. The preceding linear-control
headroom calculation optimized expected squared error instead. Its algebra
remains correct, but its small average-MSE headroom is not a bound for the
task's median objective. Test that distinction before using it to select a
research-agent study.

Use exactly the same twelve public development pools and budgets 50, 100,
200 and 400. No hidden data, evaluator, task hints or solutions may be read.
Compare fixed coefficients c=0, c=1 and the full-label expected-MSE optimum
Cov(L,H)/Var(H). Also examine the fixed grid c=0,0.05,...,4.0. A coefficient
defines mean(sample L)+c*(mean(population H)-mean(sample H)). All candidates
share the same uniform sample without replacement. L is true cross-entropy
loss and H is surrogate expected cross-entropy; this is established
control-variate estimation, not a new algorithm.

Use two disjoint blocks of 4,000 seeds: 202609200000 through 202609203999 for
selection, and 202609210000 through 202609213999 for evaluation. These are
our public-development seeds, not the benchmark's private pinned seeds.
For each seed, independently permute rows with SeedSequence([seed,7701]),
then draw each budget's sample with default_rng(seed).choice(N,b,replace=False),
as in the existing development driver. Reusing seeds across pools and budgets
does not make cells independent.

For each cell, choose the grid coefficient with lowest selection-block median
squared error, breaking ties toward the smaller coefficient. Evaluate that
fixed choice on the second block. Report its selection and evaluation values,
the whole coefficient curve, all three fixed controls, the selected coefficient,
and exact expected-MSE ratios for those coefficients. Never choose a new winner
using the evaluation block. Report the number of cells improved/worsened and
the median of the 48 normalized cell ratios. The same original pools occur in
both blocks: this tests sampling-seed transfer only, not new-pool generalization.

The MSE-optimal coefficient uses every label. The grid selection also uses
full labels to evaluate candidate errors. Both are diagnostic oracle controls,
not legal budgeted estimators or Agent policies. The grid supplies no bound
outside [0,4] or between its points. Monte Carlo medians are estimates, not
exact finite-population medians; no significance or saturation claim follows.

Run the trusted script on the designated Linux server with numerical libraries
limited to one thread. Verify all 48 public input files before calculation.
Save the two linear error components for every sample, all coefficient curves,
source/protocol/input/runtime hashes and execution status. Output paths must
be new. No model calls or GPU experiment changes. Local synthetic checks must
compare these components against the existing label-query driver and validate
that evaluation-block outcomes cannot influence selection.
