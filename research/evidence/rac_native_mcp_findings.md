# Native MCP integration audit

Executed on 2026-09-19. These are constructed local software tests, not LLM
benchmark episodes, production incidents or estimates of failure prevalence.

## Actual components and protocol

The unchanged RAC revision is
`068c327ab3f9b79a86a39503946e26320b74b97a`; every imported source file is
checked against the previously pinned Git tree. A separate environment uses
`langchain-mcp-adapters==0.3.2`, `langchain-core==1.6.3`, `mcp==1.30.0` and
`pydantic==2.13.5`. The official adapter wheel SHA-256 is
`094e6b3096dbcc408417d5722f6915f164772e50c502ae3d8989405bf12c3c84`.
The install report and five executed dependency files have recorded hashes;
the latter also match their installed distribution RECORD entries.

The [official package documentation](https://pypi.org/project/langchain-mcp-adapters/)
describes a default that exposes MCP execution errors as error tool messages,
with `handle_tool_errors=False` retaining exception-raising behavior. This
current version was released after the RAC paper. The experiment therefore
tests compatibility with these exact current dependencies, not the original
authors' historical environment.

Our low-level MCP server implements a local booking flag, logs calls to a
dedicated state file and declares `book -> cancel` through RAC's documented
`x-compensation-pair` input-schema extension. Actual stdio subprocesses,
initialization, tool discovery, schema transfer and invocation are exercised.
The shared state file preserves the fixture across the adapter's per-call
server sessions. No mock replaces the MCP serialization or RAC client.

## Automatic discovery: one unmodified-factory execution

The declared pair survives in the converted tool's `args_schema`, and RAC's
own parser recognizes it when supplied that dictionary directly. The
high-level client nevertheless discovers no pairs. The source path explains
the mismatch: `_fetch_raw_schemas` expects the old client's `_sessions`
attribute; fallback `_get_tool_schema` uses `get_input_schema()`, whose value
here is a Pydantic model class, while `parse_mcp_schema` checks a dictionary.
The source returns from this branch before trying the preserved `args_schema`.

Without any manual repair, invoking `book` activates the fixture, records
zero actions, and a subsequent rollback returns `success=True` with
`No actions to rollback`. No cancellation is attempted. That message accurately
describes the empty recorded plan; it does not verify that the environment has
no residual effect. This is one schema form and one dependency combination,
not evidence that every MCP compensation declaration fails.

Evidence: `rac_mcp_discovery_probe_v1.json` and
`scripts/probe_rac_mcp_discovery.py`.

## Execution semantics after explicit diagnostic registration

To isolate the next boundary, twelve separate executions explicitly register
the pair with RAC's public `add_compensation_pair` method. Every record
discloses this intervention. The original client, wrapper, executor and
recovery manager remain unchanged.

| Path | Default adapter behavior | Diagnostic exception-raising control |
|---|---|---|
| Successful cancellation | Flag cleared, record compensated | Same |
| Cancellation returns `isError=True` | Flag remains active, rollback reports success | CriticalFailure, record not compensated |
| Server cancellation handler raises | SDK returns an MCP execution error; flag remains active, rollback reports success | CriticalFailure, record not compensated |
| Cancellation reports success without changing state | Flag remains active, rollback reports success | Same |
| Forward booking error, plain argument invocation | Content list returned, log marks COMPLETED | Error raised, log marks FAILED |
| Forward booking error, complete tool-call invocation | ToolMessage retains `status=error`, log still marks COMPLETED | Error raised, log marks FAILED |

The last row is particularly specific: status information is present in the
returned object, yet the tracking decision ignores it. The wrapper's error
predicate handles strings and dictionaries, but not ToolMessage or the
content-block list returned for a plain-argument invocation. Rollback also
ignores a normally returned compensation result, consistent with the earlier
core probes. A silent no-op is a separate observation: no response-status
check alone can establish that the requested state transition occurred.

The exception-raising control replaces the client's raw tool list with tools
loaded using `handle_tool_errors=False`; the RAC factory does not expose that
flag. It is a diagnostic intervention, not a default end-to-end configuration
or a proposed new recovery method. The server exception is an application
execution error, not a simulated network/transport failure.

Evidence: `rac_real_mcp_probe_v1.json`, `rac_mcp_probe_validation_v1.json`,
`scripts/probe_rac_real_mcp.py`, `scripts/rac_mcp_fixture_server.py` and
`scripts/validate_rac_mcp_probes.py`. The validator checks all twelve fixture
states and the separate automatic-discovery execution. Thirteen executions
must not be described as thirteen independent defects.

## Runtime and inference limits

A separate six-case comparison installs the official `0.2.2` adapter wheel
into an isolated import overlay while holding the server, RAC source,
LangChain core, MCP SDK and Pydantic versions fixed. With that older adapter's
default behavior, both cancellation-error modes raise CriticalFailure and
both forward-error invocation forms are marked FAILED. Actual cancellation
and silent-no-op behavior remain unchanged. Automatic pair discovery still
fails. This agrees with the exception-mode diagnostic, but now the manipulated
variable is an actual package version rather than a runtime flag. Evidence:
`rac_mcp_adapter_version_probe_v1.json` and
`scripts/probe_rac_mcp_adapter_version.py`; all six checks pass. The initial
overlay import was blocked by local directory permissions before a tool ran;
the successful run reads the same official installation with the required
local filesystem access. It does not alter the `0.3.2` environment.

This comparison does not establish the dependency versions used by the RAC
authors. In particular, the other dependencies remain current. Neither the
native MCP wrapper mismatch nor the change in its default error path should
be retrospectively attributed to the paper's original model experiments.

No model or external service is called. The parent audit observes zero
non-stdlib connection attempts. Eight Windows asyncio loopback socket pairs
are explicitly allowed only at the standard library's socketpair call site;
these are event-loop infrastructure, not MCP network transport. Each child
installs its connection prohibition after event-loop construction. An initial
preflight that blocked Windows' own socketpair failed before a fixture tool
ran; the guard was corrected, and that infrastructure failure is not a RAC
outcome.

The prior archived-trajectory review still finds zero instances under its
conservative structured-status criterion. These local executions neither
change that result nor establish that the paper's model runs experienced
these failures. A publication-level contribution requires broader independent
evidence and comparisons beyond discovering integration branches that need
repair.
