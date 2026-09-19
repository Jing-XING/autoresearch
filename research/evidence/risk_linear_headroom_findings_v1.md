# Exact linear-control headroom on public development pools

The diagnostic and protocol were committed as `45d0826` before execution.
The designated server ran the committed script with Python 3.13.5 and
NumPy 2.5.3, verifying all 48 public input files. The calculation completed
with exit zero in approximately 0.274 seconds. No model, private grader,
new sampled trial, GPU job or hidden evaluation data was used.

| Fixed coefficient rule | Median of 12 exact expected-MSE ratios to uniform |
|---|---:|
| Uniform, c=0 | 1.000000 |
| Standard difference, c=1 | 0.823771 |
| Full-label optimal linear coefficient | 0.801406 |

Every pool has lower expected MSE with c=1 than with c=0. The optimal
coefficients range from 0.790457 to 3.098284. The median **within-pool**
oracle/difference MSE ratio is 0.979514: about 2.05% further reduction over
the fixed coefficient. This is not the ratio of the two medians above.
Across individual pools that ratio ranges from 0.769332 to 0.997519, so
the conclusion is not that all remaining improvement is negligible.

The ratio is invariant across the four label budgets because the same
finite-population sampling factor multiplies each fixed coefficient's
residual variance. Absolute MSEs for all 12 pools, four budgets and three
rules are retained. The oracle uses every public label to calculate its
coefficient and is not a legal budgeted estimator. Its bound applies only
to fixed-coefficient uniform sampling, not adaptive selection, nonlinear
estimators or fitting the coefficient from a sampled subset.

The earlier development report's 0.851889 value is a median of sixteen-seed
median-squared-error ratios over 48 cells. The current statistic instead
uses exact expected squared error. Neither number replaces the other, and
their difference cannot be attributed solely to Monte Carlo noise. The
earlier 35/48 improving cells and current 12/12 improving expected variances
do not contradict each other; their estimands and aggregation units differ.

The full returned report is preserved byte-for-byte as
`risk_linear_headroom_v1.json`, 24,203 bytes, SHA256
`ff1bac6824091c53d215dc1aae8b186243b020fcf6389004f80520ab2ab22057`.
The separate reanalysis uses a NumPy covariance matrix and quadratic
variance identity instead of the original scalar residual calculation.
All 144 MSE cells agree within rtol 1e-12 and atol 1e-14; the largest
absolute variance discrepancy is 2.22e-16. Two local synthetic tests also
enumerate every subset of four-element populations and verify the formula,
including constant, perfect and negatively correlated proxies. This is
independent arithmetic implementation within the same research process,
not external replication or a new research-agent result.

## Research decision

Follow-up qualification: the task's public objective is median squared
error, not expected squared error. The later frozen two-block diagnostic in
`risk_median_objective_findings_v1.md` addresses that separate objective.
The original calculation below is not a bound on the median criterion.
The follow-up still finds no aggregate advantage from selecting a coefficient
over the standard full-label analytic coefficient on fresh sampling seeds;
neither is an Agent policy or a budget-valid estimator.

Do not build the fifth paper around Agent selection of this one coefficient.
Its optimum is an established analytic control-variate rule, and on these
fixed public inputs a simple existing correction already captures much of
the available improvement within this restricted class. The two pools with
larger remaining gains preclude a blanket claim that the task is saturated.
This diagnostic does not reject the broader public task or establish whether
an Agent can discover better sampling designs. Such a study would need a
distinct question, strong estimation and decision baselines, actual adaptive
trajectories and protected evaluation.

Recompute on a copy with the public files acquired by the existing asset
fetcher, keeping a new report path:

```text
python scripts/analyze_risk_linear_headroom_v1.py --root . --protocol research/risk_linear_headroom_v1.md --output results/risk-linear-headroom-new.json
```

The source uses only the public input manifest and arrays. It neither fetches
nor executes official graders. Exact floating-point bytes may differ across
Python/NumPy versions; the mathematical comparison above records its tolerance.
