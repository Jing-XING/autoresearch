# Byte identity of research inputs and evidence

Experiment manifests refer to exact file bytes, not a normalized JSON value.
The repository's `.gitattributes` therefore disables Git line-ending conversion
for JSON, JSONL and Python files. Keep these attributes when checking out on
Windows or Linux. Do not reformat frozen cards, registrations or result files
before validating their recorded hashes.

The NK target protocol Markdown file is explicitly covered as well because
its registration pins the protocol's exact bytes. Other prose documents are
not implicitly assumed to have byte-stable line endings.

A 2026-09-19 audit found 86 differences between local tracked-file bytes and
commit `3f4554b`, all attributable solely to CRLF/LF conversion. This could make
a Linux checkout fail a hash check even though the JSON data were identical.
The repair saves the existing local bytes without changing any experimental
input, selection, label, model output or running deployment. After re-staging,
all 218 checked JSON/Python files matched their index blobs. Four representative
files were also actually exported with both `core.autocrlf=true` and `false`;
all eight comparisons matched the original local bytes.

`evidence/git_exact_byte_reproducibility_v1.json` records the before/after audit,
all 86 differing paths and hashes, and the actual checkout checks. This is a
storage-format repair, not a repeat of the scientific experiments. Earlier
commits retain their original Git normalization and are not silently rewritten.
Previously created deployment/run archives retain their own exact bytes and
hashes; they are not reconstructed from a differently normalized source tree.

To audit a later checkout from the repository root:

```text
python scripts/audit_git_byte_identity.py --tree HEAD --output results/git-byte-check.json
```

The command compares every tracked JSON/JSONL/Python file with the requested
Git tree and reports any mismatch. Intentional uncommitted edits will appear
as mismatches too. This check does not fetch ignored raw result archives,
reproduce model inference, validate semantic answer labels or establish that
a manuscript is ready for submission.

## Zero-episode queue restart

The first fresh-domain batch (`vakra-expansion-v1`) failed while recording
single-GPU model placement: Transformers returned a `torch.device` in
`hf_device_map`, which the JSON writer did not support. Its two Qwen3 workers
failed before MCP/task initialization; the supervisor stopped the two Qwen2.5
workers during model loading. There were zero case files. Four downstream
supervisors also stopped on the dependency failure without starting workers.

The original outputs and logs remain intact, with a verified 29-file raw
failure archive. Only the recorded device-map values are converted to strings
in VAKRA placement metadata and the corresponding output-budget replay metadata.
Inference loading, seeds, prompts, selected tasks, budgets and masks are unchanged.
The restart package copies the original registrations byte for byte. New,
separately hashed supervisor entrypoints change only revision, output and
dependency path identifiers; the original registered scripts remain present.

`evidence/research_queue_restart_amendment_v2.json` pins all old/new archive
hashes and modified files. `evidence/research_queue_startup_failure_v1.json`
records the failed attempt, and `evidence/research_queue_restart_deployment_v2.json`
records the actual remote preflights and observed restart. The new expansion
is `vakra-expansion-v2`; its output-budget, memory, NK-curation and NK-target
successors have new run identifiers too. The memory code revision is
`tau-memory-test40-ties-code-v3`. Their scientific registrations retain the
original identifiers and are linked through the explicit amendment.

The restart was verified beyond process launch: all four actual single-GPU
placement files were valid JSON with device `cuda:0`, and the expansion had
produced twelve episode files at the recorded observation. Those task answers
were not inspected. These checks establish startup recovery, not batch success
or new scientific results.
