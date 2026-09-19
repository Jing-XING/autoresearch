"""Offline replay and descriptive paired diagnostics for the frozen pilot.

Replay reuses the deployed control flow; it checks trace integrity, not independent
implementation correctness or neural reproducibility. No model is loaded.
"""
from collections import Counter, defaultdict
import json
import math

from .hotpot_pilot import CONDITIONS, SETTINGS, execute_episode
from .native_tool_agent import NativeModelReply


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class ReplayMismatch(BaseException):
    """Must escape the worker's intentional catch-and-record Exception block."""


class RecordedModel:
    def __init__(self, generations):
        self.generations = generations
        self.position = 0

    def generate_tools(self, messages, tools, max_new_tokens):
        if self.position >= len(self.generations):
            raise ReplayMismatch("Unrecorded model call")
        row = self.generations[self.position]
        self.position += 1
        role = "actor" if messages[0]["role"] == "system" else "prediction"
        if (tools != [] or row["role"] != role or row["messages"] != messages
                or row["max_new_tokens"] != max_new_tokens):
            raise ReplayMismatch("Recorded model input differs from replay")
        if "reply" in row:
            return NativeModelReply(**row["reply"])
        # Recreate only the saved exception's name/message; do not import or
        # execute arbitrary exception classes named by an artifact.
        error_class = type(row["error_type"], (Exception,), {})
        raise error_class(row["error"])


def validate_episode(row, item, condition):
    require(row["id"] == item["id"] and row["condition"] == condition, "Wrong episode identity")
    require(row["settings"] == SETTINGS and row["scored"] is False, "Wrong settings/scored flag")
    require(isinstance(row["elapsed_seconds"], (float, int))
            and math.isfinite(row["elapsed_seconds"]) and row["elapsed_seconds"] >= 0, "Invalid duration")
    for generation in row["generations"]:
        require(("reply" in generation) != ("error_type" in generation), "Reply/error conflict")
        if "reply" not in generation:
            require(isinstance(generation["error_type"], str) and isinstance(generation["error"], str), "Invalid error")
            continue
        reply = generation["reply"]
        ids = reply["output_token_ids"]
        require(isinstance(ids, list) and all(type(x) is int and x >= 0 for x in ids), "Invalid token IDs")
        require(type(reply["input_tokens"]) is int and reply["input_tokens"] > 0
                and reply["input_tokens"] <= SETTINGS["max_input_tokens"], "Invalid input usage")
        require(type(reply["output_tokens"]) is int and reply["output_tokens"] == len(ids)
                and len(ids) <= generation["max_new_tokens"], "Invalid output usage")
        require(math.isfinite(reply["elapsed_seconds"]) and reply["elapsed_seconds"] >= 0, "Invalid generation time")
        require(reply["supplied_prefix"] == "" and reply["text"] == reply["completion_text"], "Unexpected prefix")
    model = RecordedModel(row["generations"])
    try:
        replay = execute_episode(model, item, condition)
    except ReplayMismatch as exc:
        raise ValueError(str(exc)) from None
    require(model.position == len(row["generations"]), "Unused recorded generations")
    # Wall-clock replay duration is necessarily different. All other saved
    # fields, including generation durations and failed calls, must match.
    expected = {k: v for k, v in row.items() if k != "elapsed_seconds"}
    observed = {k: v for k, v in replay.items() if k != "elapsed_seconds"}
    require(canonical(expected) == canonical(observed), "Recorded episode differs from replay")
    mutations = Counter()
    simulation_calls = 0
    for event in row["trace"]:
        if "state_after_simulation" in event:
            simulation_calls += 1
            before, after = event["state_after_authoritative"], event["state_after_simulation"]
            mutations.update(k for k in before if before[k] != after[k])
    return {"simulation_calls_completed": simulation_calls, "changed_fields": dict(sorted(mutations.items())),
            "recorded_generation_calls": len(row["generations"])}


def authoritative_projection(row):
    keys = ("step", "state_before", "action", "authoritative_result", "state_after_authoritative",
            "protocol_error", "error_type", "error", "state_at_error")
    return {"messages": row["messages"], "trace": [{k: e[k] for k in keys if k in e} for e in row["trace"]],
            "termination": row["termination"], "final_answer": row["final_answer"], "final_state": row["final_state"]}


def observation_sequence(row):
    # Exclude bookkeeping steps in info: shared simulations increment these
    # even when the actual observations seen by the actor remain unchanged.
    return [e["authoritative_result"][0] for e in row["trace"] if "authoritative_result" in e]


