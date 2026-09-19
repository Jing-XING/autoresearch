# Fresh no-memory controls reproduce the prior development trajectories

The complete no-memory arm of `tau-memory-small20-v2` was returned and checked
before analyzing the memory interventions. Both models cover all 20 registered
small-split tasks with no missing episodes, run errors or protocol exceptions.
Official successes are 13/20 for Qwen3-4B-Instruct-2507 and 7/20 for
Qwen2.5-7B-Instruct, as in `tau-native-small20-prefix-v1`.

Comparison goes beyond aggregate scores. Matching episodes by model and task,
all 40 trajectories have identical model inputs, tool schemas, reply strings,
raw decoded completions, output token IDs, supplied prefixes and input/output
token counts at every model call. Per-model weights and runtime package
versions are identical. Wall-clock timings and simulation identifiers are
excluded from this deterministic comparison. Adapter source hashes changed
because memory support was added; this is disclosed rather than treating
different versions as byte-identical software.

The machine-readable comparison is
`tau_memory_v2_control_reproducibility.json`; the fresh-arm completeness and
prompt-hash audit is `tau_memory_v2_none_summary.json`. Repeating the same
tasks adds a reproducibility check, not 40 independent observations or evidence
for any memory benefit. The five-arm grid is still incomplete at this check.

Raw archive: 8,083,324 bytes, 136 files, SHA256
`d776635604a6d948f7d87c935588e8bcb49578050482f0d1b0128d5229666a5b`.
It is retained locally at `results/remote/tau-memory-small20-v2-none.zip`.
