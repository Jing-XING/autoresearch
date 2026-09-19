# Native airline compensation controls

Executed 19 September 2026. These are constructed workflow diagnostics using
unchanged public benchmark tools, not an official task benchmark or a model
evaluation. The final run completed 25 cases and passed a separate database
snapshot/ledger recomputation. No deployed airline or payment service was used.

## Native domain and declared contract

The source is [tau2-bench](https://github.com/sierra-research/tau2-bench/tree/b7ea9074c1cba482b30687fecdb5c8425fd6f619),
with canonical source/data manifest digest
`d07cc342f43894f866d1fd151fdd1ed996976cb194299e2d87913bc5bc8ee349`.
Each server startup verifies all 302 source files listed in that manifest.
The official airline unit-test fixture was separately fetched at the same
commit, SHA-256
`3c2c621f7fae1117903ce84dc11abbbd0136118de51a297276422e70f263cc6d`.
Its existing local copy differs only in CRLF normalization; the experiment
uses the fetched original bytes. Only pytest registration decorators are
removed when loading the two fixture-construction functions. Native tool
classes, Pydantic models and their method bodies are not patched.

The first profile is the official single-flight/card-payment test input.
The second explicitly extends it to the fixture's two connecting flights,
using a 100-unit certificate plus a 144-unit card payment. It is a constructed
extension, not a second randomly sampled benchmark task. Direct native
booking/cancellation preflights passed for both profiles.

The declared cancellation contract is cancelled reservation status and zero
net amount in that reservation's payment ledger. Full database restoration,
seat inventory and payment-instrument restoration are measured separately.
The pinned tool explicitly leaves seat release unimplemented; unchanged
seat availability is therefore **not** counted as failure of this declared
contract. Cancelled reservations and refund-history entries are retained.

## Transport and matrix

All calls use actual stdio MCP with SDK 1.30.0 and the native tool-generated
input schemas. A local wrapper adds four declared cancellation conditions:
normal cancellation; an invalid-ID native exception before effects; successful
cancellation on a disposable database copy; and an injected acknowledgement
exception after actual cancellation. The copy-only condition returns the
native cancellation payload from the copy while retaining the live database.

Two profiles × four conditions × three client configurations give 24 cases:
RAC with adapter 0.3.2 defaults; the same RAC with a diagnostic raw-client
`handle_tool_errors=False` setting; and unchanged agent-saga's native
upstream transport/proxy. RAC revision is
`068c327ab3f9b79a86a39503946e26320b74b97a`; agent-saga revision is
`4310ff570e60c42c081ae216e87a1ccb093525d4`. Compensation pairs/policies and
explicit rollback boundaries are supplied by the experimenter. Neither
automatic discovery nor a model's rollback decision is credited.

RAC stores this adapter's content list as a Python-literal string inside
`result.raw`. The main matrix uses a disclosed bounded literal decoder in
the developer state mapper to recover the actual returned reservation ID.
It does not assume the predictable fixture ID. agent-saga extracts the ID
from the actual MCP `structuredContent` using its declared policy.

An additional normal single-flight RAC control omits the stored-result
decoder. It reports success/COMPENSATED, but the native cancellation handler
is never called and the reservation stays active. This diagnoses the complete
configured integration, not proof that every developer mapper must fail.

## Observed outcomes

Both profiles have the same qualitative result below. The cancellation
contract is recomputed from saved native database states.

| Cancellation condition | RAC default | RAC raising control | agent-saga | Contract met |
|---|---|---|---|---|
| Normal | success; COMPENSATED | success; COMPENSATED | clean; COMPENSATED | Yes |
| Native error before effect | success; COMPENSATED | CriticalFailure; remains COMPLETED | incomplete; COMPENSATION_FAILED | No |
| Disposable-copy cancellation | success; COMPENSATED | success; COMPENSATED | clean; COMPENSATED | No |
| Error after actual effect | success; COMPENSATED | CriticalFailure; remains COMPLETED | incomplete; COMPENSATION_FAILED | Yes |

An exception-producing rollback has no returned success report; its missing
report is recorded as null, not imputed as a boolean. The after-effect error
shows that reported failure does not establish absence of the intended effect.
That conservative failure record is not itself treated as a framework defect.

For all eight profile/fault groups, the three clients leave exactly equal
database states. In all six profile/client normal-versus-copy comparisons,
the native cancellation payloads are identical despite different persisted
states. This demonstrates the limits of response-only validation in these
fixtures; no new general impossibility theorem is claimed.

## Validation, runtime and retained attempts

`validate_tau_airline_compensation.py` checks all 25 raw state hashes,
the complete condition grid, eight WAL files, the unchanged original
reservations, seat deltas and ledger/status oracle. It is a separate
recomputation by the same research process, not independent human review.
Parent external-connection attempts were zero; 17 standard-library loopback
socket-pair operations were allowed. Child processes prohibit external socket
connections. A fresh process inventory found no remaining native-airline MCP
server after completion.

The child uses the existing local isolated tau2 environment with MCP 1.30.0
and nine dependencies added; no pre-existing dependency was replaced by that
installation. A 90-package inventory and install report are retained. Remote
GPU environments and frozen experiment revisions were not changed.

Two partial attempts are retained and excluded from the final case count:
the first stopped on a strict expected-call assertion after the unadapted
mapper prevented native cancellation; the second stopped because the test
harness did not yet catch RAC's `CriticalFailure`. The final harness records
exception outcomes and saves each completed case incrementally. No upstream
source was changed to accommodate these observations.

Artifacts: `tau_airline_compensation_preflight_v1.json`,
`tau_airline_compensation_probe_v1.json`,
`tau_airline_compensation_validation_v1.json`, and
`tau_airline_compensation_raw_receipt_v1.json`. The validated ZIP contains
65 entries, 201,975 bytes, SHA-256
`f488704ad00d9910dbf332df54580a995ade3fc874b66e73df34d97edb529aaf`.
It includes final/partial raw states, logs, fixture bytes, scripts and runtime
inventory. Framework/domain sources remain pinned upstream dependencies.

Reproduction requires restoring those fixed repositories, the source manifest
and fixture at the recorded paths, then using the recorded parent/child
environments. Run the preflight, the stdio comparison, the separate validator
and the packager in that order in a fresh output workspace. Scripts refuse
to overwrite versioned evidence outputs. The current launcher records its
Windows interpreter path explicitly; porting it requires a declared launcher
path adaptation, not a claim that the old run used a different environment.

These results extend a boolean fixture to native reservation, inventory,
payment-history and certificate state. They still cover two chosen inputs
and imposed faults, not representative deployed workloads, autonomous model
behavior, fault frequency, recovery under concurrency or a new recovery method.
