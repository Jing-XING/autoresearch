"""Deterministic context adapter around exact pinned WikiEnv method bodies.

Network retrieval, constructors, provider clients and Gym wrappers are replaced.
This is an explicitly adapted distractor-context control, not an upstream run.
"""
import ast
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import string
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/third_party/speculative-action/source"
METHODS = {"_get_obs", "_get_info", "reset", "construct_lookup_list", "get_page_obs", "guess_step", "step"}
STATE = ("page", "obs", "lookup_keyword", "lookup_list", "lookup_cnt", "steps", "answer",
         "result_titles", "search_time", "num_searches")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_native():
    manifest = json.loads((ROOT / "research/evidence/speculative_action_source_manifest_v1.json").read_bytes())
    paths = ["hotpotqa/src/environment.py", "hotpotqa/src/prompts.py"]
    for rel in paths:
        assert sha(SOURCE / rel) == manifest["files"][rel]["sha256"]
    prompt_tree = ast.parse((SOURCE / paths[1]).read_text(encoding="utf-8"))
    prompt = next(n for n in prompt_tree.body if isinstance(n, ast.ClassDef) and n.name == "PromptTemplates")
    scope = {}
    exec(compile(ast.Module(body=[prompt], type_ignores=[]), paths[1], "exec"), scope)
    tree = ast.parse((SOURCE / paths[0]).read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "WikiEnv")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in METHODS]
    assert {n.name for n in methods} == METHODS
    exec(compile(ast.Module(body=methods, type_ignores=[]), paths[0], "exec"), scope)
    native = type("PinnedWikiMethods", (), {n.name: scope[n.name] for n in methods})
    hashes = {n.name: hashlib.sha256(ast.dump(n, include_attributes=False).encode()).hexdigest() for n in methods}
    return native, hashes


class SnapshotWiki:
    def __init__(self, public_input, predictor):
        if set(public_input) != {"id", "question", "context"}:
            raise ValueError("Only public ID, question and context may enter the environment")
        native, self.method_hashes = load_native()
        self.native = native()
        self.public = copy.deepcopy(public_input)
        self.pages = dict(self.public["context"])
        if len(self.pages) != len(self.public["context"]):
            raise ValueError("Duplicate titles require explicit handling")
        self.title_map = {self.normalize(t): t for t in self.pages}
        if len(self.title_map) != len(self.pages):
            raise ValueError("Ambiguous normalized title")
        self.native.guess_llm = SimpleNamespace(call=predictor)
        self.native.sim_obs = None
        self.native.search_time = 0
        self.native.num_searches = 0
        self.native.result_titles = []
        self.native.reset()
        self.native.search_step = self.search

    @staticmethod
    def normalize(title):
        return " ".join(title.casefold().split())

    def search(self, entity):
        """Exact normalized titles or a deterministic suggestion list; no gold access."""
        key = self.normalize(entity)
        env = self.native
        env.num_searches += 1
        if key in self.title_map:
            title = self.title_map[key]
            env.page = "\n".join(self.pages[title])
            env.obs = env.get_page_obs(env.page)
            env.lookup_keyword = env.lookup_list = env.lookup_cnt = None
        else:
            tokens = set(re.findall(r"\w+", key))
            rank = sorted(self.pages, key=lambda t: (-len(tokens & set(re.findall(r"\w+", self.normalize(t)))), t))
            env.result_titles = rank[:5]
            env.obs = f"Could not find {entity}. Similar: {env.result_titles}."
        # Runtime is deliberately not an estimate of a live network API's latency.

    def state(self):
        return {key: copy.deepcopy(getattr(self.native, key)) for key in STATE}

    def step(self, action):
        return self.native.step(action)

    def simulate(self, action, *, isolate):
        before = self.state() if isolate else None
        try:
            result = self.native.step(action, step_type="simulate")
            return {"result": result, "sim_obs": self.native.sim_obs}
        finally:
            if before is not None:
                for key, value in before.items():
                    setattr(self.native, key, value)


def load_answer_scorer():
    manifest = json.loads((ROOT / "research/evidence/hotpot_control_data_manifest_v1.json").read_bytes())
    path = ROOT / "results/third_party/hotpotqa-control/hotpot_evaluate_v1.py"
    assert sha(path) == manifest["scorer_sha256"]
    names = {"normalize_answer", "f1_score", "exact_match_score"}
    selected = [n for n in ast.parse(path.read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in selected} == names
    scope = {"re": re, "string": string, "Counter": Counter}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), scope)
    return scope
