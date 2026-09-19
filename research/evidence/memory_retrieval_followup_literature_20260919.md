# Primary-source constraints on the memory follow-up

Read on 2026-09-19. These are prior-work comparisons, not reproductions.

- [MERIT: Causal Episodic Memory for Feedback-Driven Agent Repair](https://arxiv.org/html/2608.05906v1), sections 3–4: memory eligibility is temporal, and repair uses oracle-assisted benchmark feedback. Negative records describe unsuccessful directions in their source context. It compares memory structures and stream orders. Our fixed prefix-curation contrast cannot claim to introduce cautious negative memory, controlled memory comparisons or source-local qualification.
- [Ask Only When Needed](https://arxiv.org/html/2604.20572v1), Appendix A: paired continuations from replayable prefixes provide a noisy local proxy for retrieval value under stated assumptions. Our comparison is across fixed source lessons at target initialization, not a new counterfactual retrieval-credit method.
- [Structurally Aligned Subtask-Level Memory](https://arxiv.org/html/2602.21611v1), sections 3.4–4.4: surface-related tasks can require different local experience; stage-aligned retrieval and structure-only controls are already studied. Altering tied source choice here is a diagnostic of the fixed lexical baseline, not a novel semantic retrieval algorithm.

The concrete unresolved question is whether the observed negative
boundary-instruction result persists on all forty unused telecom test tasks
and under fixed, outcome-independent alternative top-tie choices. This narrow
empirical question does not establish publishability by itself.

Additional primary-source checks:

- [How Memory Management Impacts LLM Agents](https://aclanthology.org/2026.acl-long.27/),
  official PDF sections 3.1–3.4 and 4.2–4.3: feedback-based addition/deletion
  and harmful reuse are already studied. The strict evaluator is simulated
  from ground truth in these experiments; do not describe it as collected
  human annotation. No reproduction performed here.
- [On the Structural Memory of LLM Agents](https://arxiv.org/html/2412.15266v1),
  section 3: chunks, triples, atomic facts, summaries and retrieval procedures
  are compared. A change from free text to structured memories is not itself
  a new contribution.
- [Agent Zero Memory](https://arxiv.org/html/2608.29606v1), section 3.1–3.4:
  temporal provenance and citation-constrained reading are explicit prior
  mechanisms. Definition 2 requires both opened citations and claim support;
  pointer membership alone does not establish the latter. We have inspected
  the formulation, not verified the system's claimed semantic guarantee or
  reproduced its benchmark results.
