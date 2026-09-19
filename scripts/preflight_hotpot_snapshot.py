"""CPU preflight on pilot contexts, not model or asynchronous performance results."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autolab.hotpot_snapshot import SnapshotWiki, load_answer_scorer


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    selection_path = ROOT / "research/evidence/hotpot_snapshot_selection_v1.json"
    selection = json.loads(selection_path.read_bytes())
    pilot_path = ROOT / "results/preparations/hotpot-snapshot-control-v1/pilot.inputs.json"
    assert sha(pilot_path) == selection["groups"]["pilot"]["inputs_sha256"]
    inputs = json.loads(pilot_path.read_bytes())
    results = []
    method_hashes = None
    for item in inputs:
        rows = []
        marker = "snapshotprediction" + item["id"]
        prediction = marker + " generated page fixture."
        assert all(marker not in sentence for _, sentences in item["context"] for sentence in sentences)
        for title, sentences in item["context"]:
            modes = {}
            for mode in ("baseline", "shared", "isolated"):
                env = SnapshotWiki(item, lambda prompt: prediction)
                method_hashes = env.method_hashes
                first = env.step("search[" + title + "]")
                before = env.state()
                if mode != "baseline":
                    env.simulate("search[" + title + "]", isolate=mode == "isolated")
                after = env.state()
                observation = env.step("lookup[" + marker + "]")[0]
                modes[mode] = {"first_observation_sha256": hashlib.sha256(first[0].encode()).hexdigest(),
                               "state_changed_by_simulation": before != after,
                               "next_lookup": observation, "final_state": env.state()}
            assert modes["baseline"] == modes["isolated"]
            assert marker not in modes["baseline"]["next_lookup"]
            assert marker in modes["shared"]["next_lookup"]
            assert modes["shared"]["state_changed_by_simulation"]
            # Retain hashes rather than duplicate the public article text in the report.
            rows.append({"title_sha256": hashlib.sha256(title.encode()).hexdigest(),
                         "sentences": len(sentences), "original_and_isolated_equal": True,
                         "shared_fixture_prediction_visible_in_next_lookup": True,
                         "original_observation_sha256": modes["baseline"]["first_observation_sha256"]})
        # Answer/reference fields must never cross the environment's input boundary.
        try:
            SnapshotWiki(dict(item, answer="forbidden-evaluator-field"), lambda prompt: prediction)
        except ValueError:
            gold_rejected = True
        else:
            raise AssertionError("Gold-field leak accepted")
        pristine = copy.deepcopy(item)
        env = SnapshotWiki(item, lambda prompt: prediction)
        env.public["context"][0][1].append("local mutation")
        assert item == pristine
        results.append({"id": item["id"], "contexts": rows, "gold_field_rejected": gold_rejected,
                        "public_input_copy_isolated": True})
    score = load_answer_scorer()
    scorer_checks = []
    cases = [("The Nile!", "nile", True, 1.0), ("yes", "no", False, 0.0),
             ("New York", "New York City", False, 0.8), ("yes indeed", "yes", False, 0.0)]
    for prediction, gold, em, f1 in cases:
        actual_em = score["exact_match_score"](prediction, gold)
        actual_f1 = score["f1_score"](prediction, gold)[0]
        assert actual_em == em and abs(actual_f1 - f1) < 1e-12
        scorer_checks.append({"prediction": prediction, "gold": gold, "em": actual_em, "f1": actual_f1})
    report = {"purpose": __doc__, "complete": True, "pilot_tasks": len(inputs),
              "contexts_checked": sum(len(r["contexts"]) for r in results), "model_calls": 0,
              "live_network_calls": 0, "evaluation_inputs_executed": False,
              "selection_sha256": sha(selection_path), "pilot_inputs_sha256": sha(pilot_path),
              "adapter_sha256": sha(ROOT / "autolab/hotpot_snapshot.py"), "script_sha256": sha(Path(__file__)),
              "native_method_ast_sha256": method_hashes, "rows": results, "official_answer_scorer_checks": scorer_checks,
              "scope": "Exact pinned WikiEnv method bodies; replaced constructors, provider client, network retrieval and Gym/data wrappers. Deterministic injected prediction is a preflight fixture, not a language-model outcome.",
              "limits": "No measured asynchronous speedup, task success rate or new isolation algorithm. Snapshot search uses distractor passages and known candidate titles, not live full Wikipedia."}
    dest = ROOT / "research/evidence/hotpot_snapshot_preflight_v1.json"
    with dest.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in ["pilot_tasks", "contexts_checked", "model_calls", "evaluation_inputs_executed"]}))


if __name__ == "__main__":
    main()
