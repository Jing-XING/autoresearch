# Speculative Actions: state-flow and evaluation-scope audit

19 September 2026. This is a bounded code diagnosis, not a new algorithm,
an independent paper, or a reproduction of the authors' benchmark results.

## Pinned material

Official repository: <https://github.com/naimengye/speculative-action>,
commit `dc938b9ef7474caf07fe4ad16549c1fa8c7d268c`.
`speculative_action_source_manifest_v1.json` records SHA-256 and Git blob
hashes for 17 selected files (123,646 bytes). Every downloaded file was
checked against the pinned recursive Git tree. No upstream provider client,
API credential, installation script or benchmark launcher was executed.
`scripts/fetch_speculative_action_sources.py` restores/verifies this slice.

## What the code actually measures

The HotPotQA README describes side-by-side real/predicted observations and
subsequent action-match analysis. `runner.py:191–218` executes the normal
tool and then the simulation sequentially. The simulation uses the normal
action, while separately predicted candidate actions are logged. This is
an analysis harness; timings from it should not be relabeled as observed
concurrent end-to-end acceleration. No contradiction with the paper's
analytic latency model is established by this observation.

The e-commerce README directs experiments to its static path.
`tool_calling_agent_static.py:247–300` walks a saved baseline trajectory,
invokes speculative prediction on assistant dialogue turns, estimates user
typing time from word count, and returns the saved baseline reward/info.
That returned reward is not fresh evidence that speculative executions
preserve task success. The separate `tool_calling_agent_reduce.py` path
passes the same `env` to its background worker and foreground call
(`348–351`), executes speculative actions through `env.step` (`122`), and
by default appends their returned messages (`326–331`). These are static
code observations; neither retail path was executed in this audit.

## Executed HotPotQA state probe

`scripts/probe_speculative_state_isolation.py` executes exact AST method
bodies extracted from the verified `WikiEnv` and `HotPotQARun` classes.
It bypasses constructors/imports and substitutes explicit deterministic
model outputs, a local page fixture, minimal wrappers and formatting
templates. The selected methods and AST hashes are enumerated in
`speculative_state_isolation_probe_v1.json`. No real model, Wikipedia
request, Gym wrapper, HotPotQA data file or benchmark reward was used.

The four direct controls use one synthetic page with two matching
sentences:

| Intervening simulated call | Next authoritative lookup |
|---|---|
| None | First sentence from the authoritative page |
| Search with a differing predicted page | First sentence from the predicted page |
| Lookup of the same keyword | Second authoritative sentence; the cursor advanced |
| Finish with a predicted answer | Environment is already terminal with that answer |

The full extracted `webthink` method was then run with a fixed three-action
sequence: search, lookup, finish. Baseline execution reads the authoritative
page. Enabling the original shared simulation flow makes the next normal
lookup read the predicted page. A diagnostic control snapshots/restores
the authoritative fields after each simulation, retaining only its explicit
`sim_obs` output slot; this restores both the baseline normal observations
and the final tracked state exactly. The control is not a proposed novel
method and makes no concurrency, persistence or performance claim.

Mechanism: `WikiEnv.guess_step` assigns the predicted response to `page`
and `obs` even when `simulate=True` (`environment.py:84–97`). The normal
and simulated steps receive the same environment in `webthink`. Lookup
subsequently consumes that shared page and cursor. The direct finish case
isolates the environment API behavior; the runner's simulation of finish
normally follows its authoritative finish, so that direct case is **not**
evidence of a reachable early-finish failure in this runner.

The seven controls demonstrate a deterministic state dependency. They are
not seven independently sampled tasks, an estimated benchmark error rate,
or evidence that a published aggregate result changes. A real model may
choose a different next action, and a correct prediction can mask page
contamination while step/cursor state still changes.

## Harness correction and limitations

The first local probe attempted a fresh deep copy for each speculative
call. Its adapter omitted constructor initialization of `sim_obs`; the
copy control raised `AttributeError` before an output artifact was written.
That is a probe-construction error, not an upstream failure. The failed
script was preserved under `results/probes/speculative-state/`; the final
probe initializes the output slot and uses the stated snapshot/restore
control. The final run completed all assertions and wrote the exclusive
versioned evidence file. Only the final seven controls are counted.

This audit supports requiring isolated normal trajectories when measuring
speculative action agreement. It does not establish a novel state-isolation
algorithm: rollback, shadow execution, dependency validation and isolation
already appear in the closest literature. Before a fourth paper can be
claimed, this question needs a wider independent evaluation and a distinct
contribution beyond repairing this implementation. Do not spend the GPU
queue on a generic async-clarification method on the strength of this probe.
