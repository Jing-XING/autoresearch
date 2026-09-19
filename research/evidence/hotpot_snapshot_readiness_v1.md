# Reproducible inputs for a state-isolation experiment

This is executed dataset preparation and a CPU environment preflight. It is
not a fourth completed paper, a model-performance result, an asynchronous
speedup measurement or a new isolation algorithm.

## Fixed public material

The [HotpotQA project](https://hotpotqa.github.io/) distributes its question
answering data and supporting facts under CC BY-SA 4.0. Its distractor setting
supplies ten candidate paragraphs per question. The original CMU download
timed out during TLS negotiation after an initial local network permission
failure. We instead acquired the
[HotpotQA Hugging Face representation](https://huggingface.co/datasets/hotpotqa/hotpot_qa)
at commit `1908d6afbbead072334abe2965f91bd2709910ab`. Python's download client
encountered a TLS EOF on the redirected blob; the Windows system HTTPS client
downloaded the same pinned file successfully with certificate checking enabled.
No credentials were used or protections disabled.

The 27,452,575-byte Parquet file matches the repository's LFS SHA-256,
`c20b638ca82b21d04fe12e14ff417ad05153d4d215a65de54497fca4e972f7c6`.
PyArrow 21.0.0 in the isolated research-eval environment converts its structs to
the original-style field layout without filtering or reordering examples.
The resulting 45,931,342-byte JSON has 7,405 unique IDs and SHA-256
`2c56eb73e5f4cfaecf52342286510c40ebdbd7c8eea5971ceb2b3438929838f7`.
Byte identity with the unavailable original CMU JSON is not asserted.

The official answer scorer is pinned at project commit
`3635853403a8735609ee997664e1528f4480762a`, file SHA-256
`d35fc91a6db21d791dbdda11daf3856e9359f5701d54e3eefba20d88fecc02c0`.
The preflight executes its unchanged normalization, answer EM and F1 function
bodies with standard-library dependencies. It does not run supporting-fact or
joint benchmark evaluation. Four checks cover normalization, partial overlap
and special yes/no behavior.

## Selection and input boundary

All 94 distinct questions from the previously inspected Speculative Actions
archive match questions in this snapshot and are excluded. A fixed SHA-256
ordering of the remaining 7,311 IDs selects eight pilot tasks followed by forty
evaluation tasks, with no outcome-based replacement. Selection uses IDs and
question hashes, not answers. Public input files contain only ID, question and
candidate context; separate evaluator files hold answers and supporting facts.
This split is local experimental protection, not a claim of absent pretraining
exposure. No neural outcome exists for either group.

## Executed environment preflight

`autolab/hotpot_snapshot.py` executes seven unchanged method bodies from the
pinned Speculative Actions `WikiEnv`: reset, step, guess handling, page-summary
and lookup helpers. It explicitly substitutes constructors, provider clients,
network retrieval and Gym/data wrappers. Search matches a normalized candidate
title, or returns a deterministic suggestion list. It exposes no reference
answer and provides no estimate of live Wikipedia latency. The existing source
manifest and per-method AST hashes identify the exact code used.

For every one of eighty candidate passages in the eight pilot tasks, the
preflight searches that passage, optionally inserts a deterministic invented
prediction through the native simulation method, then performs a lookup.
Shared state makes the injected marker visible to the later lookup. Snapshot
isolation restores the authoritative state and next observation exactly to
the no-simulation control in all eighty cases. The explicit speculative-output
slot is retained separately. These are deliberately constructed interface
checks, not eighty independent Agent failures or a measured incidence rate.
Reference-field rejection and caller-input copy isolation also pass. The forty
evaluation environments were not executed by this preflight.

## What this enables and does not establish

The adapter provides fixed task identity, stable public retrieval content,
separate gold labels and replayable authoritative state. These address concrete
confounds identified in the original live/replayed analysis paths. A future
model study can compare baseline, shared and isolated simulation on the same
questions while retaining every failure. It still needs a frozen model/protocol
definition and real generation; no GPU job has been added for this direction.
The current adapter is a controlled distractor-context setting, so it cannot
directly reproduce published full-Wikipedia quality or latency numbers.

Restoration entry points: `fetch_hotpot_control_data.py --hf-mirror`,
`prepare_hotpot_snapshot_control.py`, and `preflight_hotpot_snapshot.py`.
PyArrow 21.0.0 is needed only for Parquet conversion. On this machine, the
documented HTTPS-client fallback was necessary for the source blob; downloaded
bytes were independently checked before conversion. Source datasets remain
under `results/third_party/`, and prepared public/evaluator files under
`results/preparations/hotpot-snapshot-control-v1/`. JSON evidence records all
selection, data, adapter, scorer and preflight hashes.
