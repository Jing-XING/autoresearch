# Successful Calls, Insufficient Evidence: Scope and Coverage in Tool-Using Agents

**Research manuscript; not submission-ready.** The empirical studies reported
here are complete. The saved-record artifact has passed Windows and Linux
reanalysis; independent answer adjudication, public artifact release and
submission-format verification remain unfinished. The preceding
manuscript is preserved verbatim in `study_record.md` as a detailed study record.

## Abstract

Successful tool execution does not establish that an agent has enough evidence
to answer a question. We study public relational-tool tasks, separating
execution validity, answer correctness and identification by the observed
trace. A fixed coverage reminder has mixed domain effects. In a matched
240-episode executor control, accepting sequential call batches gives
Qwen2.5 twelve additional final answers but only one net additional correct
answer under fixed SQL interpretations. A separate SmolLM3 study produces
six correct answers among 220 scored executions. A larger Qwen3 checkpoint
scores 35/55 versus 38/55 with the reminder on the known tasks.
A prospective 420-episode expansion across four further databases yields
original/reminder counts of 24/49 versus 20/49, 14/49 versus 15/49, and
27/49 versus 29/49 across three checkpoints. All conditional paired
intervals include zero; omitting Disney reverses both positive aggregate
differences. Forty-three input-budget failures and incomplete requested lists
further delimit interpretation. On two prospectively length-selected tasks,
larger generation budgets complete four previously truncated answers but leave
eight incomplete responses unchanged. Full-transcript database replays provide two
examples where a correct original answer is not identified under an explicit
admissible intervention. One retrieves every requested output value yet
applies an incorrect predicate. A bounded price-swap search adds no
correct-answer witness. These results support reporting execution,
correctness and evidence sufficiency separately, with explicit limits on
counterfactual admissibility and resource budgets. They are diagnostic
results on public training tasks, reviewed by one unblinded assistant;
they establish neither official benchmark scores, population failure
prevalence nor a new controller's superiority.

## 1. Introduction

A tool response is both a computational result and evidence for an agent's
next decision. These roles can diverge. A count operation may execute correctly
on an incorrectly scoped table. A preview may contain only true values while
omitting part of a requested list. Even retrieving every output value can
leave the answer dependent on an unchecked predicate. Evaluating call validity
misses the first two problems; evaluating answer agreement can miss the third.

Relational tools make these distinctions inspectable. A server keeps complete
relations behind handles while exposing schemas, row counts and previews.
Filtering, sorting, aggregation or retrieval can recover further evidence,
but large observations consume context and complete answers can exceed output
limits. Evaluation must distinguish what an interface could reveal, what an
agent actually observes and what its output channel can express.

