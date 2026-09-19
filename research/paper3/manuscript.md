# When Tool Errors Survive but Recovery Records Do Not: Auditing Agent Compensation Interfaces

**Working manuscript, incomplete.** The results below are executed software
probes and an archival artifact audit. They are not model-task performance
results, estimates of deployed failure prevalence or an independently validated
new recovery algorithm. The evidence is not yet sufficient for submission.

## Abstract

Agent recovery components depend on tools, adapters and execution logs agreeing
about whether an operation succeeded. We examine these agreements in a fixed
release of RobustAgentCompensation (RAC), separating compensation execution,
returned status, recorded state and the residual effect in a controlled
environment. Local probes reproduce a rollback path that ignores normally
returned error results. Executing the paper's archived source confirms the
same mechanism under current dependencies. A native stdio MCP study identifies
two further integration boundaries: a schema-declared compensation pair is
not discovered, and a returned error ToolMessage can coexist with an internal
COMPLETED record. Six matched executions with an older MCP adapter distinguish
the effect of exception-raising behavior from that of returning an error
message. Successful and silent-no-op controls show the limits of status checks.
Separately, an audit of all 280 JSON files in the published archive identifies
duplicate aggregate records and nested progress snapshots; a conservative
structured-status screen finds no observed instance of the constructed
status contradiction. These results support a narrowly scoped, reproducible
integration diagnosis. They do not reproduce the published model benchmark
or establish that the observed interface failures occurred in its trials.

## 1. Introduction

Recovering from an unsuccessful agent action can require more than retrying
the failed call. Earlier actions may have modified external state and need
compensation. A recovery manager typically records those actions, maps them
to compensating tools, executes the compensations and updates its log. Each
step introduces an agreement between components: what is recorded, which
result constitutes failure, and what a successful compensation establishes.

Tool libraries represent failures in several ways. A function can raise an
exception, return a typed error message, or place an application-defined error
inside ordinary content. An adapter may deliberately turn an exception into
an observation that allows an agent to continue. That transformation is
reasonable for a conversational loop, but a downstream recovery component
must interpret the resulting value consistently. It cannot assume that every
normal return means the requested state transition occurred.

This study investigates a concrete implementation rather than proposing a
new general transaction protocol. The subject is the public RAC code and its
archived artifact. We ask which failures can be demonstrated through actual
component execution, which depend on the selected dependency version, and
whether the released experimental traces independently show those failures.
Separating these questions prevents a unit-level counterexample from becoming
an unsupported claim about benchmark performance or deployed reliability.

## 2. Observational distinctions

We record four separate properties of an operation: whether invocation raises,
what error status its returned object carries, how the recovery log classifies
the operation, and whether the fixture's intended state change occurred.
These observations need not agree. A normal return may carry an explicit error;
a positive status may accompany a silent no-op; an empty log may coexist with
a prior untracked effect.

Our fixture uses a single active-booking flag. A successful forward operation
sets it, and its specified compensation clears it. This makes residual effect
observable independently of the recovery report. It is a narrow local contract,
not a demand that real compensating transactions restore every historical
database byte. In particular, the absence of recorded actions establishes only
that the manager has an empty plan. It does not certify that no external effect
exists.

We reserve the phrase reported successful rollback with residual effect for
a run that actually attempts the declared compensation, reports success and
leaves the flag active. We describe failed automatic discovery separately.
The latter returns an accurate description of its empty recorded plan, while
failing to track the workflow's schema-declared compensatable operation.

## 3. Subject, versions and experimental method

The current RAC source is fixed at commit
`068c327ab3f9b79a86a39503946e26320b74b97a`. Its source blobs are checked against
the pinned Git tree before import. The published Zenodo archive is separately
verified by its released MD5, a recorded SHA-256 and ZIP integrity checks.
Archived Python files are extracted without modification and tested separately.
No probe rewrites the third-party implementation.

The real LangChain experiments use `langchain-core==1.6.3`. Native MCP tests
add `mcp==1.30.0`, `langchain-mcp-adapters==0.3.2` and `pydantic==2.13.5` in an
isolated environment. A further comparison changes only the adapter to
`0.2.2` through an isolated import overlay. These are declared experimental
configurations, not reconstructions of the authors' original dependency set.
The archive does not supply a complete dependency lock for that reconstruction.

All tests use local constructed tools, without a model or a live booking
service. Connection guards prohibit external network access. The native MCP
fixture uses actual stdio subprocesses, SDK initialization, schema exchange
and tool invocation. Its state file persists across the adapter's per-call
server sessions. Windows event-loop socket pairs are recorded separately from
MCP transport. The parent sees no external connection attempts.

The probe series covers distinct execution paths, not independent random
samples. Twelve initial core/adapter cases isolate returned status; 24 cases
exercise retry and alternative-action interceptors; 21 use actual LangChain
StructuredTool/ToolMessage objects; eight additional controls isolate invocation
format. Fourteen archived-source rollback cases address source-version scope.
The native MCP study contains twelve execution controls and one unmodified
automatic-discovery workflow, followed by six matched older-adapter executions.
We do not sum these numbers into a task-level sample size or a defect rate.

## 4. Returned errors and rollback records

The core rollback path calls the compensation executor and immediately marks
the original action compensated. It does not inspect the returned action
result. Raised exceptions instead reach its failure branch. The author-provided
LangChain executor catches a tool exception and returns an error action result.
Composing these two components therefore changes an exposed failure into a
reported successful rollback, with the fixture's booking still active.

Supplying the implementation's explicit error-detection strategy does not
change this rollback branch. A diagnostic executor that rejects its documented
error result prevents the false success for explicit failures, but cannot
detect a silent no-op that returns a positive status. This control separates
an interface mismatch from a missing postcondition observation. Neither
status checking nor postcondition checking is claimed as a new method.

