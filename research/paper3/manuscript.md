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
message. An independent agent-saga transport reports explicit MCP compensation
errors as failures on the same fixture, while silent no-ops remain undetected.
SagaLLM coordinator controls separately expose its exception-based completion
convention. These comparisons delimit the diagnosed mechanisms rather than
establishing a general framework ranking.
Twenty-five native airline controls and a 2,000-reservation direct-call census
distinguish cancellation contracts, strict state idempotence and errors after
completed effects.
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

This study investigates concrete implementations rather than proposing a
new general transaction protocol. Its primary subject is the public RAC code
and its archived artifact, with selected independent implementation controls.
We ask which failures can be demonstrated through actual
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

Independent controls pin agent-saga commit
`4310ff570e60c42c081ae216e87a1ccb093525d4` and SagaLLM commit
`2781c33edc4005b066671d5dc3cad157fae14f11`. Downloaded source blobs are verified
against their Git trees. Eight agent-saga controls use its unmodified
`UpstreamServer` and `SagaMCPProxy` with the existing SDK fixture, a local
write-ahead log, an explicitly supplied compensation policy and rollback
boundary. The outer client-facing stdio loop is not exercised. Six SagaLLM
controls execute its unmodified coordinator with scripted agents, not its
model-driven agent. The isolated parent environment adds colorama 0.4.6,
graphviz 0.21 and pydantic 2.13.5; the child uses the existing MCP environment.
These fixtures were selected after the RAC diagnosis, so their selection is
not independent of the observed mechanism.

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

### 5.4 Independent native MCP transport control

