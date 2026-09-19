# Trace sufficiency: closest-work boundaries

Checked 2026-09-19 against primary papers. These comparisons do not assert
novelty or reproduce the cited methods.

[Blockaid, OSDI 2022](https://www.usenix.org/system/files/osdi22-zhang.pdf)
already uses query traces and their returned values to define trace
conditional determinacy, with SMT counterexamples for noncompliant queries.
Its context is SQL access-policy enforcement. The underlying idea that
observationally equal databases can require different query answers is
established prior art, including the trace-conditioned formulation. A new
Agent audit must contribute operational treatment of actual handle/preview
interfaces and validated empirical findings; renaming the definition or
adding hashes is insufficient. We have read the paper's introduction and
formal-method context, but have not reproduced its implementation.

[GroundEval v2](https://arxiv.org/html/2606.22737v2), sections 3–6, scores
answer and trajectory properties against reviewed machine-readable contracts.
Its obligations include declared absence-search spaces, access/time limits
and causal links. The framework drafts contracts from observed executions
and requires review. A generic deterministic trace score or separation of
correctness from grounding therefore overlaps. A database replay witness
instead asks whether a changed target answer remains compatible with the
entire observed tool interface; this narrower distinction requires evaluation,
not merely a terminology change. The study's judge comparisons also differ
in what evidence is exposed, which must be kept explicit in any reproduction.

[HERALD v1](https://arxiv.org/html/2608.06012v1) already audits retrieval
reward mechanisms by controlled changes and studies minimal checker repairs.
It distinguishes the agent-visible and oracle information boundaries. Our
candidate interventions act on underlying relational data while retaining
observed tool returns, rather than automatically constituting a new generic
counterfactual-auditing principle. Its method is not reproduced here.

[ClaimReceipt v1](https://arxiv.org/html/2609.01992v1) concerns recomputable
experimental claims and coverage of committed runs. Complete-run accounting
and hashes in this repository support reproducibility but are not an
independent scientific contribution.

[EG-VAR v1](https://arxiv.org/html/2607.12650v1), Junyu Ren, 14 July 2026,
already combines tool attestation, source-specific trusted lifts and Lean 4
kernel checking. Its content-edited tabular counterfactuals alter visible
evidence; our diagnostic instead holds the observed trace fixed. This target
difference alone is not novelty. Trusted formalization remains a separate
failure boundary. Method and scope read; code and benchmark not reproduced.

## Additional validity boundary found during development

A schema-valid counterfactual is not necessarily consistent with the natural
language task's background knowledge. An automatic mutation can place a
Japanese city's District value in England while leaving its country code
unchanged. A model that restricts to GBR before counting England may remain
reasonable under geographical constraints even though an evaluator's
District-only SQL now differs. Likewise, moving Rwanda into Baltic Countries
violates ordinary geographical assumptions. Such witnesses establish only
SQL-and-schema-relative non-identifiability; they must not be counted as
natural-language reasoning failures without an explicit admissible-world
contract. Preserve these results as a diagnostic of the evaluator's scope,
not an opportunity to relabel agent scores.

The finite candidate grammar also misses the already verified Andorra
Spanish-official witness in the Qwen3 reminder trajectory. Search exhaustion
is therefore demonstrably not a sufficiency certificate. Both the semantic
false-positive risk and search incompleteness must accompany any later
performance table.
