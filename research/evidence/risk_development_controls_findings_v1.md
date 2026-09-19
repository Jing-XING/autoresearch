# Public risk-estimation controls: observed development results

The frozen protocol `research/risk_development_controls_v1.md` and implementation
were committed as `eae5e2f` before running on the designated Linux server. All
2304 trials completed without failure: 12 public development pools, four label
budgets, sixteen seeds, and three established controls. No model-generated
candidate, hidden pool or official grader was used.

| Fixed control | Median of 48 within-cell median squared-error ratios |
|---|---:|
| Uniform labels without replacement | 1.000000 |
| Surrogate-only diagnostic | 28.308671 |
| Standard difference estimator | 0.851889 |

Each ratio uses the uniform control as its denominator; lower is better. These
are development diagnostics, not the benchmark's official reward. The difference
estimator improves on uniform in 35 of 48 cells, with cell ratios ranging from
0.292012 to 1.977243. The aggregate does not imply improvement on every pool or
budget. Sixteen seeds are too few for strong comparative or tail claims.
The surrogate-only diagnostic buys but ignores the same labels and is deliberately
weak; its error is not evidence against stronger prediction-assisted estimators.

All 432000 label-query records, original/permuted indices, labels, exact risks,
estimates and squared errors were independently checked from the archived data.
The verifier uses scalar `math.log`/`math.fsum` and `statistics.median` instead of
calling the evaluator's estimator or aggregation implementations. Recorded inputs,
source hashes, identical sampling, the complete grid and all cell ratios agree.
Four synthetic API/arithmetic tests also passed locally and on the server.

The actual runtime was Python 3.13.5 and NumPy 2.5.3, with the three numerical
thread environment variables set to one. Tests took about 0.215 seconds and the
control process about 2.269 seconds. These are single-run observations, not a
performance benchmark. The original task's package pin and sandbox were not
reproduced. The first deployment command had a quoting syntax error before any
execution; it was corrected before the sole completed experimental run.

Package: 58 entries, 770157 bytes, SHA-256
`14e1e49d47e0debadda2bf361cb691b285854c18302df6d92d8c3671d55c946a`.
Raw results: `results/remote/risk-development-controls-v1-results.zip`, eight
entries, 1176665 bytes, SHA-256
`3fb82164e58c6cc0c23818dae6071a0b939c7d5b3b4387f8d22df85518a997f4`.
The archive stays local; summary, protocol, code and receipts are versioned.

This establishes a working public development task and familiar controls for
future research-agent work. It establishes neither a novel estimator nor the
effectiveness of an Agent's experiment-selection policy. A distinct Agent
question, model-generated trajectories, strong decision-policy baselines and
protected evaluation remain necessary for a paper in that direction.
