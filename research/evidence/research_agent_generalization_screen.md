# Research-agent evaluation candidate: current overlap

19 September 2026; primary-page screening, not source-code reproduction.

[AutoResearchExam](https://benchmarks.bespokelabs.ai/autoresearchexam/)
already studies validation improvement versus hidden-test generalization in
29 open-ended ML tasks. Its 24-hour runs expose validation feedback while
keeping test scores hidden, and score the time-weighted hidden-test reward
of the validation-selected incumbent. It separates worker and verifier
containers and discusses budget-dependent rankings, submission frequency,
and a hint-based comparison. These are reported design/results, not results
we have reproduced. Thus adding an unseen test set, plotting a validation/test
gap, or reporting an anytime curve is not a new contribution.

The [official task repository](https://github.com/bespokelabsai/AutoResearchExam)
was located, including CPU research tasks and an official harness link.
No revision, runtime, private-test access or resource requirement has yet
been verified. Do not claim this project has an executable benchmark solely
from the repository link, and do not read hidden evaluator answers into any
future research-agent context.

Research decision: this may supply more suitable public tasks for a distinct
experimental-decision study than a bespoke toy research loop. A new question
would need a concrete decision rule and matched baselines beyond ordinary
holdout separation and established adaptive-data-analysis methods. The
current dependent-verification candidate is not replaced or counted complete
by this screening. No additional GPU job is authorized by this note; the
already registered experimental queue remains unchanged.

Subsequent work: [task/runtime preparation](autoresearch_exam_task_readiness_v1.md)
now pins all29 task specifications and the public inputs for three CPU-only
interfaces. The designated host executed public array/schema checks and
48 calls to the unchanged CI generator. No hidden evaluator, task reward or
adaptive research-agent loop was run. Current container has neither Docker
CLI nor daemon socket; original task runtime parity remains unverified.

The next public development control is now executed and independently
audited: [risk controls](risk_development_controls_findings_v1.md), 2304
trials on the designated host. Uniform, surrogate-only and standard
difference-estimator ratios are 1, 28.308671 and 0.851889. This supplies
tested task infrastructure and established controls, not an Agent-policy
result or a novel statistical estimator. Hidden grading remains untouched.

## Additional closest-work check, 19 September 2026

[RoboPhD, v1](https://arxiv.org/html/2604.04347v1), sections 3.2--3.5,
already compares Elo competition, a two-candidate variant, generalized
autoresearch and GEPA under matched evaluation budgets. Its candidates share
fresh evaluation examples within a round, and the same evaluations supply
comparative diagnostics for later proposals. Thus fresh paired evaluation,
less validation, and tournament selection cannot be claimed as new on their
own. The paper also discloses differences in sampling and model access across
engines. We read the method and comparison design; we have not reproduced its
source or reported results.

Decision: the existing risk-task controls support infrastructure only. Do not
launch a large Agent experiment whose sole proposed contribution is choosing
between the above established allocation patterns. A narrower causal question
and a faithful strong baseline are still required. Meanwhile, strengthen the
separate recovery-interface study using native composition controls, where a
specific source-derived hypothesis can be tested without new model calls.
