# Public research-task feasibility on the designated compute host

19 September 2026. This is executed input/runtime preparation, not a fifth
paper result or a claim that a research-agent evaluation has completed.

## Pinned official task inventory

The [official task repository](https://github.com/bespokelabsai/AutoResearchExam/tree/7758e84af55f7666cbdcdd7192959f45b09827af)
is pinned at `7758e84af55f7666cbdcdd7192959f45b09827af`. Its complete recursive
Git tree has 1,004 tracked blobs totalling 489,268,162 bytes. The repository
contents were not all downloaded. The acquisition allowlist fetched 143
public specification/setup documents (272,319 bytes), verified by Git blob
identity, byte length and SHA-256. All twenty-nine task specifications are
included. No test, hidden-data, hint or solution file was selected.

The worker resource declarations divide into twenty-two CPU-only tasks and
seven one-H100 tasks. Every CPU-only worker declares eight CPUs, 14,336 MB
memory and 153,600 MB storage. These are declared resource requests, not
measured peak usage or proof that a task fits in a smaller allocation. H100
tasks cannot be treated as A40-equivalent benchmark runs without an explicit
adaptation and its limitations.

The existing remote container reports no `docker` command and no
`/var/run/docker.sock`. Its visible logical CPU count is 64 and `/xingjing`
has approximately 4,520.5 GiB free in the observed snapshot. The logical
count is not a measurement of its cgroup quota, CPU affinity or available
cores. No Docker installation, daemon exposure or change to the existing
GPU experiment queue was made. The official Docker harness path therefore
remains unavailable in this container; a future custom runner must state
which execution and separation guarantees it actually implements.

## Acquired public development inputs

Three deliberately selected CPU tasks have small NumPy/SciPy interfaces:

| Task | Public material | Contract to implement later |
|---|---|---|
| Label-efficient risk estimator | Twelve labelled development pools, 2,000 rows and two classes each | `Estimator`: sequential paid-label queries followed by a risk estimate |
| Shortest valid CI for squared calibration error | Twenty-four development settings in three draws, plus the public generator | `ece2_interval`: bounded interval for top-k calibration error |
| Low-discrepancy subset selection | Eight three-dimensional point clouds and their subset sizes | `select`: distinct in-range point indices within a time budget |

This is a feasibility sample, not a random task sample or a contribution by
itself. The 59 additional public assets total 1,460,641 bytes. Development
labels and generator parameters are intentionally public under the task
instructions; they are not held-out evaluation answers. No intermediate or
final evaluator data, evaluator code, author hints or solutions were fetched.
The generic runner has not yet executed an adaptive candidate-development
loop on these tasks.

## Actual remote preflight

The deployed package contains 205 payload files plus a digest manifest. Its
SHA-256 is `44b35de3c9746a7a0317a006f2aab7b78186032a4fa14840a768da2f1985d7cd`.
The designated server ran the packaged preflight script with Python 3.13.5,
NumPy 2.5.3 and single-thread numerical-library settings. It verified all
202 acquired public files, then checked the following:

- All twelve pools have the declared array shapes, dtypes, finite valid
  probability vectors, normalized rows and in-range labels.
- All eight clouds have the declared sizes, three coordinates in the unit
  cube and valid requested subset sizes.
- The unchanged public CI generator produces the declared arrays for each
  of the twenty-four settings at its middle grid point. Each setting is
  generated twice with the same specified seed; all twenty-four pairs are
  exactly equal. This executes forty-eight generator calls.

The preflight completed with zero external connection attempts, zero model
calls and zero grader calls. It does not test CI coverage, establish the
generator's mathematical estimand, compute risk-estimation reward, evaluate
star discrepancy or reproduce the official benchmark. The midpoint and
seed checks are API diagnostics, not independent task samples.

NumPy 2.5.3 differs from the original per-task requirements: the risk task
pins 2.3.2, while the CI and subset tasks pin 2.5.2. The observed replay is
within the tested version only. Separate frozen task environments and an
actual evaluator are still needed before comparative method experiments.
No SciPy-dependent function was imported or tested in this preflight.

## Evidence and next scientific requirement

`autoresearch_exam_task_specs_v1.json` and
`autoresearch_exam_public_assets_v1.json` enumerate exact acquired files.
`autoresearch_exam_public_input_preflight_v1.json` is the byte-identical
remote report. The deployment receipt records the archive, report and
script hashes. The previous official scorer study still covers only its
twelve CLI tests; this preparation does not broaden that claim.

A fifth paper still requires a distinct research-agent decision question,
appropriate existing decision-policy baselines, a frozen experimental
comparison, actual adaptive agent runs and held-out evaluation. Generic
holdouts, anytime curves and grader-time accounting already appear in the
official harness. The executable public inputs remove one feasibility gap;
they do not establish novelty or meet those scientific requirements.
