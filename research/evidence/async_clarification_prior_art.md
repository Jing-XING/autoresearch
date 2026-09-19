# Async clarification candidate: direct overlap found

Status: primary-source method reading, not reproduction. Checked 19 September
2026 while the third-model experiment runs. The broad candidate “continue
useful safe work while awaiting clarification” is not an established gap.

[Building Interactive Real-Time Agents with Asynchronous I/O and Speculative Tool Calling](https://arxiv.org/html/2605.13360v1),
sections 3–4, already decouples user/environment updates from execution.
Its task DAG allows pending-call modification/removal, cancels dependent
calls, discards unused observations, and withholds side-effecting tools until
a commit point. It also trains smaller models on a clock-based simulator.
This directly overlaps a generic async loop, safe/unsafe classification,
dependency tracking, or delayed-confirmation gate. Its streaming-user
setting differs from an already-asked clarification, but that change alone
would not support a new method claim. No code or reported result was
reproduced in this project.

[Speculative Actions](https://arxiv.org/html/2510.04371v2), sections 2, 3.2
and 5, generalizes pre-execution to slow APIs and human responses, including
shopping dialogue. An authoritative actor validates speculative branches;
unselected branches require harmless/reversible execution. Its updated
version includes breadth/cost analysis and confidence-based selective branch
launching. Thus “predict a response, pre-execute, validate, roll back,”
adaptive branch counts and generic uncertainty-aware speculation are also
occupied. The [official repository](https://github.com/naimengye/speculative-action)
was pinned at `dc938b9ef7474caf07fe4ad16549c1fa8c7d268c`;
17 selected files were hash-verified and the HotPotQA/state and retail
execution paths were read. A method-level offline state probe is recorded in
[the code findings](speculative_action_code_findings_v1.md). It is not a
benchmark or model reproduction.
The older anonymous OpenReview PDF was blocked by browser verification;
the authors' arXiv v2 was used instead.

[Value of Information](https://aclanthology.org/2026.acl-long.1987.pdf)
formulates a clarify-or-commit decision with latent user preferences and
communication cost. That formulation is adjacent but does not by itself
cover scheduling several pending operations. It cannot establish novelty
once the above closer asynchronous methods are considered.

[PASTE](https://arxiv.org/html/2603.18897v1), sections 3–6, was read at
method level. Its patterns combine event signatures, predicted tools,
symbolic argument mappings and empirical confidence. Separate authoritative
and speculative queues share results; matching jobs are promoted. Speculation
uses slack capacity, a resource budget and preemption, with a utility based
on consumption probability, expected latency benefit, resource cost and
duration. Section 5.2 already supplies explicit operator eligibility,
deduplication, partial preparation and dry-run/staging transformations.
Section 6 describes cache keys using tool names and argument hashes. Thus
generic resource-aware scheduling, tool allowlists, and bounded speculative
work are not gaps. The paper says code will be released after review; no
implementation or reported performance has been independently reproduced
here. A missing state-version field in this description alone would not
prove that its implementation reuses invalid state.

Decision: do not launch an expensive generic async-clarification experiment
or count a paper slot as secured. A defensible residual question needs a
specific failure beyond these mechanisms, an executable task distribution,
and a strong dependency/scheduling baseline. Resource contention, stale
read results or unsupported reply alternatives are possible questions, not
asserted novelty. This note prevents implementing an already-described
workflow under a new name.

Additional method check: [A2H](https://arxiv.org/html/2602.15831v1),
sections 3.2.1–3.2.2, distinguishes hard-block permission, soft-block
clarification/solicitation, and non-blocking notification. Its asynchronous
callback pattern saves state, suspends, and resumes upon reply. This is not
itself a scheduler for useful actions during a pending reply. However, that
distinction does not rescue the broad proposal from the closer Async I/O and
Speculative Actions overlap above. No A2H implementation was run.