The archived-source tests reproduce the ignored-result mechanism in the
published code, using fourteen selected combinations of executor and tool
behavior. Direct exceptions are exposed, whereas an adapter-produced error
result can be ignored. The dependency environment remains current, so this
is evidence about execution of the archived branch under the stated setup;
it is not evidence that a corresponding error occurred in a published trial.

## 5. Native MCP boundaries

### 5.1 Automatic pair discovery

The fixture declares a `book -> cancel` relation through the input-schema
extension documented by RAC. That extension survives in the converted
tool's `args_schema`, and RAC's own parser recognizes the dictionary when
called directly. Its high-level client nevertheless discovers no pair in
the tested configuration.

The source path explains the mismatch. Raw-schema discovery expects an older
client's `_sessions` attribute. The fallback obtains `get_input_schema()`,
which returns a Pydantic model class here, while the pair parser expects a
dictionary. Returning that value also bypasses the later `args_schema` branch.

In the unmodified-factory workflow, a successful booking sets the flag but
the wrapper records no action. Rollback then reports an empty plan and
attempts no cancellation. This observation concerns one documented declaration
form and these dependencies. It does not show that every metadata form or
every application configuration fails.

### 5.2 Error status present in the returned message

Twelve further native executions explicitly register the compensation pair
using the manager's public method. This disclosed diagnostic intervention
isolates execution semantics after discovery; it is not counted as successful
automatic discovery. The client, wrapper, executor and recovery manager remain
unchanged.

| Constructed behavior | Default adapter | Exception-raising diagnostic |
|---|---|---|
| Successful cancellation | Flag cleared; compensated | Same |
| Cancellation returns MCP execution error | Flag active; compensated | CriticalFailure; not compensated |
| Cancellation handler raises | Flag active; compensated | CriticalFailure; not compensated |
| Cancellation returns success without effect | Flag active; compensated | Same |
| Forward error through plain arguments | Content list; log COMPLETED | Raised error; log FAILED |
| Forward error through full tool-call envelope | Error ToolMessage; log COMPLETED | Raised error; log FAILED |

In the last row, the returned ToolMessage explicitly retains its error status.
The wrapper still marks the action completed because its result check handles
strings and dictionaries, but not that message type. Plain-argument invocation
returns content blocks instead, which the same predicate also does not handle.
The rollback path's ignored normal return supplies the second discrepancy.
The MCP SDK converts a server-handler exception into an execution-error
response; this case does not simulate a transport outage.

### 5.3 A controlled package-version comparison

The diagnostic exception mode requires a raw-client replacement because the
RAC factory does not expose the adapter's error-handling flag. We therefore
also execute six matched cases with adapter version `0.2.2`, leaving the other
packages, server and RAC source fixed. Under the older adapter's default,
both cancellation errors raise CriticalFailure and both forward errors produce
FAILED records. Successful cancellation and the silent no-op behave as before.
Automatic pair discovery remains unsuccessful.

This comparison isolates a package-version effect in the constructed workflow.
It does not establish which adapter version the RAC paper used. In particular,
the remaining packages are still current, and the newer default was released
after the paper. Attributing this MCP-specific behavior retrospectively to
the original reported model experiments would be unwarranted.

## 6. What the released experiment archive shows

We separately inspect all 280 JSON files in the published archive. The audit
distinguishes execution traces from aggregate records and progress snapshots.
The 13 aggregate JSON files contain 1,272 record occurrences but only 224
distinct canonical records. Thirty-five REALM snapshots share one start time
and form an exact event-prefix chain. Neither group can be pooled as independent
trials merely by counting files or rows.

A conservative screen asks whether a recorded successful event has an
immediate structured result carrying an explicit contradictory error status.
It decodes JSON-object strings but does not infer failure from arbitrary
natural-language text, nested fields or an unobserved post-state. It finds
zero instances under that definition. Nine compensation events are marked
successful without an independent state-restoration observation. Thus the
archive neither corroborates the constructed mismatch's occurrence nor proves
that all compensations achieved their intended effects.

The archive is also insufficient for an independent reproduction of every
reported domain and evaluator. The linked anonymous task artifact was expired
when accessed. We retain these access and provenance limits rather than
imputing successful outcomes from token counts or choosing the best duplicate
record. No published success-rate claim is revised by our local probes.

## 7. Related work and limits

[RAC](https://arxiv.org/abs/2605.03409) is the subject of the audit and already
studies compensation in agent workflows. [Verified Tool Calls](https://arxiv.org/abs/2608.02645)
is direct prior work on validating tool effects. [Bugs in Modern LLM Agent
Frameworks](https://arxiv.org/abs/2602.21806) already studies execution semantics
and interface compatibility. The [Agent Crash Test](https://github.com/pavloparaschakis/agent-crash-test)
artifact likewise includes controlled tool faults and effect oracles.
Our controlled failures do not establish novelty for fault injection,
typed errors, postcondition verification or framework bug taxonomies.

The current evidence is concentrated in one recovery implementation. Its
several paths and two source versions do not constitute replication across
independent recovery systems. The operations are constructed, the declarations
and failure modes are selected, and the experiments contain no autonomous
model decisions. An external effect oracle is available by construction.
These conditions make the mechanisms inspectable but limit deployment claims.

## 8. Provisional conclusion

The executed probes demonstrate specific inconsistencies between returned
tool errors, automatic compensation discovery and recovery records. They also
show why recording the complete dependency combination matters: an adapter's
error-delivery default changes the same constructed workflow's recovery result.
The archival analysis prevents these findings from being misrepresented as
observed benchmark failures. Broader independent comparisons, a complete
bibliography and submission-quality positioning remain necessary before this
working manuscript can support a publication claim.
