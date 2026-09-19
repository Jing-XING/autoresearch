# Development control frozen before collection

2026-09-19. This is a simple prompt baseline and a falsification gate, not a
proposed novel method. The first four world tasks informed the prompt; none
of the twelve tasks in this batch is a held-out confirmation set.

Compare original official system prompt with that same prompt plus a generic
coverage reminder. The exact suffix is recorded by the runner and hashes.
The reminder distinguishes three-value previews from full results, requests
appropriate filtering/aggregation, and asks for explicit limitations when
evidence is incomplete. It adds no task answer, reference plan, database
schema beyond the existing interface, or hidden evaluation feedback.

Fixed allocation: first 12 world-train input queries in official input order,
2 checkpoints (Qwen3-4B-Instruct-2507, Qwen2.5-7B-Instruct), 2 prompt conditions,
48 episodes. No outcome-based task replacement or rerun. Both conditions use
20 model calls, 512 generated tokens per call, greedy decoding and a 32,768
input-token ceiling. Exceeding that ceiling ends the episode and is counted
separately from CUDA/model errors. Nothing is silently truncated. The first
8-episode batch did not impose this ceiling, so its outcomes are not substituted
for the new matched original-prompt control.

Report every termination, tool error, generation usage and final response.
Semantic answer audit must distinguish incomplete sets, incorrect predicates,
wrong aggregation scopes and reference representation discrepancies. A final
response is not sufficient for success. No official VAKRA score is claimed
without its documented evaluator. Do not select a new prompt on the best
observed cells or use pilot significance testing as confirmation.

The purpose is to learn whether a simple reminder resolves observed failures,
and what failures survive it. Even a positive result would not establish
novelty: output verification and explicit failure-status prompts already
exist in the related literature. A later method requires independent tasks,
stronger baselines and a clearly different mechanism.
