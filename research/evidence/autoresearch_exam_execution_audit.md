# Research-agent evaluation: execution and scoring boundary

19 September 2026. The official Terminus harness is fixed at
[`a2a8381236a21092a05022f3aa71fd59d508ae39`](https://github.com/bespokelabsai/AutoResearchExam-Terminus/tree/a2a8381236a21092a05022f3aa71fd59d508ae39).
All 31 tracked blobs (1,046,376 bytes) were acquired and verified against their
Git blob identities and SHA-256 digests. This includes the dependency lock,
tests and license. Source acquisition does not constitute a benchmark run.

## What the code actually times

In `src/harbor_autoresearch/trial.py`, the research window begins with a
monotonic clock after preparation. The loop allocates its remaining duration
to an agent phase, collects and seals submitted artifacts, runs the public
grader, then runs the private grader on the same saved artifact. The next
record's wall time is measured after both graders. The loop records agent,
evaluation and other time separately; public feedback and another agent phase
follow only if the stopping conditions permit them. Private scores are kept
in separate progress records. The two graders run sequentially in this path.

This implements the stated end-to-end wall-clock budget. It is not evidence
of a timing defect. A different experiment that subtracts private evaluation
time would change the resource definition and feedback schedule. Offline
timestamp editing cannot establish how an adaptive research agent would act
with earlier feedback or a different remaining-budget prompt. A causal
comparison would require independently executed, matched-budget policies,
retaining artifact versions and all timing components. Scorer replay alone
would be only an accounting sensitivity analysis.

## Checkpoint selection and score conversion

`scoring.py` selects by finite public reward and retains an earlier tied
iteration. `scripts/compute_auarc.py` integrates the hidden-test reward of the
publicly selected incumbent, starting from zero. A later public improvement
can lower the selected private reward. Post-deadline records add no area;
at-deadline records also have zero remaining width. The scoring CLI maps raw
private metrics using the 29 saved difficulty maps unless `--plain` is used.
Dataset aggregation averages repeated runs within a task, then weights tasks
equally. These are existing benchmark choices, not proposed contributions.

We executed the unchanged upstream `test_compute_auarc.py`: **12 tests passed**
in an isolated Python environment with pytest 9.0.3 and `PYTHONUTF8=1`.
The tests exercise the scoring CLI and saved maps, including validation-only
selection, ties, deadlines, invalid/missing selected scores and aggregation.
They do not execute Harbor's trial loop, Docker, task graders or model agents.
The unused `asyncio_mode` configuration produces one warning because this
scorer-only environment does not install pytest-asyncio; strict unrelated
project addopts were overridden. No upstream source was changed.

An initial run had seven passes and five failures because child interpreters
did not inherit parent `-X utf8`; the Windows GBK default could not decode the
UTF-8 reward-map file. The successful run propagates `PYTHONUTF8=1`. Both
reports are retained. This is a local portability setup issue, not a novel
research result or a revision of the benchmark's published findings.

## Consequence for the fifth-paper candidate

The public harness is suitable for further feasibility checks, but task
resource requirements, Docker availability on the designated compute host,
data acquisition and an isolated local-model agent run remain unverified.
The task repository and any hidden evaluator answers were not loaded into
an agent experiment. No GPU job was added or current experiment modified.

Generic anytime scoring, validation-selected holdout evaluation, finite
budget accounting and public/private separation are already implemented.
They cannot serve as a new contribution by themselves. Keep P05 unclaimed
until a distinct decision problem and comparison can be specified. Any later
method study must distinguish an end-to-end wall-clock estimand from an
agent-effort estimand rather than silently substituting one for the other.

Evidence: `autoresearch_exam_harness_source_v1.json`,
`autoresearch_exam_scorer_tests_v1.json`, and
`autoresearch_exam_scorer_tests_v2.json`. Acquisition is reproduced by
`scripts/fetch_autoresearch_exam_harness.py`; the exact test command and
environment override are saved in the test reports.
