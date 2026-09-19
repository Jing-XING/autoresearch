# Linear-control headroom diagnostic on public development pools

20 September 2026. This is a post-development feasibility analysis, motivated
by the already observed sixteen-seed control results. It is not a held-out
method evaluation, preregistered confirmatory study or new estimator.

For each of the same twelve public pools, let L be the observed per-row loss
and H the surrogate expected loss. Consider only uniform sampling without
replacement and a fixed coefficient c: estimate mean(L) by mean_sample(L)
plus c times (mean_population(H) minus mean_sample(H)). The coefficient is
fixed independently of the sampled labels. For sample size b and population
N, the exact sampling MSE is (1-b/N) times S2(L-cH)/b, with finite-population
variance using denominator N-1. The full-label oracle coefficient is
Cov(L,H)/S2(H), or zero when H is constant. This is standard control-variate
algebra, not a novel algorithm. It optimizes expected squared error within
this class, not median squared error or the original benchmark reward.

Compute the full-label moments, exact MSE for c=0, c=1 and the oracle at
b=50,100,200,400. Keep all twelve pools, including cases where c=1 is worse.
Report per-pool values and median ratios without sampling-error confidence
intervals: they exactly describe these fixed public arrays. Explicitly state
that full labels make the oracle unavailable to a budgeted estimator. Its
bound says nothing about adaptive label selection, nonlinear estimators,
fitted coefficients, unseen pools or research-agent performance.

Execute the calculation on the designated server with single-thread NumPy,
after checking the public manifest and all 48 pool input files. Do not read
private graders or add model calls. Validate the formula locally on tiny
synthetic populations by enumerating every subset, including constant-proxy
and perfect-proxy cases. Raw report paths must be new. Preserve source,
protocol and input hashes. Use this diagnostic to decide whether a future
coefficient-selection Agent study would mostly test a familiar analytic rule;
do not label the diagnostic itself a fifth paper.
