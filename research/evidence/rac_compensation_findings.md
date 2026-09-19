# RAC compensation-status counterexample

Status: executed CPU software probe, 2026-09-19. This is not an LLM benchmark,
an estimate of failure prevalence, or a replication of the RAC paper's results.

## Fixed source and executed evidence

The upstream source is [research-rac](https://github.com/wso2-incubator/research-rac),
commit `068c327ab3f9b79a86a39503946e26320b74b97a`.
The probe verifies the downloaded official Git tree's SHA-256 and every source
blob's Git object hash before importing the unchanged core and adapter.
The source archive SHA-256 is
`9e97b642c1ca014bfc2a3f35f3a8263790e2e56fee16658d3e856168246a3f5c`.

Run `scripts/probe_rac_compensation_status.py` with `--source`, `--tree` and a
new `--output` path. The evidence file
`rac_compensation_status_probe_v2.json` records the source hashes, probe hash,
runtime, all twelve outcomes and asserted controls. The earlier v1 run is
retained; v2 additionally pins the manifest and records the probe hash.
Neither run invokes a model, paid API or external booking service.

## Observed mechanism

In `core/recovery_manager.py:412`, rollback invokes the compensation executor
without inspecting its return value. It immediately marks the original action
compensated at line 413. An exception reaches the failure branch, but an error
returned normally does not. The probe explicitly supplies the author's
`ExplicitStatusStrategy`; this does not change that rollback path.

The unchanged `langchain_adaptor/adapters.py:140` catches a tool exception and
returns `SimpleActionResult(status="error")`. Consequently, a tool failure
which the direct executor correctly exposes becomes a reported successful
rollback after passing through this author-supplied adapter. This is a concrete
interface mismatch within the fixed implementation, not an inference from
the paper's algorithm description.

Each fixture begins with one active synthetic booking and a completed `book`
record. `cancel` either removes it, throws, returns an explicit error without
removing it, or returns success without removing it. We observe the fixture
state independently of the recovery report.

| Compensation behavior | Direct protocol executor | Author LangChain adapter | Adapter with diagnostic status check |
|---|---|---|---|
| Actual cancellation | Clean state; reports success | Clean state; reports success | Clean state; reports success |
| Exception | Residual booking; reports failure | Residual booking; reports success | Residual booking; reports failure |
| Explicit error payload | Residual booking; reports success | Residual booking; reports success | Residual booking; reports failure |
| Success response, no state change | Residual booking; reports success | Residual booking; reports success | Residual booking; reports success |

The diagnostic check only rejects an explicit outer error status or the
fixture's documented inner error payload. Its inability to detect a silent
no-op is deliberate: successful transport and positive status do not prove
the state transition. These twelve selected cases are not random samples;
do not turn the table into a benchmark percentage.

## Research interpretation and limits

The result motivates checking whether failure semantics survive every
recovery boundary. It does not establish that status checking is a new method.
Postcondition checks, idempotency and compensating transactions already have
substantial prior work. In particular, [Verified Tool Calls](https://arxiv.org/abs/2608.02645)
is a direct comparator, and [RAC](https://arxiv.org/abs/2605.03409) already
studies agent compensation. A stronger contribution would require evidence
across real integration paths and a mechanism beyond fixing this branch.

The probe uses a minimal object implementing the tool `invoke` interface; it
does not run a LangChain agent or exercise every LangChain/MCP configuration.
Retry and alternative-action paths are not covered by these twelve cases;
the separate interceptor probe below checks those paths. The paper's performance and
released summary tables remain unreplicated.

Two additional neighboring papers were screened in primary sources.
[ParaRecover](https://arxiv.org/html/2609.12345v1) already evaluates error
localization and recovery across parallel tool trajectories; error recovery
evaluation itself is not novel. [FinHarness](https://arxiv.org/html/2605.27333v1)
studies inline finance-agent safety monitoring. Its phrase “compensation
verification” appears in an executive-payroll access example, not a proposed
compensating-action verification mechanism. A keyword match must not be used
as evidence that these mechanisms are identical.

## Original interceptor follow-up

`scripts/probe_rac_interceptor_recovery.py` executes the unchanged
`ToolCallInterceptor` and `RecoveryManager` together. An initial tool call
throws a timeout before any effect; recovery then either retries it or invokes
a configured static alternative. Each recovery route has success, exception,
explicit error-status and silent-no-op controls, with no check, a status check,
or an exact fixture-state check: 24 deliberately constructed cases in total.

In both original unchecked routes, a returned `SimpleActionResult` with
`status="error"` produces `InterceptResult(success=True, recovered=True)`
and a `COMPLETED` transaction record, despite no effect. The recovery result
still contains the error status. Thus the mismatch reaches the unchanged
interception boundary; it is not confined to a standalone manager report.
Successful recovery and raised-error controls behave as expected. Status
checking rejects the explicit error but still accepts a silent no-op. An
exact fixture-state check rejects both, using privileged access available
only in this constructed control.

Evidence: `rac_interceptor_recovery_probe_v1.json`, with source and probe
hashes, all cases, and passed assertions. An initial setup assertion revealed
that the author's retry counter starts at one and stops at
`attempt >= max_retries`; setting the policy to two makes exactly one recovery
call. The finalized probe asserts that call count in every case. No author
code was patched. No full agent rollout or model-message conversion is tested,
and these cases are not independent replications across frameworks.

## Real LangChain tool and message classes

The follow-up `probe_rac_real_langchain_tools.py` uses actual
`langchain-core==1.6.3` `StructuredTool`, `ToolException` and `ToolMessage`
classes, with `pydantic==2.13.5`, in a separate virtual environment. The package
version is published on [PyPI](https://pypi.org/project/langchain-core/1.6.3/).
Every installed wheel's version and SHA-256 is retained in
`rac_real_langchain_tools_probe_v1.json`. Network connections are denied by
the probe; no attempted connections or model calls occurred.

Seven fixed behaviors are exercised across rollback, retry and static
alternative paths: real success, runtime exception, unhandled ToolException,
handled ToolException, explicit error ToolMessage, error dictionary and silent
no-op. All 21 fixture checks complete. This is integration coverage of the
same mechanism, not 21 independent bugs or framework samples.

For retry and alternative routes, an actual error `ToolMessage` reaches the
original interceptor as the recovery result, but `to_tool_message` converts
it into an outer message with `status="success"`. The original inner error
status and the absent fixture effect are recorded. A tool configured with
LangChain's `handle_tool_error=True` also produces a normal returned value
that the recovery path counts as successful. Handling `ToolException` is an
intended LangChain facility; this observation concerns how RAC interprets
that returned value. Raw runtime exceptions and unhandled ToolExceptions
remain failures in the retry and alternative controls.

These executions close the earlier mock-interface limitation for the tested
tool/message classes. They still do not run a complete LangGraph agent,
evaluate recovery planning by an LLM, or measure real-service failure rates.
