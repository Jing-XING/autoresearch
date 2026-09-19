# Fixed-protocol replication with an independent model family

The registered `vakra-smollm3-v1` grid uses SmolLM3-3B at official Hugging Face
revision `a07cc9a04f16550a088caea529712d1d335b0ac1`. Its Apache-2.0, ungated
metadata and every downloaded file digest are pinned in the download manifest.
Mirror files must match the official Git-object/LFS-derived fingerprints.
Only safetensors weights and standard Transformers model code are used.

Run the same first twenty questions in computer_student, cars and
book_publishing_company. For each domain, cross the already fixed
original/coverage_check prompts with single/sequential executor policies.
These four arms on one checkpoint give 240 episodes over sixty known task
identities. This is an architecture replication on inspected tasks, not an
independent task holdout or confirmation of a new method.

Keep twenty model-call attempts, twenty total executed tool attempts, 512
output tokens per generation, a 32768-token input ceiling, greedy decoding,
the fixed seed and the existing five-protocol-error policy. The sequential
executor follows the registered permissive-execution protocol. Every failure
is retained. Original database/query/runtime preparation and all frozen SQL
interpretations remain unchanged. No answer cards enter the agent runtime.

Use the official native SmolLM3 template with `xml_tools` containing the flat
function schemas and `enable_thinking=False`, as documented by the model
authors. Fix its rendered calendar date to 19 September 2026 through the
template's `strftime_now` variable; retain the original template file.
The template inserts its own metadata and empty reasoning prefix. Those
model-specific conventions are part of the method and must be disclosed,
not described as byte-identical prompts across model families. Both Qwen
checkpoints used in the comparison are also non-thinking instruction models.

Before GPU inference, verify template/schema rendering and all relevant
adapter tests on the server. Once prior GPU jobs and model downloads finish,
run one two-turn toy-tool infrastructure smoke test, using a fresh unrelated
read_value function and fixed numeric response. Its generated text is logged.
The grid is not selected or altered based on toy answer quality; only a
model-loading/generation infrastructure exception prevents launch.

The four workers run one shard each in the same query order. Shared initial
inputs and tokenizer serialization, protocol statistics, actual tool budgets,
answer scores under the named SQL audit, costs and all task-level changes
must be checked after completion. The third model's size is not matched to
both Qwen models; the experiment does not isolate architecture causally.
The native templates contain generic one-or-more-functions wording as well
as the official task prompt's per-iteration single-call instruction. Their
coexistence alone does not prove an instruction contradiction or a causal
explanation for model errors.