def same_input_diagnostics(rows):
    groups = defaultdict(list)
    for row in rows:
        for index, generation in enumerate(row["generations"]):
            key = canonical([generation["role"], generation["messages"], generation["max_new_tokens"]])
            groups[key].append((row, index, generation))
    repeated = []
    for key, values in sorted(groups.items()):
        if len(values) < 2:
            continue
        returned = [g["reply"] for _, _, g in values if "reply" in g]
        repeated.append({"role": values[0][2]["role"], "calls": len(values), "returned": len(returned),
            "text_variants": len({r["text"] for r in returned}),
            "token_id_variants": len({tuple(r["output_token_ids"]) for r in returned}),
            "input_token_count_variants": len({r["input_tokens"] for r in returned}),
            "locations": [{"id": r["id"], "condition": r["condition"], "generation": i} for r, i, _ in values]})
    return {"repeated_input_groups": len(repeated),
            "groups_with_at_least_two_returned": sum(g["returned"] >= 2 for g in repeated),
            "groups_with_token_disagreement": sum(g["token_id_variants"] > 1 for g in repeated),
            "groups_with_text_disagreement": sum(g["text_variants"] > 1 for g in repeated),
            "groups_with_errors": sum(g["returned"] < g["calls"] for g in repeated), "groups": repeated}


def summarize(rows, gold, scorer):
    """Rows carry model and replay_audit added only after raw replay succeeds."""
    answers = {r["_id"]: r["answer"] for r in gold}
    require(len(answers) == len(gold), "Duplicate gold IDs")
    require(set(answers) == {r["id"] for r in rows}, "Gold identity mismatch")
    scored = []
    for row in rows:
        # No answer or an execution error is scored zero, retained in n=8.
        answer = row["final_answer"]
        em = f1 = 0.0
        if row["termination"] == "finished" and answer is not None:
            em = float(scorer["exact_match_score"](answer, answers[row["id"]]))
            f1 = float(scorer["f1_score"](answer, answers[row["id"]])[0])
        scored.append({"model": row["model"], "id": row["id"], "condition": row["condition"],
                       "em": em, "f1": f1, "termination": row["termination"], "usage": row["usage"],
                       "elapsed_seconds": row["elapsed_seconds"], "replay_audit": row["replay_audit"]})
    models = {}
    for model in sorted({r["model"] for r in rows}):
        raw = [r for r in rows if r["model"] == model]
        data = [r for r in scored if r["model"] == model]
        by_key = {(r["id"], r["condition"]): r for r in raw}
        require(len(by_key) == len(raw), "Duplicate episode")
        ids = sorted({r["id"] for r in raw})
        require(len(ids) == 8 and len(raw) == 24, "Not the frozen eight-task grid")
        arms = {}
        for condition in CONDITIONS:
            group = [r for r in data if r["condition"] == condition]
            require(len(group) == 8, "Incomplete condition")
            arms[condition] = {"n": 8, "em_correct": sum(r["em"] for r in group),
                "mean_f1": sum(r["f1"] for r in group) / 8,
                "terminations": dict(Counter(r["termination"] for r in group)),
                "usage_totals": {role: {k: sum(r["usage"][role][k] for r in group)
                    for k in ("attempts", "input_tokens", "output_tokens", "seconds")} for role in ("actor", "prediction")},
                "elapsed_seconds_sum": sum(r["elapsed_seconds"] for r in group)}
        pairs = []
        score_index = {(r["id"], r["condition"]): r for r in data}
        for condition in ("shared", "isolated"):
            em_delta = [score_index[i, condition]["em"] - score_index[i, "baseline"]["em"] for i in ids]
            pairs.append({"condition_minus_baseline": condition, "n": 8,
                "em_gains": sum(x > 0 for x in em_delta), "em_losses": sum(x < 0 for x in em_delta),
                "em_ties": sum(x == 0 for x in em_delta), "mean_em_difference": sum(em_delta) / 8,
                "mean_f1_difference": sum(score_index[i, condition]["f1"] - score_index[i, "baseline"]["f1"] for i in ids) / 8,
                "authoritative_trajectory_equal_ids": [i for i in ids if canonical(authoritative_projection(by_key[i, condition]))
                    == canonical(authoritative_projection(by_key[i, "baseline"]))],
                "authoritative_observations_equal_ids": [i for i in ids if observation_sequence(by_key[i, condition])
                    == observation_sequence(by_key[i, "baseline"])],
                "actor_message_history_equal_ids": [i for i in ids if by_key[i, condition]["messages"] == by_key[i, "baseline"]["messages"]],
                "final_answer_equal_ids": [i for i in ids if by_key[i, condition]["final_answer"] == by_key[i, "baseline"]["final_answer"]]})
        models[model] = {"conditions": arms, "paired": pairs, "same_input": same_input_diagnostics(raw)}
    return {"scope": "Eight-task development pilot; descriptive, not confirmatory; no speedup claim",
            "scored_episodes": len(rows), "models": models, "episodes": scored}
