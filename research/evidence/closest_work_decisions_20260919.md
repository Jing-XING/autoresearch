# Closest-work decisions after executed pilots

These are research-selection decisions, not publication claims. Sources were
opened at their primary paper pages; no search snippet is used as proof of
novelty or numerical superiority.

## Tool-output evidence

[Agents Don't Paginate](https://arxiv.org/html/2608.26130v1), Sections 2–4,
already studies first-chunk selection and absent pagination. Its model probe
asks for file localization rather than complete multi-turn task execution.
Our observed VAKRA omission concerns exhaustive set coverage in an interactive
relational workflow. That difference is a candidate experimental scope,
not proof of novelty. Reordering preview values alone is not a new contribution.

[Fabrication After Tool Failure](https://arxiv.org/html/2609.14758v1),
Sections 3–6, fixes an unusable tool payload and studies the ensuing report.
It includes an explicit retrieval-status instruction and verification prompt
controls. A status flag or generic request to verify tool evidence is already
covered. Our new coverage_check prompt is therefore a baseline, not a method
claim. Recoverable partial evidence and further tool selection could support
a different question only if the closed-loop decision mechanism adds value.

[How Good Are LLMs at Processing Tool Outputs?](https://aclanthology.org/2026.eacl-long.134.pdf),
Sections 2–4 and Appendix C, compares direct answers and executable code with
schema/full/reduced responses. Its reduced JSON retains examples to preserve
structure; this is explicitly paired with code generation. The authors also
discuss information lost by summarization and retrieval. Any proposed output
controller must compare against executable processing, not only a model
reading a long string. The [released repository](https://github.com/LongFuncEval/toolJSONprocessing)
is an additional candidate source, not yet downloaded or reproduced here.

Working question: when evidence is partial but further access is possible,
can a task-sensitive controller choose a small, sufficient observation and
avoid claiming exhaustive coverage? This remains unestablished. The running
48-episode simple-prompt control precedes any claim that a more complex
controller is necessary. Counts, membership witnesses and exhaustive lists
need different evidence; adding every missing row indiscriminately may worsen
cost and exceed context. Ordinary database query planning and typed contracts
are strong conceptual baselines, not new inventions.

## Skill maintenance: downgrade the current D02 formulation

[Skill Drift Is Contract Violation](https://arxiv.org/html/2605.10990v1),
Sections 4.1–4.3, already extracts environment assumptions from skill text,
checks violated contracts and localizes repairs using evidence spans. Its
literal replacement verifier has limited semantic scope, which the paper
explicitly acknowledges. The current D02 proposal of dependency-aware local
skill repair overlaps directly and is not ready for an independent paper.

[SkillOps](https://arxiv.org/html/2605.13716v1), Section 2, already represents
skills with preconditions, operations, typed artifacts, validators and failure
modes, plus dependency/compatibility relations and maintenance actions.
Adding a skill graph or validator does not establish a new contribution.

[DepRepair](https://arxiv.org/abs/2607.17957) additionally grounds dependency
repair in upstream change evidence and affected usage sites. Only its abstract
was inspected in this pass; its executable benchmark needs artifact review
before any repair comparison is designed.

Decision: do not spend GPU experiments on the unmodified D02 proposal. Retain
it only if a narrower failure class and a mechanism beyond these baselines can
be demonstrated. This does not reduce the five-paper delivery objective;
candidate directions must be replaced when evidence rejects their premise.

## Further candidate screening: verification, recovery and clarification

The following is primary-abstract screening, not full reproduction or a
claim that every possible narrower contribution is excluded.

[Partially Correlated Verifier Cascades](https://arxiv.org/abs/2607.13918)
already models latent false-accept rates, diminishing evidence from repeated
gates and blind-spot ceilings. It explicitly motivates changing evidence
sources or model families. P05 cannot claim verifier dependence or a warning
against independent-vote assumptions as its new contribution.

[Engineering Reliable Commit Gates](https://arxiv.org/abs/2609.10969)
already separates source diversity from model diversity, chooses cost-aware
verification portfolios, and tests concurrent writes and lost responses with
atomic guards and idempotent request identifiers. This overlaps both P03 and
P05. A new retry wrapper, lineage label, or diversified vote is insufficient.
The paper reports transfer limits, which should not be omitted when choosing
it as a baseline. Its reported results have not been independently reproduced
in this repository.

[Ask Early, Ask Late, Ask Right](https://arxiv.org/abs/2605.07937)
studies clarification injected at controlled execution positions and separates
missing goal, input, constraint and context information. P04 must therefore
distinguish useful work during an outstanding reply from merely asking at a
better time. The latter is already explicitly studied.

[A2H](https://arxiv.org/abs/2602.15831) formalizes agent-to-human discovery and
communication. Its abstract establishes protocol scope; asynchronous callback
and blocking semantics require reading the method before comparison. A new
message schema alone would not justify P04. Native GAIA2 user-message behavior
also does not yet establish the pending-reply environment needed here.

Decision: keep these three slots provisional. Do not manufacture independent
papers by splitting a common reliability wrapper into multiple manuscripts.
Their shared motivation is not evidence of distinct scientific contributions.