Accidental correctness and trace-conditioned determinacy are established
concerns in [semantic SQL evaluation](https://aclanthology.org/2020.emnlp-main.29/)
and [database access control](https://www.usenix.org/conference/osdi22/presentation/zhang).
Our contribution is an empirical diagnosis in interactive tool use: matched
controls expose different failure sources, and complete observation replays
provide checkable, explicitly local counterexamples. We do not introduce
determinacy, pagination or a universal grounding verifier.

We ask three questions. **RQ1:** Does a fixed scope-and-coverage reminder
transfer beyond its development database? **RQ2:** How much do an executor
restriction and the generation budget account for apparent answer failures?
**RQ3:** Can a correct answer remain unidentified by the complete observed
trace under a declared class of alternative database states?

The prospective comparison answers RQ1 with heterogeneous effects and sign
reversals under domain removal. Executor and output-budget controls answer
RQ2 differently: more final responses yield little net correctness gain,
whereas four selected lists exhibit exact token-prefix evidence of output
truncation. Two native-tool replays answer RQ3 by preserving all target
observations despite changing the required answer. Retained inadmissible and
unsuccessful searches limit generalization from those positive examples.

## 2. Evidence identification

Let D denote a database, q a fixed interpretation of the requested computation,
and h the agent's observable history. For a declared admissibility condition A,
let C_A(h) contain states that satisfy A and reproduce h under the actual tool
semantics. The answer is identified by h within A precisely when q has the
same value on every state in C_A(h). This concerns information in the trace,
not the absence of useful model priors or the correctness of its final answer.

A replay witness is a D' in A with q(D') different from q(D) but exactly the
same observations under the recorded action sequence. We compare initialization,
ordered tool definitions, complete tool content and error flags. Equality of
selected fields or preview lengths is insufficient. For a deterministic policy
with identical fresh model state, observation equality preserves the next
action inductively. A stochastic policy additionally requires coupled random
choices; independently sampled trajectories need not match.

Admissibility carries substantive assumptions. A country-label edit can
preserve SQLite constraints while violating geographical knowledge used to
interpret a question. Our retained examples therefore declare which status
field may vary and which cells stay fixed. A witness refutes identification
within that class; failure to find one in a bounded search certifies nothing.
This is an application of established determinacy ideas, not a new theorem.

We separately record interaction termination, requested-value agreement and
local replay witnesses. A final response is not necessarily a correct answer,
and a correct value need not have a correct explanation. A preview can suffice
for positive membership while failing an exhaustive list; an exact aggregate
can suffice without reading every row, provided its scope is correct. No
aggregate grounding rate is inferred from the selected replay examples.

## 3. Experimental design

### 3.1 Environment, checkpoints and controls

We use public capability-1 training tasks from VAKRA, server commit
`c9e82dfe46aee016d2bfe3a0c8fed652760e4c0c` and dataset revision
`1388b9f1aaed887a73957eba651a6c2034010476`. Unchanged native MCP tools operate
on local database copies. Initialization uses the upstream reference-derived
relation or join, an oracle setup convention rather than agent planning.
Agents receive questions, tool schemas and the public initial preview, but
no reference program, SQL card or answer. VAKRA's own evaluation already
considers trajectories and grounding; our diagnostic labels are not its
[official scores](https://huggingface.co/blog/ibm-research/vakra-benchmark-analysis).

Every target starts with fresh system and user messages. Server registration
can persist within a worker, so replays preserve warmup and preceding tool
order. A logged universe switch activates dynamic getters before evaluation,
and tool schemas are refreshed. This workaround changes no data semantics.

The original condition retains the upstream system-prompt method. The reminder
appends instructions to distinguish previews from full columns, check requested
predicates, use filtered aggregates where appropriate, and disclose incomplete
evidence. Its exact text is in `autolab/vakra_native.py` and Appendix A below.
It was developed on world examples, then fixed for subsequent comparisons;
it is a simple instruction control, not a learned or verified controller.

The expansion uses Qwen3-4B-Instruct-2507, Qwen2.5-7B-Instruct and
Qwen3-30B-A3B-Instruct-2507 with local Transformers inference and greedy
decoding. Checkpoint files, dependencies, source and input identities are
hash-pinned. Smaller checkpoints use one A40 per worker; Qwen3-30B-A3B uses
two with all layers resident on GPUs. This is a checkpoint comparison,
not a controlled scaling experiment.

Primary runs allow twenty model attempts, twenty tool attempts, 512 new tokens
per generation and 32,768 input tokens. Over-limit inputs terminate without
silent truncation. The sequential executor accepts valid call batches and
counts every executed attempt; unknown tools or oversized batches are rejected
before partial execution. The earlier strict executor rejects multi-call
generations, following the prompt's one-call instruction. Tool errors,
malformed outputs and budget failures are retained.

### 3.2 Selection and study sequence

| Study | Task set | New model episodes | Role |
|---|---|---:|---|
| Initial observations | 4 world queries, 2 checkpoints | 8 | Development; one OOM |
| Matched development | 12 world queries, 2 checkpoints, 2 prompts | 48 | Includes the initial queries |
| Strict replication | 60 queries, 3 other databases, 2 checkpoints, 2 prompts | 240 | Fixed prompt transfer |
| Sequential executor | Same 60 queries and conditions | 240 | Post-outcome protocol control |
| SmolLM3-3B | Same 60 queries, 2 prompts, 2 executors | 240 | Checkpoint sensitivity |
| Qwen3-30B-A3B | Same 60 queries, 2 prompts | 120 | Known-task extension |
| Prospective expansion | 70 queries, 4 further databases, 3 checkpoints, 2 prompts | 420 | Primary transfer evidence |
| Larger generation budget | 2 expansion tasks, 3 checkpoints, 2 prompts | 12 | Registered length sensitivity |

Table 1. Overlapping studies, not independent task samples. CPU tool replays
and evaluator-authored acquisition controls are not new model episodes.

The initial replication selects the three smallest previously untested
non-world capability-1 databases by file size: computer_student, cars and
book_publishing_company, with twenty released inputs each. The expansion
excludes those and world, retains eligible files at most 5,000,000 bytes,
and selects four domains in seeded hash order. A fixed task hash ordering
selects at most twenty examples per domain: cookbook (20), Disney (20),
genes (10) and ice_hockey_draft (20). No task is replaced after answer review.
These are new to our experiments, not necessarily to pretraining. SmolLM3's
earlier floor motivated its omission from the expansion, so checkpoint
selection was informed by development.

### 3.3 Scoring and uncertainty

Before expansion predictions, reference SQL and task wording were inspected
to fix interpretation cards and an ambiguity mask. Twenty-one of seventy
tasks have recorded wording/reference conflicts or unresolved ambiguity.
All seventy remain in execution and cost accounting; forty-nine enter each
answer comparison, giving 294 scored and 126 separately reported ambiguous
executions. Long answers and failed runs receive no new exclusion. Missing
answers count as unsuccessful in the fixed denominator. Earlier three-domain
comparisons analogously retain 55 of 60 tasks in their frozen SQL subtotal.

One unblinded assistant read every complete response or recorded absence and
assigned requested-value labels against the cards. Correct values can be
credited despite faulty explanations; annotation reasons and sensitivity
labels disclose those cases. There is no independent human adjudication.
Identical final text in the executor comparison reuses its answer label;
changed responses are reviewed. Label reuse does not establish grounding.

We pair prompt outcomes by task and preserve domain-specific scored counts
when resampling. Expansion intervals use the exact finite distribution of
the ordinary within-domain paired bootstrap; earlier intervals use 10,000
resamples. These post-completion descriptive calculations condition on the
observed domains and assistant labels. They cover neither annotation error,
unseen domains nor generation seeds. Repeated runs and checkpoints are not
independent tasks. Detailed protocols and the full study sequence remain
in `study_record.md`.

## 4. RQ1: Mixed transfer of the coverage reminder

| Domain | Scored tasks per arm | Qwen3-4B original / reminder | Qwen2.5-7B original / reminder | Qwen3-30B-A3B original / reminder |
|---|---:|---:|---:|---:|
| Cookbook | 16 | 9 / 8 | 7 / 7 | 11 / 11 |
| Disney | 18 | 12 / 9 | 5 / 7 | 12 / 15 |
| Genes | 3 | 0 / 0 | 0 / 0 | 0 / 0 |
| Ice hockey | 12 | 3 / 3 | 2 / 1 | 4 / 3 |
| Combined | 49 | 24 / 20 | 14 / 15 | 27 / 29 |

Table 2. Requested-value matches against frozen interpretations. The genes
floor concerns only three scored tasks and does not establish equivalence.

All 24 workers exit successfully, producing the exact 420 registered records
and 210 verified initial prompt pairs. The complete archive retains 364 final
responses, forty protocol errors and nine finals at the generation ceiling.
The fixed 21-task ambiguity mask excludes
126 executions from answer accuracy while retaining all costs. Thus each arm
has 49 scored tasks across the same four databases.

| Checkpoint | Original correct | Reminder correct | Gains / losses | Difference (pp) | Conditional 95% paired bootstrap interval (pp) |
|---|---:|---:|---:|---:|---:|
| Qwen3-4B | 24/49 | 20/49 | 3 / 7 | -8.16 | [-20.41, 4.08] |
| Qwen2.5-7B | 14/49 | 15/49 | 4 / 3 | +2.04 | [-8.16, 12.24] |
| Qwen3-30B-A3B | 27/49 | 29/49 | 4 / 2 | +4.08 | [-4.08, 14.29] |

Table 3 reports aggregate differences and intervals. For this descriptive analysis, we compute the exact finite distribution of
the stratified paired bootstrap. Each task pair contributes -1, 0 or +1 for
reminder-minus-original correctness. Within each of the four fixed domains,
we resample its observed number of scored pairs with replacement, then sum
over domains and divide by 49. Convolution with rational probabilities gives
the 2.5th and 97.5th percentiles without Monte Carlo approximation. A small
exhaustive-resampling check validates this calculation. This is an ordinary
conditional bootstrap calculation, not a new estimator or a preregistered
hypothesis test. It does not cover unseen-domain sampling, model randomness
or annotation uncertainty, and we make no multiplicity-adjusted superiority
claim across checkpoints.

Every interval contains zero. Omitting Disney gives a net difference of
-1/31 tasks (-3.23 points) for each checkpoint, reversing the two positive
full-grid differences. Applying the eight previously disclosed conservative
Disney label changes, without adding new changes, produces counts 21/49
versus 19/49, 14/49 versus 14/49, and 25/49 versus 28/49 respectively; all
three corresponding conditional intervals still include zero. These checks
restrict the aggregate prompt-benefit interpretation. They do not establish
prompt equivalence or erase the within-domain gains and losses.

A separate post-hoc calculation addresses label sensitivity rather than
task resampling. We group exact final-answer text within the same question,
across prompts and checkpoints, and require one shared requested-value
judgment for every such group. The 364 present responses form 348 distinct
question/text groups; fifteen repeated groups cover 31 executions, with no
conflicting labels. This consistency check does not adjudicate correctness.
Missing final answers remain fixed failures. Flipping a group's binary
judgment changes all its occurrences together. Under this deliberately
hypothetical model, Qwen2.5's one-answer gain can be reduced to a tie by one
changed judgment and reversed by two; Qwen30B's two-answer gain requires two
and three changes, respectively. Qwen3's four-answer loss requires four
changes to reach a tie and five to reverse. These are minimum hypothetical
changes, not discovered annotation mistakes, error probabilities or a second
reviewer's decisions. Per-checkpoint extremal assignments need not be
simultaneously attainable across checkpoints.

The 21 ambiguous questions create a different boundary. For a hypothetical
70-question score, hold all 49 primary-task labels fixed and allow arbitrary
binary labels only for present ambiguous answers, tying exact duplicate text
and keeping absent answers unsuccessful. The resulting reminder-minus-original
net-difference envelopes are [-21, 13], [-15, 17] and [-10, 18] for Qwen3,
Qwen2.5 and Qwen30B. These are conservative label-relaxation envelopes,
not population intervals or sharp bounds over coherent SQL interpretations;
some extremal label assignments may have no common semantic interpretation.
They leave the original denominator and labels unchanged and reinforce that
the reported conditional 49-task comparison is not a score for all 70 tasks.

Forty-three expansion episodes terminate at the input ceiling, all in ice
hockey. Saved attempted-input counters range from 32,849 to 161,160 tokens,
after one to four successful generations. These are trace counters, not
independently retokenized measurements. No failure is discarded from a scored
denominator or from execution costs.

Disney illustrates the judgment boundary: some responses give a correct
count with wrong supporting film names, or name the required values while
adding contradictory statements. The eight-case sensitivity above changes
those specific judgments; it is not a bound on all possible annotation error.

Earlier known-task comparisons provide context rather than independent
confirmation. Strict Qwen3 changes from 29 to 32 correct answers out of 55;
strict Qwen2.5 changes from 19 to 21. Qwen3's difference reverses sign when
cars is removed. Qwen3-30B changes from 35 to 38, with a conditional interval
of [-3.64, 14.55] percentage points. SmolLM3 yields only six correct answers
among 220 scored executions, despite 221 final responses among 240 runs.
Its floor and 66 finals at the output ceiling limit cross-family inference.

## 5. RQ2: Executor restrictions and output capacity

### 5.1 Relaxing a call restriction

The strict executor contributes 99 of 128 protocol-error events in the
three-domain comparison. Repeating its full 240-episode grid with sequential
batch execution holds tasks, models, prompts and primary budgets fixed.
All first replies match; 37 trajectories diverge after model inputs change,
while 213 final answers remain byte-identical. This is a known-task sensitivity
study, not a replacement for the original results.

| Checkpoint / prompt | Strict finals | Sequential finals | Strict correct | Sequential correct |
|---|---:|---:|---:|---:|
| Qwen3 / original | 60/60 | 60/60 | 29/55 | 29/55 |
| Qwen3 / reminder | 60/60 | 60/60 | 32/55 | 32/55 |
| Qwen2.5 / original | 51/60 | 56/60 | 19/55 | 19/55 |
| Qwen2.5 / reminder | 49/60 | 56/60 | 21/55 | 22/55 |

Table 4. Twelve additional Qwen2.5 final responses produce one net additional
correct answer. Recovered answers can omit rows, misalign fields or use the
wrong scope. Under the original prompt, one correct recovered answer is
offset by loss of another; the reminder contributes the net gain.

Across Qwen2.5 prompts, protocol errors decrease from 127 to 31 and model
attempts from 542 to 498, while tool attempts increase from 315 to 455.
Input tokens decrease from 6,158,394 to 5,693,901 and output tokens from
54,925 to 53,818. These opposing resource changes prevent an unqualified
efficiency claim. A concurrent download prevents an isolated wall-time comparison.

### 5.2 Increasing the generation ceiling

Before predictions, reference inspection selected complete lists of 791
alcohol-free recipes and 129 hockey players. Three explicit serializations
with the pinned Qwen30B tokenizer measure 5,047-5,406 and 646-649 tokens,
respectively. These motivate a registered control but are not lower bounds
on every valid answer, nor measurements of the other tokenizers.

The twelve prospectively registered controls complete, with every worker
exiting successfully. The only configured budget change is 512 to 8,192 new
tokens on every target generation. Source versions, packages, model files,
templates, decoding, input limits and tool/step ceilings match the corresponding
primary configurations. Before target generation, the runner replays each
worker's warmup and preceding tool history without model inference and checks
the initial messages, ordered tool schemas and preview against the primary
record. Offline comparison independently confirms those initial inputs.
All twelve runs produce final answers, without protocol, input-limit or
step-limit terminations; none reaches the new generation ceiling.

| Task / checkpoint | Primary complete answers, original / reminder | Larger-budget complete answers, original / reminder | Final tokens, larger-budget original / reminder |
|---|---:|---:|---:|
| 791 recipe names / Qwen3-4B | 0 / 0 | 0 / 0 | 55 / 94 |
| 791 recipe names / Qwen2.5-7B | 0 / 0 | 0 / 0 | 60 / 86 |
| 791 recipe names / Qwen3-30B-A3B | 0 / 0 | 0 / 0 | 81 / 85 |
| 129 player names / Qwen3-4B | 0 / 0 | 1 / 1 | 617 / 619 |
| 129 player names / Qwen2.5-7B | 0 / 0 | 0 / 0 | 33 / 54 |
| 129 player names / Qwen3-30B-A3B | 0 / 0 | 1 / 1 | 626 / 628 |

Table 5 reports all twelve controls. All four recovered player lists contain exactly the 129 requested names,
checked by parsing their complete comma-separated bodies and comparing name
multisets with the frozen SQL card. The corresponding short-budget answers
end at 512 generated tokens and omit required names. The eight other final
responses are byte-identical to their primary answers: they still provide
only the first three entries, sometimes offering a future retrieval or
mentioning the total. This is insufficient under the unchanged complete-list
criterion. All twelve full responses are also read by the same unblinded
assistant; the mechanical check is not an independent semantic adjudication.

The observed match extends beyond initialization. All twelve pairs have
identical pre-final model inputs and generated token-ID sequences, identical
ordered tool names/arguments and response content/error flags, and identical
inputs to the final generation. Each short final's token IDs are an exact
prefix of the corresponding long final's IDs. Thus, in these four recovered
cases, the larger allowance extends the same observed final generation after
the same acquisition history. This supports a local attribution to the output
cap, stronger than merely noticing a response at the ceiling. The intervention
nevertheless changes all target generations; equivalent pre-final behavior
is an observed result here, not a guarantee for other tasks or checkpoints.

This contrast separates two limited explanations. Four player-list failures
are relieved by a larger generation allowance, whereas the eight unchanged
responses stop far below that allowance with incomplete lists. It does not
identify why those agents stop, establish that all needed evidence was acquired,
or demonstrate an autonomous acquisition repair. Two selected questions with
six model/prompt arms are not twelve independent task samples. No confidence
interval for a general recovery rate is inferred, and the twelve controls
do not replace or rescore the primary 420-run experiment.

### 5.3 Available evidence is not necessarily acquired

Cookbook task 015 provides a complementary control. Its six histories reach
the correct maximal-cooking-time filter but fail to list all ten ingredients.
An evaluator-authored native-tool continuation sorts names and repeatedly
filters above the last visible name. Ordinary keyset pagination exposes
remaining row counts 10, 7, 4 and 1 and recovers the complete answer in four
added calls. Including unsuccessful prefix attempts, total target calls are
six or seven, below the twenty-call ceiling.

Warmup, 224 preceding responses and the six target prefixes replay exactly;
the database hash remains unchanged. The continuation uses only tool replies;
offline SQL validates its result afterward. It requires stable data, non-null
strings, compatible ordering and accurate row counts. This proves feasible
acquisition for one selected question, not autonomous repair or a general
solution: the evaluator chose the checkpoint and column after review, and
no model continued from the repaired observations.

## 6. RQ3: Correct answers under indistinguishable observations

### 6.1 Two retained witnesses

In a world-database episode, Qwen3 with the reminder correctly returns Catalan
for the official language of Andorra, the highest-life-expectancy country.
Its four-row handle previews only three language rows. Changing the unseen
Spanish row's official-status flag preserves initialization, ordered schemas
and both complete recorded tool responses while changing the SQL answer to
Catalan and Spanish. All other data stay fixed. An earlier independent episode
would expose the changed value but is absent from the target's fresh model
messages. This claim is episode-local and conditional on allowing that status
change, not on immutable real-world language knowledge or cross-task memory.

The publishing witness removes an apparent remedy: full output retrieval.
Qwen3's original-prompt episode selects authors with contract values unequal
to `Y`, then retrieves both complete title and sales columns. Its seventeen
distinct pairs match the released data, where all 23 author flags are zero.
Under the explicit intervention admitting one flag change from `0` to `1`,
the required answer loses one title, but all target observations remain
identical: both zero and one differ from `Y`. Complete output retrieval does
not establish the predicate's correctness.

An evaluator-supplied equality filter with value `0`, followed by the same
getters, returns seventeen versus sixteen pairs and agrees with SQL in both
worlds. The interface can distinguish the states; the recorded agent did not.
This CPU control is not a new neural run or evidence of autonomous repair.
The positive witness is one of six from eight contract-related episodes;
the other five do not begin with correct answers.

### 6.2 Negative and restricted controls

A broad world-database search retains at most eight answer-changing candidates
from 2,048 seeded draws per task. Forty original trajectories replay exactly;
58 mutant databases and 141 replays yield seventeen observation-preserving
witnesses. Four involve correct original answers, but change geographical
membership, such as assigning a Japanese district to England. We reject
them as support for the retained claim: schema validity does not preserve
the background constraints used to interpret those questions.

An exhaustive narrower audit of 984 official-language flags recovers the
known Spanish-status witness. Of six witnesses across eight target episodes,
only that known case begins with a correct answer. This is a positive replay
control, not independent evidence of prevalence.

In cars, swapping two existing positive prices preserves their multiset,
other cells and declared keys. Across twenty tasks and eighty sequential
executions, 99 answer-changing mutants and 332 replays yield ten witnesses,
all for already wrong answers. None of the 43 correct-answer episodes gains
a witness; seven tasks have no retained candidate. This failed extension
limits generalization, while bounded search failure certifies no answer.

Two computer_student mutations preserve prescribed initial relations while
changing answers under the documented advisor relationship. Indistinguishability
holds only for operations on those relations and descendants. The live API
accepts other universe identifiers, and 14 of 27 alternative initializations
expose different full relations under each mutation. We make no impossibility
claim about the unrestricted interface or agents with external knowledge.

## 7. Related work

[Agents Don't Paginate](https://arxiv.org/abs/2608.26130v1) studies first-chunk
selection and a file-localization probe, including negative downstream results.
[Fabrication After Tool Failure](https://arxiv.org/abs/2609.14758v1) studies
reporting after unusable payloads and prompt-level defenses.
[How Good Are LLMs at Processing Tool Outputs?](https://aclanthology.org/2026.eacl-long.134/)
compares answer generation, executable processing and response representations.
Our reminder belongs to this established intervention space. Our controls
instead examine continued relational acquisition, executor constraints and
answer capacity together; they do not demonstrate superiority over executable
processing methods.

[Blockaid](https://www.usenix.org/conference/osdi22/presentation/zhang) formalizes
trace-conditioned database determinacy.
[Distilled test suites](https://aclanthology.org/2020.emnlp-main.29/) distinguish
SQL programs that agree accidentally on one database. Our replays apply related
reasoning to complete interactive observations, requiring admitted interventions
to leave the agent-visible history unchanged.
[GroundEval](https://arxiv.org/abs/2606.22737v2) uses state-dependent evidence
contracts; [HERALD](https://arxiv.org/abs/2608.06012v1) studies counterfactual
retrieval audits; [EG-VAR](https://arxiv.org/abs/2607.12650v1) derives proof-backed
claims through a trusted data-to-logic boundary. The present empirical controls
and local witnesses do not introduce formal grounding or counterfactual auditing.

[ELT-Bench-Verified](https://arxiv.org/abs/2603.29399v2) investigates benchmark
defects with automated diagnosis and human validation, while
[AgentJudgeBench](https://arxiv.org/abs/2608.26623v1) evaluates judges of tool
calling. Frozen interpretation cards and disclosed masks are safeguards here,
not independent adjudication or evidence that our labels outperform an official
evaluator. Full bibliographic records accompany the manuscript.

## 8. Discussion and limitations

These controls establish different boundaries. Relaxing call execution mainly
recovers interaction; increasing generation capacity recovers four exact
continuations but leaves early-stopped previews unchanged. Full output
retrieval can still miss a predicate error. Evaluation should report these
levels separately, with resources and counterfactual assumptions explicit.
No single dominant failure cause follows across all tool-using agents.

Tasks come from one benchmark's public training material and eight databases
selected partly for local feasibility. The new-domain comparison is prospective
relative to our experiments, but development informed model and intervention
choices. Four checkpoints do not represent a population of models. Each cell
has one greedy run; intervals describe task composition rather than repeated
generation. Oracle initialization, local templates and budgets constrain
comparisons with hosted agents and official scores.

Answer labels are assistant-authored and unblinded. Fixed cards reduce
outcome-dependent reinterpretation but cannot remove reviewer bias. Some
credited answers have faulty explanations. After the earlier student-domain
review, an additional ambiguity between employee ID and job level was noticed;
the frozen job-level interpretation was retained and disclosed. The Disney
sensitivity examines eight specific judgments, not all possible label errors.
The additional label-flip and ambiguity envelopes expose sensitivity under
explicit hypothetical assignments; they neither estimate annotation error
rates nor replace independent adjudication.
Hash agreement verifies provenance, not semantic truth.

Replay examples are post-hoc and conditional on synthetic status changes.
They establish existence, not incidence, and do not exclude helpful priors
or further distinguishing interactions. Pagination and predicate repairs are
evaluator-selected controls, not an end-to-end agent method. Hardware and
download overlap prevent a common speed ranking. More recorded executions
alone do not establish a new controller or benchmark-wide prevalence.

## 9. Conclusion

Interaction completion, answer agreement and identification by observed
evidence behave differently in these relational-tool studies. The fixed
reminder has mixed cross-domain effects. A permissive executor mainly
increases final-response production; larger generation budgets resolve four
demonstrably truncated lists but leave eight incomplete responses unchanged.
Two native-tool witnesses show how correct answers can remain unidentified
within explicit alternative worlds, including after full output retrieval.
Retained inadmissible and unsuccessful searches keep these claims local.
Evaluation of tool use needs joint attention to scope, acquisition, answer
capacity and the evidential meaning of the trace.

## Data, code and use of language models

Sources are maintained on the `codex/agent-paper-research` branch of
[Jing-XING/autoresearch](https://github.com/Jing-XING/autoresearch/tree/codex/agent-paper-research).
`reproduce.md` documents the complete expansion and budget analyses;
`claim_to_evidence.md` links earlier claims to their artifacts. Raw archives
are retained locally with hashes and are not yet a complete public download.
`study_record.md` preserves the preceding manuscript verbatim, including
protocol history and detailed controls. `references.bib` supplies the cited
bibliographic records.

A language-model assistant performed literature retrieval, implementation,
experiment operation, answer review, analysis and drafting. Numerical results
come from logged executions and retained artifacts. Answer annotation has no
independent human review. Author identities, affiliations, funding,
accountability declarations and submission approval have not been invented
or assigned by the assistant.

## Appendix A. Exact reminder

Before answering, verify that the observed results cover the requested scope. A first_3_values preview is a sample, not a complete column. Compare it with num_records. For a complete list, obtain the relevant full column from a correctly filtered handle. For a count or aggregate, use the appropriate tool on the correctly filtered data. Filter or aggregate large tables before fetching full columns. Check every requested condition, including any status qualifier. If the evidence remains incomplete, explicitly state that limitation instead of claiming completeness.
