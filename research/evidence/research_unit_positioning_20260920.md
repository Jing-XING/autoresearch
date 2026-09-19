# Decision: distinguish experiment units before proposing an agent controller

20 September 2026. This is a feasibility decision, not a novelty certificate.

The methods and stress-test sections of [AutoLLMResearch v2](https://arxiv.org/html/2605.11518v2)
go beyond generic cheap-to-expensive transfer: the paper explicitly discusses
configuration-space and optimization-landscape shifts, and tests sparse
coverage and reversed optimal regions. We inspected sections 1 and 6, not
the source implementation. A rank-reversal example alone would therefore
not distinguish our candidate.

[GraphEcho v1](https://arxiv.org/html/2609.17695v1), sections 3-5, directly
studies repeated origins versus repeated representations. It includes
active acquisition, instruction/provenance controls and a preprocessing
control that groups equivalent paths. Its synthetic verdicts use distinct
supporting/refuting origins. Document provenance in its SciFact construction
is explicitly not proof of statistical independence. These details rule out
claiming that provenance labels or deduplication alone are new here. We did
not execute its implementation or reproduce its reported results.

The narrower next question concerns what is grouped: two estimators can
share a resample without being duplicate evaluations; repeated reports of
one evaluation add no replicate. A third case has partial overlap. Treating
every shared identifier as redundant can erase a legitimate matched arm.
This distinction is standard experimental-design reasoning. The possible
research contribution would be a demonstrated consequence for autonomous
experiment selection and a tested correction beyond ordinary grouping.
Neither is established yet.

The fixed public preparation in `research/research_unit_pilot_v1.md` first
tests a smaller prerequisite: extracting these units under an explicit
schema. Its thirty planned model responses are static development audits,
not thirty autonomous research projects. The examples reuse three public
pools from the already measured risk diagnostic; no private evaluator is
exposed and no fifth-paper result is inferred from a deterministic grouping
test. Model-pilot code and deployment must be separately frozen before use.

Do not expand solely because repeated display changes a count. Expansion
requires a decision-level endpoint, independent task variation, strong
deterministic/statistical controls, and another closest-work comparison.
The four existing paper slots and their experiment queue remain unchanged.
