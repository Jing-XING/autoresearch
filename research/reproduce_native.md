# Reproducing the native agent development experiments

This code is research infrastructure. The current public experiments are
development runs; no proposed method has passed a held-out evaluation and no
completed-paper claim is made. See
[the complete small-set audit](evidence/tau_native_small20_development.md).

## Separate environment

Use Python 3.12 or 3.13 and an isolated environment. These experiments do not
use the original repository's pretraining dependency lock. The recorded GPU
environment used torch 2.8.0+cu128, transformers 4.57.1, accelerate 1.10.1, and
litellm 1.82.6. GPU inference was performed on A40 devices. The model folders
must be complete local snapshots of Qwen/Qwen3-4B-Instruct-2507 and
Qwen/Qwen2.5-7B-Instruct; every run records the actual model-file SHA256 hashes.
No API-based agent or user simulator is used in these solo runs.

Obtain [Sierra's official tau2 source](https://github.com/sierra-research/tau2-bench)
at commit `b7ea9074c1cba482b30687fecdb5c8425fd6f619`, including its data files,
and install that directory editable. **Do not install the unrelated `tau2`
package by name from PyPI.** Keep the source/data unchanged: the runner checks
the complete 1,169-file canonical manifest before using it. The exact version
also imports websockets even for text execution; the tested environment used
websockets 17.1. Python 3.13 additionally required audioop-lts 0.2.2.

Set `PYTHON_DOTENV_DISABLED=1` and `LITELLM_LOCAL_MODEL_COST_MAP=True` so the
experiment does not load unrelated credentials or fetch a model cost map.
On Windows, pass `-X utf8` to Python. A CPU installation of the pinned official
source is sufficient for the integration tests; they use scripted outputs and
prohibit external completion calls.

## Run and preserve artifacts

From this repository, with paths adapted to the isolated environment:

```sh
CUDA_VISIBLE_DEVICES=0 python -m autolab.tau2_native_baseline \
  --model-path /models/Qwen3-4B-Instruct-2507 \
  --tau-repo /source/tau2-bench \
  --output /runs/example/qwen3/shard-0 \
  --split small --count 20 --shard 0 --shards 1 \
  --max-steps 60 --tool-prefix
```

For the recorded four-GPU layout, run two stride shards per model with
`--shards 2` and shard indices 0/1. Every output directory must be new. Preserve
all failures, status files, model audits, simulations, manifests, and logs.
The `--tool-prefix` option supplies an opening marker. Both the supplied
prefix and the actual generated text/token IDs are logged separately. This
must be reported as a distinct formatting condition; it is not grammar
constrained decoding.

The source adapter exposes only policy, ticket, tool schemas, and observed
history to the model. It retains official task transitions and rewards. A
small compatibility subclass accepts unused constructor arguments passed to
the official DummyUser; the actual dummy-user behavior is inherited.

`autolab.summarize_tau2_native.summarize(Path(batch_root))` audits coverage,
configuration compatibility, input hashes, and official/status reward
agreement. Its default expected model names are `qwen3` and `qwen25`.

## Offline diagnostics, not extra agent feedback

```sh
python -m autolab.tau2_prefix_audit \
  --root /runs/example --tau-repo /source/tau2-bench \
  --output /analysis/state-audit.json
python -m autolab.trajectory_cutoffs \
  --root /runs/example --output /analysis/cutoffs --cutoffs 4 8 16
```

Prefix state replay uses hidden official assertions and action criteria only
after inference. Its labels are not available to agents or curators and do
not replace official rewards. Cutoff data store visible inputs separately
from future-outcome labels. Generation cutoffs are different from the
orchestrator's message-step budget. Do not treat several prefixes, or repeated
model evaluations of one task, as independent tasks.

## Validation

```sh
python -m unittest discover -s tests -v
python -X utf8 -m unittest discover -s tests -p test_tau2_native_integration.py -v
```

The second command must run inside the official tau2 environment; otherwise
the optional integration suite skips. Its positive examples are deliberately
scripted test controls, not model performance results. Tests cover reward
preservation, absence of hidden-evaluator leakage into inputs, malformed tool
output retention, strict prefix grouping, state reversals, and zero reward
under budget expiry even when a repair was performed.
