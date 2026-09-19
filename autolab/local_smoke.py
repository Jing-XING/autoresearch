"""Execute a real local-model smoke test; results are NOT paper evidence."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time

from autolab.tool_agent import Budget, InventorySmokeEnvironment, ModelReply, run_episode, write_episode


class LocalTransformersModel:
    def __init__(self, model_path: Path):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if not torch.cuda.is_available():
            raise RuntimeError("GPU smoke requires a CUDA-enabled PyTorch installation")
        torch.manual_seed(20260919)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, local_files_only=True, trust_remote_code=False
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, local_files_only=True, trust_remote_code=False,
            use_safetensors=True, torch_dtype=torch.bfloat16, device_map="cuda:0"
        ).eval()

    def generate(self, messages, max_new_tokens):
        tensors = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_tensors="pt", return_dict=True
        ).to(self.model.device)
        n_input = tensors["input_ids"].shape[-1]
        self.torch.cuda.synchronize()
        started = time.monotonic()
        with self.torch.inference_mode():
            result = self.model.generate(
                **tensors, max_new_tokens=max_new_tokens, do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
        self.torch.cuda.synchronize()
        output = result[0, n_input:]
        return ModelReply(
            text=self.tokenizer.decode(output, skip_special_tokens=True),
            input_tokens=n_input, output_tokens=len(output),
            elapsed_seconds=time.monotonic() - started
        )


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-path", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--run-prefix", default="qwen3-4b-smoke-v1")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for suffix in ("limited", "sufficient", "manifest"):
        if (args.output / f"{args.run_prefix}-{suffix}.json").exists():
            raise FileExistsError("Choose a new run-prefix; smoke artifacts are immutable")
    metadata = {
        "purpose": "infrastructure_smoke_only",
        "model_path": str(args.model_path.resolve()),
        "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in
                     ("torch", "transformers", "accelerate", "safetensors")},
        "seed": 20260919, "do_sample": False,
        "source_sha256": {name: sha256_file(Path(__file__).parent / name)
                          for name in ("local_smoke.py", "tool_agent.py")},
    }
    # Snapshot fingerprints pin the actual downloaded weights, not a mutable branch name.
    metadata["model_files"] = [
        {"file": f.name, "bytes": f.stat().st_size, "sha256": sha256_file(f)}
        for f in sorted(args.model_path.iterdir())
        if f.is_file() and not f.name.startswith(".")
    ]
    write_episode(metadata, args.output, f"{args.run_prefix}-manifest")
    model = LocalTransformersModel(args.model_path)
    metadata["gpu"] = model.torch.cuda.get_device_name(0)
    task = "Transfer exactly 2 units from warehouse_a to warehouse_b. Commit the transfer and then finish."
    summaries = []
    for label, tool_limit in [("limited", 1), ("sufficient", 5)]:
        result = run_episode(
            model, InventorySmokeEnvironment(), task,
            Budget(model_calls=8, tool_calls=tool_limit, max_new_tokens=128), metadata
        )
        path = write_episode(result, args.output, f"{args.run_prefix}-{label}")
        summaries.append({
            "case": label, "termination": result["termination"],
            "success": result["evaluation"]["success"], "usage": result["usage"],
            "path": str(path)
        })
        print(json.dumps(summaries[-1]), flush=True)
    print("SMOKE_COMPLETE", json.dumps(summaries), flush=True)


if __name__ == "__main__":
    main()
