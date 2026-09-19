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
