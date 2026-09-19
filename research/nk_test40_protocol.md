# Paired NK-schema transfer extension

This is a disclosed adaptation experiment, not a reproduction of the full
Negative Knowledge method. No new curation or target outcome was observed
when this protocol was frozen on 2026-09-19. It does not change the preceding
560-episode study or make its already registered tasks independent again.

The question is whether adding the existing execution-boundary instruction
changes downstream utility within a structured NK-schema curator. The two
arms share source data, schema, 1,024-token curation ceiling, curator model,
eligible pool, retrieval decision, target task and execution settings. They
differ only by the boundary instruction at source curation. Source generation
is greedy; this is one curation realization, not multiple independent banks.

## Registered endpoint

Use all 40 official telecom test tasks already named in the previous test
registration. Run both NK conditions on Qwen3-4B-Instruct-2507 and
Qwen2.5-7B-Instruct: 40 tasks × 2 conditions × 2 checkpoints = 160 episodes.
Each condition/model has two fixed task shards; condition order is reversed
between the two shards. Exact model files, task data, source code and source
choice artifacts are hashed in the accompanying registration.

The official solo policy, native tool prefix and evaluator remain unchanged:
greedy inference, 512 new tokens per generation, 60 steps and 5 protocol
errors. No task criteria, source suffix, future reward or target answer is
included in model inputs. All tasks must have no NL_ASSERTION reward component.
Target exceptions and premature terminations remain unsuccessful in the
primary denominator. An incomplete worker grid is not analyzed as complete.

The original 74-source bank is restricted by visible zero-reward eligibility
to 70 sources before retrieval. The fixed 40 ticket-based choices select five
records with reuse 13/3/8/1/15. Relative to the previous 74-source selection,
one target selects a different source. These choices are shared by both arms
and must be checked again against the assembled bank before model loading.

## Invalid memories and controls

Generation errors, malformed JSON, invalid taxonomy, excessive text and
ceiling hits are retained. Source choice does not depend on their validity.
A selected invalid memory is represented as an empty experience under the
same quoted-data wrapper. No alternate retrieval, repair, generation retry,
task exclusion or replacement run is permitted on that basis. The wrapper
means this fallback is not byte-identical to the preceding no-memory arm.

The primary comparison is `nk_schema_boundary` versus `nk_schema`, separately
for each checkpoint. Prior no-memory and generic-curation results may be
contextual comparisons only after task, model, source, runtime and input
compatibility is checked. Differences from the earlier experiment's pool and
256-token curation ceiling prevent interpreting cross-study differences as
the isolated effect of representation. This protocol adds no new no-memory
runs and claims no full-method superiority from the paired contrast.

## Required reporting

Report all 40 outcomes per checkpoint/condition and all paired gains, losses,
joint successes and joint failures. Separate protocol/runtime failures and
curation validity from task success. Report source and target token costs and
the number of distinct injected memories, including empty ones. Break down
results by the five shared-source groups, plus group-equal and leave-one-group-
out descriptive sensitivity. These few reused sources and related task
families do not justify treating 160 rows as independent observations.

If one arm produces an invalid selected memory, that difference remains part
of the registered intervention's utility, not evidence about boundary
reasoning alone. An analysis restricted to pairs with valid memories is
selected after treatment and can only be descriptive. No benefit is assumed.

## Execution order and preservation

The new target supervisor waits for `nk-prefix-curation-v1` to complete and
all GPUs to be idle. It then assembles the bank with strict four-shard
coverage, registered code/model hashes and raw-reply validation, and launches
eight workers across four GPUs. Limits are twelve hours waiting and four
hours execution. Partial outputs remain available on failure; no existing
batch is restarted or mutated. Successful deployment and CPU preflight are
not evidence of model performance. The target experiment must finish and be
audited before any result is added to the manuscript.
