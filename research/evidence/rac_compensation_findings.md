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
Retry and alternative-action paths have similar unchecked returns in source,
but are not covered by these twelve executed cases. No claim about their
empirical behavior is included here. The original paper's performance and
released summary tables remain unreplicated.

Two additional neighboring papers were screened in primary sources.
[ParaRecover](https://arxiv.org/html/2609.12345v1) already evaluates error
localization and recovery across parallel tool trajectories; error recovery
evaluation itself is not novel. [FinHarness](https://arxiv.org/html/2605.27333v1)
studies inline finance-agent safety monitoring. Its phrase “compensation
verification” appears in an executive-payroll access example, not a proposed
compensating-action verification mechanism. A keyword match must not be used
as evidence that these mechanisms are identical.
