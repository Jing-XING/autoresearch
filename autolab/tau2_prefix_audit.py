"""Offline state-satisfaction audit; never replaces official episode rewards.

Uses hidden benchmark assertions AFTER a trajectory has been collected. These
diagnostic labels must not be passed to an agent, stopping rule, or memory curator.
"""
import argparse
import hashlib
import json
from pathlib import Path


def audit_prefixes(simulation, task, domain="telecom"):
    from tau2.data_model.message import AssistantMessage, ToolMessage
    from tau2.data_model.tasks import RewardType
    from tau2.evaluator.evaluator_env import EnvironmentEvaluator
    from tau2.evaluator.evaluator_action import ActionEvaluator
    from tau2.environment.toolkit import get_tool_types
    from tau2.registry import registry

    if simulation.task_id != task.id:
        raise ValueError("Task identity mismatch")
    basis = set(task.evaluation_criteria.reward_basis)
    if not basis or not basis <= {RewardType.DB, RewardType.ENV_ASSERTION, RewardType.ACTION}:
        raise ValueError("Audit supports only nonempty environment/action reward bases")
    environment = registry.get_env_constructor(domain)(solo_mode=True)
    tool_types = {}
    for toolkit in (environment.tools, environment.user_tools):
        if toolkit is not None:
            tool_types.update(get_tool_types(toolkit))
    messages = simulation.messages
    boundaries = [(0, 0, 0)]
    pos, generation, tools = 0, 0, 0
    while pos < len(messages):
        message = messages[pos]
        if not isinstance(message, AssistantMessage):
            raise ValueError("Expected solo assistant at generation boundary")
        generation += 1
        calls = message.tool_calls or []
        end = pos + 1 + len(calls)
        if end > len(messages):
            raise ValueError("Incomplete tool-result group")
        for offset, call in enumerate(calls):
            response = messages[pos + 1 + offset]
            if not isinstance(response, ToolMessage) or response.id != call.id:
                raise ValueError("Tool-result order or identity mismatch")
        tools += len(calls)
        boundaries.append((end, generation, tools))
        pos = end
    rows = []
    for end, generation, tools in boundaries:
        score = EnvironmentEvaluator.calculate_reward(
            environment_constructor=registry.get_env_constructor(domain),
            task=task, full_trajectory=messages[:end], solo_mode=True,
            strict_replay=True,
        )
        action_score = ActionEvaluator.calculate_reward(
            task=task, full_trajectory=messages[:end], tool_types=tool_types,
        ) if RewardType.ACTION in basis else None
        task_satisfied = score.reward == 1.0 and (action_score is None or action_score.reward == 1.0)
        rows.append({"message_count": end, "generation_count": generation,
                     "tool_count": tools, "state_satisfied": score.reward == 1.0,
                     "action_satisfied": action_score.reward == 1.0 if action_score is not None else None,
                     "task_satisfied": task_satisfied})
    if simulation.termination_reason.value == "agent_stop":
        if float(rows[-1]["task_satisfied"]) != simulation.reward_info.reward:
            raise ValueError("Final replay disagrees with official environment/action reward")
    first = next((r["generation_count"] for r in rows if r["task_satisfied"]), None)
    regressions = [after["generation_count"] for before, after in zip(rows, rows[1:])
                   if before["task_satisfied"] and not after["task_satisfied"]]
    return {"task_id": task.id, "official_reward": simulation.reward_info.reward,
            "termination": simulation.termination_reason.value,
            "first_satisfied_generation": first, "regressions": regressions,
            "final_state_satisfied": rows[-1]["state_satisfied"],
            "final_task_satisfied": rows[-1]["task_satisfied"], "prefixes": rows,
            "meaning": "offline hidden-assertion state diagnostic, not policy-visible feedback or revised benchmark reward"}


def main():
    from tau2.data_model.simulation import SimulationRun
    from tau2.runner.helpers import get_tasks
    from autolab.tau2_native_baseline import verify_tau_source

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--tau-repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--split", choices=["small", "train"], default="small")
    args = parser.parse_args()
    source_hash = verify_tau_source(args.tau_repo)
    tasks = {t.id: t for t in get_tasks("telecom", task_split_name=args.split)}
    rows, failures, hashes = [], [], {}
    for file in sorted(args.root.glob("*/shard-*/case-*-status.json")):
        status = json.loads(file.read_bytes())
        simulation_file = file.with_name(file.name.replace("-status", ""))
        identity = {"model": file.parent.parent.name, "status_file": file.relative_to(args.root).as_posix()}
        hashes[identity["status_file"]] = hashlib.sha256(file.read_bytes()).hexdigest()
        if status["reward"] is None:
            failures.append({**identity, "task_id": status["task_id"], "reason": "original_run_error"})
            continue
        simulation = SimulationRun.model_validate_json(simulation_file.read_bytes())
        hashes[simulation_file.relative_to(args.root).as_posix()] = hashlib.sha256(simulation_file.read_bytes()).hexdigest()
        result = audit_prefixes(simulation, tasks[status["task_id"]])
        rows.append({**identity, **result})
    if not rows and not failures:
        raise ValueError("No recorded cases found")
    report = {"purpose": "development trajectory diagnosis only", "task_split": args.split, "tau_source_sha256": source_hash,
              "input_sha256": hashes, "rows": rows, "unscored_runs": failures}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"audited": len(rows), "unscored": len(failures),
                      "ever_satisfied": sum(r["first_satisfied_generation"] is not None for r in rows),
                      "regression_episodes": sum(bool(r["regressions"]) for r in rows),
                      "satisfied_but_official_failed": sum(r["final_task_satisfied"] and r["official_reward"] == 0 for r in rows)}))


if __name__ == "__main__":
    main()
