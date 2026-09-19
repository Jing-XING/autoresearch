# Larger-model capacity control — fixed before its benchmark outputs

Registered locally on 2026-09-19. This is a follow-up capacity stress test on
the same public development tasks. It is not a new task holdout, a matched
parameter-scaling experiment, or validation of a novel method.

The checkpoint is [Qwen3-30B-A3B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507),
revision `0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe`. Its official
configuration uses `qwen3_moe`, 48 layers and bf16. The official tokenizer
template emits JSON inside `tool_call` blocks; it is compatible with the
existing native parser. All 23 required model/tokenizer artifacts are pinned
in `qwen30b_download_manifest.json`. The 1M-context configuration is unused.

Evaluate all 60 tasks in `vakra_crossdomain_setup_audit.json` under original
and fixed coverage-check prompts, using the sequential executor: 120 total
episodes, regardless of outcome. Preserve prepared initial observations,
tool schemas, frozen query interpretations and answer-review policy. Use
greedy decoding, seed 20260919, 20 model attempts, 20 executed tool attempts,
512 maximum new tokens per generation, 32768 input tokens and the existing
five-protocol-error termination rule. No forced tool prefix or model-specific
answer hint. Do not retune prompts using this checkpoint's answers.

Two replicas each use exactly two visible A40s, with Transformers' balanced
GPU-only device map and 36 GiB loading ceiling per GPU. Record actual device
placement; reject CPU/disk offload. Start only after the third-model batch
finishes and all GPUs are free. First run an unrelated two-turn toy tool
generation smoke check. Infrastructure failure is recorded, not a reason to
select different benchmark cases. No benchmark answer quality determines
whether the grid runs.

Compare final-answer availability, explicit executor/model failures,
SQL-compatible answer counts, task-wise paired gains/losses, token usage and
tool attempts. Keep the five preflagged interpretation ambiguities separate
from the frozen 55-task subtotal while retaining all 60 tasks in execution
accounting. Preserve the later-detected publishing ambiguity without changing
the subtotal retrospectively. Answer annotation is assistant-authored and
not official VAKRA scoring or independent human validation.

The motivation is to test whether observed failures persist at higher model
capacity. Different architecture, training and checkpoint release prevent
causal attribution to parameter count. Comparisons involving two GPUs cannot
be presented as matched-hardware latency comparisons with single-GPU runs.
The existing Qwen and SmolLM results, successful or unsuccessful, remain in
the record. Download/inference status and actual outputs will be recorded
separately; this protocol does not imply successful completion.
