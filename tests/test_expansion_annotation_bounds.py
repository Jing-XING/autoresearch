import copy
import itertools
import unittest

from scripts.analyze_expansion_annotation_bounds_v1 import analyze_rows, change_envelope, label_groups


def row(task, model, condition, text, label):
    return {"domain": "fixture", "uuid": task, "task_index": int(task), "model": model,
        "condition": condition, "final_answer": text, "answer_label": label,
        "termination": "agent_finished" if text is not None else "max_steps",
        "source": f"{task}/{model}/{condition}", "source_sha256": "fixture"}


class AnnotationBoundsTest(unittest.TestCase):
    def test_flip_envelope_against_exhaustive_subsets(self):
        for delta in (-3, -1, 0, 1, 3):
            changes = [-1, -1, 1, 1, 1]
            effects = [{"group_id": str(i), "delta_change": v} for i, v in enumerate(changes)]
            observed = change_envelope(delta, effects, 5)
            candidates = [(sum(bits), delta + sum(c * b for c, b in zip(changes, bits)))
                          for bits in itertools.product((0, 1), repeat=5)]
            for point in observed["curve"]:
                values = [v for k, v in candidates if k <= point["maximum_changed_judgments"]]
                self.assertEqual([point["minimum_net_difference"], point["maximum_net_difference"]], [min(values), max(values)])
            ties = [k for k, v in candidates if v == 0]
            reversals = [k for k, v in candidates if delta * v < 0]
            self.assertEqual(None if observed["to_exact_tie"] is None else observed["to_exact_tie"]["changed_judgments"], min(ties) if ties else None)
            self.assertEqual(None if observed["to_strictly_reverse_observed_sign"] is None else observed["to_strictly_reverse_observed_sign"]["changed_judgments"], min(reversals) if reversals else None)

    def test_exact_response_equality_binds_models_and_prompts(self):
        rows = [row("0", "a", "original", "same", "correct"),
                row("0", "a", "coverage_check", "same", "correct"),
                row("0", "b", "original", "same", "correct"),
                row("0", "b", "coverage_check", None, "no_answer")]
        result = analyze_rows(rows)
        self.assertEqual(len(result["groups"]), 1)
        self.assertEqual(result["models"]["a"]["annotation_flip_sensitivity"]["curve"][-1]["maximum_net_difference"], 0)
        b = result["models"]["b"]["annotation_flip_sensitivity"]
        self.assertEqual(b["to_exact_tie"]["changed_judgments"], 1)
        self.assertIsNone(b["to_strictly_reverse_observed_sign"])
        changed = copy.deepcopy(rows)
        changed[2]["answer_label"] = "incorrect"
        with self.assertRaisesRegex(ValueError, "conflicting labels"):
            label_groups(changed)

    def test_ambiguous_envelope_against_all_consistent_binary_assignments(self):
        rows = []
        for index, pair in enumerate(((None, None), ("same", "same"), (None, "b"), ("a", None), ("x", "y"))):
            rows += [row(str(index), "a", condition, text, "ambiguous")
                     for condition, text in zip(("original", "coverage_check"), pair)]
        result = analyze_rows(rows)["models"]["a"]["all_task_label_relaxation"]
        keys = {(r["uuid"], r["final_answer"]) for r in rows if r["final_answer"] is not None}
        values = []
        for bits in itertools.product((0, 1), repeat=len(keys)):
            assignments = dict(zip(sorted(keys), bits))
            values.append(sum((1 if r["condition"] == "coverage_check" else -1) * assignments.get((r["uuid"], r["final_answer"]), 0) for r in rows))
        self.assertEqual(result["net_difference_bounds"], [min(values), max(values)])
        self.assertEqual(result["net_difference_bounds"], [-2, 2])
