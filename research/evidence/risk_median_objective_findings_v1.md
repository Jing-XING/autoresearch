# Median-objective diagnostic on the public development pools

The protocol and calculation were committed as `bf9f4ae` before execution.
The designated Linux host completed the sole calculation with exit zero in
5.566 seconds using Python 3.13.5 and NumPy 2.5.3, with numerical libraries
limited to one thread. A preceding GitHub download timed out before the
working directory or experiment existed; the same frozen files were then
transferred directly. There were no model, GPU or private-grader calls.

The study uses the original twelve public pools and four label budgets.
Two disjoint sets of 4,000 seeds give 384,000 pool/budget samples. Every
coefficient sees the same sampled labels. Coefficients on the fixed grid
0,0.05,...,4 are chosen using only the first block, then evaluated unchanged
on the second. Both blocks reuse the same public pools, so this tests seed
transfer rather than unseen-pool generalization. The benchmark's private
seeds, grader, reward conversion and sandbox are not reproduced.

| Control | Selection-block median cell ratio | Evaluation-block median cell ratio | Evaluation cells better than c=1 |
|---|---:|---:|---:|
| Uniform, c=0 | 1.000000 | 1.000000 | 0/48 |
| Difference, c=1 | 0.819591 | 0.814237 | 0/48 |
| Full-label expected-MSE coefficient | 0.798857 | 0.775233 | 44/48 |
| Grid coefficient chosen on first block | 0.792243 | 0.787379 | 37/48 |

Each entry is the median across 48 cells of that cell's median squared error
divided by the uniform control's median squared error. The table does not
report expected MSE or an official benchmark reward. It cannot be compared
numerically as if it were the earlier exact expected-MSE diagnostic.

The grid search looks better than the analytic coefficient in its selection
block but worse in the evaluation aggregate. It beats that coefficient in
16 of the 48 evaluation cells. This is a descriptive finite-run comparison,
not a population superiority claim. The median within-cell ratio to c=1
is 0.979687 for the selected grid coefficient and 0.973652 for the analytic
coefficient. These correspond to about 2.03% and 2.63% further reduction in
the median cell; they are not ratios of the aggregate table entries.
Individual ratios range from 0.737084 to 1.023193 for the grid choice and
0.727545 to 1.017832 for the analytic coefficient, so some cells have much
larger gains and others regress. Selected coefficients range from 0.65 to 3.65.

## Consequence for the fifth-paper candidate

The original expected-MSE calculation did not bound this median objective.
The new, objective-matched diagnostic still provides no reason to make
one-dimensional coefficient search the proposed Agent contribution. A
standard analytic control remains a strong comparison, and selecting among
81 coefficients does not improve the aggregate on fresh sampling seeds.
This does not establish saturation or reject adaptive sampling, nonlinear
estimators, budget-valid coefficient fitting or new-pool generalization.

Both the analytic coefficient and selection-block scoring use all public
labels, so they are diagnostic oracles, not legal budgeted estimators. No
research Agent has been evaluated here. A fifth paper still needs a distinct
decision question, adaptive trajectories and protected evaluation; neither
these controls nor their familiar selection effects constitute that paper.

## Evidence and verification

The seven-member raw ZIP is retained at
`results/remote/risk-median-objective-v1-results.zip`, 5,826,002 bytes, SHA256
`b9b07c7f46eccf90a366262f1ae55905d7afd3e53bb4c69e2330a61bf8555c3d`.
`risk_median_objective_summary_v1.json` preserves the remote report's exact
343,325 bytes, SHA256
`37e1d600e25dbb4f0875675bf685454525ccf5018b3533d78caa6f82e845aeff`.

The separate verifier imports no calculation-runner functions. It checks
all 48 input files, 384 control medians using scalar arithmetic and
`statistics.median`, all 7,776 grid medians, selection and aggregates. It
replays 288 specified sample-component pairs with scalar loss calculations;
the maximum absolute discrepancy is 1.33e-15. The remaining component pairs
are hash-verified saved data, not individually regenerated in this check.
`risk_median_objective_reanalysis_v1.json` records the exact verification
scope. Two synthetic tests separately compare the components to the existing
label-query driver and ensure evaluation outcomes cannot select a coefficient.

Reproduce only into new paths:

```sh
python scripts/analyze_risk_median_objective_v1.py --root . \
  --protocol research/risk_median_objective_v1.md --output results/risk-median-new
python scripts/verify_risk_median_objective_v1.py \
  --archive results/remote/risk-median-objective-v1-results.zip \
  --sha256 b9b07c7f46eccf90a366262f1ae55905d7afd3e53bb4c69e2330a61bf8555c3d \
  --output results/risk-median-rechecked.json
```
