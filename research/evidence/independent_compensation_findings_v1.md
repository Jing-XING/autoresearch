# Independent recovery controls: scope and retained attempts

Executed on 2026-09-19. These controls broaden the incomplete recovery paper;
they do not constitute a new recovery algorithm, a model benchmark, or an
estimate of defects in deployed systems.

The source revisions are [SagaLLM 2781c33](https://github.com/genglongling/SagaLLM/tree/2781c33edc4005b066671d5dc3cad157fae14f11)
and [agent-saga 4310ff5](https://github.com/thomasjgeorge23/agent-saga/tree/4310ff570e60c42c081ae216e87a1ccb093525d4).
Every downloaded file is checked both against its SHA-256 and the pinned Git
blob identifier. Source files are imported unmodified. Selection is motivated
by the earlier RAC diagnosis and is not a random sample of frameworks.

## Eight native MCP controls

agent-saga's actual `UpstreamServer` exchanges initialize, tool-list and tool-call
messages with the same MCP SDK fixture used in the RAC experiment. A policy
explicitly pairs `book` with `cancel`, taking the booking ID from the forward
arguments. The local write-ahead log is started and closed according to the
upstream CLI lifecycle. The experiment explicitly requests rollback; it does
not evaluate automatic transaction-boundary inference or the outer
client-facing `serve_stdio` loop.

Both an explicit MCP error and a server exception serialized as an MCP error
produce `COMPENSATION_FAILED`, a non-clean report and a residual booking.
RAC with the tested default 0.3.2 adapter had reported success on these same
fixture states. Successful cancellation passes both systems. A silent no-op
produces a positive report and residual booking in both. Four forward controls
add success, explicit error, server exception and no-op observations: the two
errors become `UNKNOWN`, followed by a successful explicitly requested
compensation using the original argument. The fixture happens to have no
effect on those failures; the library does not assume this fact.

The validator verifies eight raw state hashes, eight persisted WAL hashes,
their terminal records and four identical cross-system fixture states. This
is a mechanism comparison, not evidence of general agent-saga superiority.

## Six SagaLLM coordinator controls

The actual coordinator receives scripted duck-typed agents with a declared
dependency graph. It recognizes raised rollback exceptions, but prints
completion after a normally returned error dictionary or a silent no-op.
The generic dictionary is not a documented typed-error contract, so its
interpretation is an interface convention, not a claimed protocol violation.
When the current forward operation raises after writing the local flag, it
is absent from the completed-agent list and receives no compensation. A
before-effect exception provides the corresponding no-residual-effect control.
No model-driven SagaLLM agent or published benchmark is reproduced.

## Failed harness attempts and dependency disclosure

An initial import failed because the pinned agent-saga `retry.py` imports
Pydantic although the project metadata lists no required dependencies. The
isolated environment added Pydantic 2.13.5. No MCP case ran in that attempt.
A subsequent harness omitted the required WAL start call and failed before
its first forward tool call; this is an experimenter setup error.

The first complete output (`independent_compensation_probe_v1.json`) contains
two invalid SagaLLM forward fixtures: their dependent was missing from the
registered graph, so sorting failed before the intended operation. The v2
harness corrects the graph and asserts the executed event sequence. It repeats
all fourteen cases. The v1 output and source are preserved; repeated cases
are not additional independent observations. Manuscript findings use v2 only.

No external parent connection was attempted, no model was called, and the
SDK child prohibits external network connections. The final process inventory
found no remaining fixture process. The raw ZIP receipt pins 38 files,
including v1/v2 states and WALs and the superseded harness source. It is ignored
by Git and must accompany any complete reproducibility release.

`scripts/fetch_independent_compensation_sources.py` verifies existing sources;
`--fetch-missing` retrieves only the pinned public files. The existing experiment
and validation scripts use exclusive output creation. A reproduction must use
an isolated copy and distinct output filenames so published records are not
overwritten. The raw source snapshot required by the probe is included in
`results/remote/independent-compensation-v2-evidence.zip`.
