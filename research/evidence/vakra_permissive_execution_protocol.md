# Fixed-prompt executor-sensitivity control

Registered before neural execution of `vakra-permissive-v1`, after inspecting
the complete `vakra-crossdomain-v1` batch. This is a post-outcome diagnostic
on known tasks, not independent confirmation of a research method.

Repeat all 240 episodes from the three-domain replication, preserving the
first twenty queries in each database, checkpoint files, greedy decoding,
prompt conditions, query order, one shard per worker, and four-GPU waves.
Use 20 model-call attempts, at most 20 executed tool-call attempts, 512 output
tokens per generation and a 32768-token input ceiling. The earlier adapter
also executes at most twenty tools because it permits one per model call.
Initialization/warmup calls are setup in both runs and excluded from the
agent's budget. Do not remove the five preidentified ambiguous tasks or
change the frozen SQL interpretation of any question.

The sole intended intervention is runtime acceptance of a generated batch.
Parse every complete tool block and validate every name against the supplied
schema before executing any call in the batch. Execute accepted calls in
their emitted order, without argument repair, reference access, placeholder
substitution or inferred dependencies. Append every response, including MCP
validation errors. A transport exception stops the batch and episode, with
the completed prefix preserved. An unknown name rejects the entire batch.
Malformed/unknown responses retain the five-error termination rule, with
feedback referring to complete tool blocks rather than one block.

An oversized batch executes no calls. If some budget remains, report the
remaining number and allow another model turn within the fixed model budget.
If no budget remains and the model still requests tools, terminate with a
separate tool-budget outcome. Spending the last tool call does not itself
prevent a subsequent final answer. Budget rejection is recorded separately
from syntax/schema errors and cannot add model-call opportunities.

**Prompt constraint retained intentionally:** the official system message
says to make at most a single call per iteration. Both executor conditions
receive exactly that instruction, including the coverage suffix where
applicable. Thus this control tests a permissive executor's response to
instruction violations, not a model complying with a newly authorized batch
protocol. It must not be called a faithful reproduction of the default
official hosted agent, which uses LangGraph. The official adapter source
supports recording lists of calls, but its hosted execution is not run here.
No claim that the original instruction violations were purely system bugs.

Report all outcomes by domain/model/prompt, paired with the earlier strict
run: termination, protocol violations, executed calls, budget rejection,
tokens, generation cost, SQL-interpretation answer labels and reference
compatibility. Reuse the frozen answer cards and policy. Report first
generation equality and unchanged-prefix checks to diagnose unintended
differences. Different call IDs are logging metadata; tokenizer template
serialization should be checked before execution. Changes after a first
batch/error are consequences of the intervention, not proof of better
reasoning. The matched input/output limits remain material constraints.

No prompt tuning or configuration changes within a registered batch. Keep
the old revision and raw archives intact. A failed preflight permits a new
explicit deployment revision before launching; a failed neural batch remains
reported and is never silently overwritten or selectively rerun.

## Completed CPU checks before neural execution

Fourteen focused adapter/native-template tests passed. Real MCP fixtures use
the original assistant texts through the first rejected batch in all 32
affected episodes. Twenty-nine batches execute 83 calls whose responses
match the prior direct MCP diagnostic exactly; three batches are rejected
before execution for unknown names. Original executed prefix responses also
match. These fixtures are scripted text with zero neural tokens and thirty
fixture steps; they are not generated continuations or answer scores.
