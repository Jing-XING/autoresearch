# Speculative Actions: complete paired-trajectory slice audit

19 September 2026. Repository commit:
[`dc938b9ef7474caf07fe4ad16549c1fa8c7d268c`](https://github.com/naimengye/speculative-action/tree/dc938b9ef7474caf07fe4ad16549c1fa8c7d268c).

## Acquisition and population

The fixed recursive Git tree contains 188 `normalobs.json` / `simobs.json`
files under `hotpotqa/run_metrics/`, totaling 1,771,046 bytes. All were
downloaded, JSON-parsed, and checked against Git blob hashes; their SHA-256
values are in `speculative_action_trajectory_manifest_v1.json`. No file in
this selection was omitted. Other repository artifacts are outside this
slice. The upstream README describes included trajectories as illustrative
samples, so this is not a reconstruction of the full experimental sample.

The slice contains 94 complete normal/simulated pairs and 336 steps.
Within every pair the actual question text agrees, and observations,
thoughts, actions and timings have equal lengths. All recorded timings
are finite and nonnegative. The audit does not interpret sequential tool
durations as concurrently observed end-to-end latency.

| Observable | Count |
|---|---:|
| Normal search steps | 227 |
| Normal lookup steps | 30 |
| Normal finish steps | 79 |
| Non-search steps with a preceding step | 109 |
| Those steps whose simulated observation exactly repeats the preceding simulated observation | 109 |
| Lookup steps with an explicit result | 4 |
| Lookup steps reporting no more results | 26 |
| Explicit lookup result bodies found verbatim in the preceding simulated observation | 4 |
| Explicit lookup result bodies found verbatim in any earlier logged normal search observation in the same trajectory | 0 |

The four result-bearing lookup steps occur in three trajectories. They are
not four independent task outcomes. All comparison records are stored by
path, step index and content hash in
`speculative_action_trajectory_audit_v1.json`; the original text remains in
the pinned upstream files rather than being republished as factual claims.

## Interpretation of state dependence

The exact repetition of simulated observations on lookup/finish steps is
consistent with the inspected runner returning the retained `sim_obs`
field, which `guess_step` updates for searches. It must not be interpreted
as a fresh predicted lookup result.

The four matching lookup bodies provide an archival signature consistent
with the shared-page mechanism exercised in the previous offline controls.
They do **not** prove that each result came exclusively from a model's
prediction: logged real search observations contain only page summaries,
and full Wikipedia page state is absent. The archive also lacks enough
generating-source provenance to assert that the currently pinned runner
produced every file. We therefore do not claim a measured contamination
rate, a causal accuracy loss, or a correction to a published success rate.

## Task identity is not the folder identifier

The 94 normal prompts have 94 distinct question-text hashes, despite only
34 distinct terminal folder identifiers. Twenty-one identifiers map to
multiple questions across configurations. Normal/simulated pairs within
each folder agree; the mismatch is across separately configured runs.
Comparing configurations as paired tasks using these folder numbers would
be invalid for this slice. No paired configuration effect is computed.

An additional exact-method control executes the pinned
`HistoryWrapper.reset` against a recording environment. Requested
`idx=42` is forwarded as `idx=None`; seed, return-info and options are
also replaced with the method's hard-coded values. The pinned inner
`HotPotQAWrapper.reset` chooses a random data index when given `None`.
Only the forwarding method was executed here: no Gym wrappers, dataset
sampling, model or provider client was run. This code path can explain
the identifier mismatch, but the archival provenance limitation prevents
asserting it as the demonstrated cause of these particular saved files.

## Reproduction and research decision

From the repository root, after restoring the source slice with
`python scripts/fetch_speculative_action_sources.py`, run:

```text
python -m scripts.fetch_speculative_action_trajectories
python scripts/audit_speculative_action_trajectories.py
```

The fetcher verifies existing files; the analyzer refuses to overwrite its
versioned evidence output. Run in a fresh checkout/output workspace for a
new reproduction. Both use the Python standard library. The executed
analysis made no model or network calls; only the separate acquisition
step accessed public GitHub content.

The next study cannot use this archive as a matched efficacy baseline.
It needs fresh task-identity checks, genuinely independent normal state,
and measurements separating prediction agreement from committed task
success. Those are requirements for a valid experiment, not a claim that
state isolation or identity checks constitute a novel algorithm. This
audit strengthens the mechanism evidence but does not secure a fourth
publication-quality contribution.