[agent-saga](https://github.com/thomasjgeorge23/agent-saga/tree/4310ff570e60c42c081ae216e87a1ccb093525d4)
provides a useful positive control. Its stdio transport raises on an MCP
`isError` result. Using exactly the same fixture script and four rollback
behaviors as the RAC default-adapter study produces the following observations.
The validation checks raw fixture-state equality across implementations and
consistency between agent-saga's report and persisted log.

| Compensation behavior | Residual booking | RAC default reports success | agent-saga reports clean |
|---|---|---|---|
| Successful cancellation | No | Yes | Yes |
| Explicit MCP error | Yes | Yes | No |
| Server exception serialized as MCP error | Yes | Yes | No |
| Successful response with no effect | Yes | Yes | Yes |

The two explicit errors become `COMPENSATION_FAILED` in agent-saga. In its
forward-error controls, the operation is recorded as `UNKNOWN`, and the
explicit rollback uses the booking identifier supplied in the original
arguments. This conservatively preserves the possibility of an effect even
though the constructed failing forward operation makes none. A silent no-op
still produces a positive rollback report with a residual booking. Thus
correct error propagation addresses one boundary without proving an external
postcondition. The comparison does not test crash recovery, connector services,
automatic pair discovery or overall framework reliability.

### 5.5 An exception-based coordinator interface

The independent [SagaLLM coordinator](https://github.com/genglongling/SagaLLM/blob/2781c33edc4005b066671d5dc3cad157fae14f11/src/multi_agent/saga.py)
calls rollback on agents whose forward calls returned before a subsequent
exception. With scripted agents, a raised compensation error produces a
warning; a normally returned error dictionary and a silent no-op both produce
a printed rollback-completion message while leaving the local effect active.
The dictionary is an experimenter-defined value, not an advertised SagaLLM
error protocol. This result demonstrates its exception convention and should
not be presented as violation of a declared typed-result contract.

Two further controls raise before and after the forward effect. In both,
the currently failing agent is absent from the coordinator's completed list
and its compensation is not attempted; only the after-effect case leaves a
residual booking. These are scripted coordinator paths, not a reproduction of
SagaLLM's model benchmark. The contrast with agent-saga's explicit `UNKNOWN`
state illustrates why a failed return and an absent effect are different
facts. This distinction is established in prior recovery work and is not a
new algorithmic contribution here.

### 5.6 Native reservation and payment-ledger state

The preceding binary booking fixture makes transport behavior inspectable,
but does not exercise a business tool's coupled state. We therefore add
unchanged [tau2 airline tools](https://github.com/sierra-research/tau2-bench/blob/b7ea9074c1cba482b30687fecdb5c8425fd6f619/src/tau2/domains/airline/tools.py)
on the official unit-test database. One input is its single-flight/card-payment
fixture; the other is an explicitly constructed two-flight extension paid
with a certificate and a card. Source hashes and fixture bytes are pinned.
These are selected workflow controls, not sampled official tasks or an
evaluation of an autonomous airline agent.

We define the cancellation contract as cancelled reservation status and
zero net amount in the reservation payment ledger. Full database equality
is unsuitable: cancellation retains the reservation and refund entries, and
the pinned implementation explicitly omits seat release. We report inventory
and payment-instrument restoration separately without counting these omitted
effects as violations of our narrower declared contract.

Actual stdio MCP exposes the native tool schemas and methods. Four imposed
conditions locate the failure before or after the relevant effect: normal
cancellation; a native invalid-ID exception; cancellation on a disposable
database copy; and an acknowledgement exception after cancellation of the
actual database. Equal native return payloads are serialized for the normal
and copy-only conditions. We compare RAC's default adapter, its diagnostic
raising configuration, and agent-saga, giving 24 executions across two inputs.

The result ID is obtained from the actual booking output. RAC's stored result
wraps this adapter's content list in a Python-literal `raw` string; the main
matrix therefore explicitly supplies a bounded decoder in the developer
mapper. agent-saga uses its configured structured-content path. A twenty-fifth
control omits the RAC stored-result adaptation: it reports COMPENSATED/success,
but no native cancellation invocation occurs and the reservation remains
uncancelled. The adapted normal control completes cancellation. This contrast
exposes a result-storage boundary without crediting our adaptation as automatic
parameter extraction.

Both booking profiles produce the following outcomes:

| Imposed cancellation condition | RAC default | RAC raising control | agent-saga | Native cancellation contract |
|---|---|---|---|---|
| Normal | Success | Success | Clean | Satisfied |
| Native error before effect | Success | Raises CriticalFailure | Incomplete | Unsatisfied |
| Disposable-copy effect | Success | Success | Clean | Unsatisfied |
| Error after actual effect | Success | Raises CriticalFailure | Incomplete | Satisfied |

RAC's raising condition leaves the action COMPLETED and supplies no returned
rollback report; we retain the exception and do not turn absence of a report
into a measured boolean. agent-saga records COMPENSATION_FAILED on the error
conditions. Failure after the actual effect illustrates why an error flag
cannot establish that compensation did not occur; conservative uncertainty
is not classified as a defect.

Independent state recomputation within our research process validates all
25 saved databases and eight WAL files. Each of the eight input/fault groups
has exactly equal final database states across clients. For six matched
input/client normal-versus-copy comparisons, native cancellation payloads
are equal while persisted database states differ. Thus these controls
separate correct error transport from verification of the requested effect.
They establish neither an error prevalence estimate nor a novel general
isolation or postcondition-verification algorithm. Both partial setup attempts
and their causes are retained, and repeated cases are not counted as extra
independent observations.

### 5.7 Contract-preserving retries can still change recorded state

An acknowledgement error after cancellation raises a separate question:
what changes if the same cancellation is repeated? We register a direct-call
census of every reservation in the pinned public airline database before
execution. The population contains 2,000 reservations, all initially having
one payment-history entry and unset status: 965 gift-card payments and 1,035
credit-card payments. This is a finite input population with homogeneous
ledger structure, not 2,000 independent agent tasks or a deployed workload.

For each reservation, we restore its initial value before each of three
diagnostic policies. The first cancels once. The second cancels three times,
with an experimenter-imposed acknowledgement exception after each native
return. The third cancels once with the same imposed exception, then calls
native `get_reservation_details` and stops if cancelled status and zero signed
ledger net are observed. These calls execute unchanged native methods directly;
they do not pass through MCP or a recovery framework. We do not attribute
the chosen retry behavior to RAC or agent-saga.

| Policy | Cancels / reads per reservation | Final ledger entries | Cancellation contract satisfied | State equal to single cancellation |
|---|---:|---:|---:|---:|
| Single cancellation | 1 / 0 | 2 | 2,000 / 2,000 | Reference |
| Three cancellation attempts | 3 / 0 | 8 | 2,000 / 2,000 | 0 / 2,000 |
| Authoritative read before retry | 1 / 1 | 2 | 2,000 / 2,000 | 2,000 / 2,000 |

The native method appends the negation of every existing payment-history
entry, including previously appended negative entries. The successive ledger
sizes are therefore 2, 4 and 8 for every reservation, while all 10,000 observed
post-cancellation states retain zero signed net and cancelled status. Strict
target-state equality fails under repeated cancellation even though the narrow
contract remains satisfied. Increased gross ledger entries do not establish
duplicate external refunds or financial loss: this tool records ledger values
and does not execute an external payment. Nor does its interface promise strict
state idempotence. These observations delimit the consequence rather than
labeling every repeated write a failed recovery.

The read-based diagnostic produces exactly the same target state as single
cancellation for all records, with one extra read and two fewer cancellation
calls than the three-attempt control. Its observer is authoritative and
synchronous by construction. This is an upper-bound diagnostic, not a novel
policy or evidence for reliability under stale reads or concurrent writers.
A separate validator computes append-negation transitions directly from the
original database, without importing the tool implementation or measurement
function. It validates every saved target field and all ledger nets. The
initial shared database hash is restored after all per-record resets. A ZIP
path-handling correction is retained separately from the unchanged raw run;
it does not create additional observations.

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

[RAC](https://arxiv.org/abs/2605.03409v1) is the subject of the audit and already
studies compensation in agent workflows. [Verified Tool Calls](https://arxiv.org/abs/2608.02645)
is direct prior work on validating tool effects. [Where Agent Frameworks Fall
Short](https://arxiv.org/html/2602.21806v4) already studies interface compatibility
and explicitly motivates version-aware API-sequence testing. The [Agent Crash Test](https://github.com/pavloparaschakis/agent-crash-test)
artifact likewise includes controlled tool faults and effect oracles.
Our controlled failures do not establish novelty for fault injection,
typed errors, postcondition verification or framework bug taxonomies.

The evidence remains concentrated in a small set of chosen interfaces. The two independent implementations
add narrowly selected coordinator and transport controls, not a representative
sample of recovery systems or matched end-to-end tasks. The operations are constructed, the declarations
and failure modes are selected, and the experiments contain no autonomous
model decisions. Native MCP airline controls add coupled business state but
only two chosen booking profiles. The separate 2,000-record retry census
covers the full public initial reservation population, whose ledger structures
are homogeneous; it adds no autonomous decisions or framework comparison.
Their status/ledger contract is narrower than full
restoration, and no official airline task success rate is reported. An external effect oracle is available by construction.
These conditions make the mechanisms inspectable but limit deployment claims.

## 8. Provisional conclusion

The executed probes demonstrate specific inconsistencies between returned
tool errors, automatic compensation discovery and recovery records. They also
show why recording the complete dependency combination matters: an adapter's
error-delivery default changes the same constructed workflow's recovery result.
The independent transport control shows that explicit MCP errors can be
propagated consistently with recovery status; the no-op control separates
that property from verified restoration. Native airline controls extend the
distinction to a coupled reservation/payment ledger: equal successful payloads
can accompany different persisted states, and exceptions can follow completed
cancellations. The native retry census further separates a preserved status/net
contract from exact state idempotence, without inferring financial harm from
ledger growth. The archival analysis prevents these
findings from being misrepresented as observed benchmark failures. Broader
realistic workflows and submission-quality positioning remain necessary before
this working manuscript can support a publication claim.
