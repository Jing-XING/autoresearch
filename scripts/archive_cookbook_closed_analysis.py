"""Record the completed cookbook slice and one post-review trace illustration.

Offline extraction only: no new model or MCP execution and no grounding score.
"""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    archive = root / "results/remote/vakra-expansion-v2-cookbook-complete.zip"
    expected = "a90bdb22b55df407cebc722d1f8635820d1c1e2a8a8981cc9142e8f301cec0b7"
    assert sha(archive) == expected
    with ZipFile(archive) as z:
        assert z.testzip() is None and len(z.infolist()) == 145
        assert sum(Path(n).name.startswith("case-") for n in z.namelist()) == 120
    raw = root / "results/remote/vakra-expansion-v2-cookbook-complete/runs/vakra-expansion-v2/cookbook/coverage_check/qwen30b/shard-0/case-015.json"
    cards_path = root / "research/evidence/vakra_domain_expansion_sql_cards_v1.json"
    record = json.loads(raw.read_text(encoding="utf-8"))
    cards = json.loads(cards_path.read_text(encoding="utf-8"))["cards"]
    card = next(c for c in cards if c["domain"] == "cookbook" and c["task_index"] == 15)
    assert card["uuid"] == record["uuid"]
    step = record["trace"][8]
    call = step["calls"][0]
    assert call["tool_call"]["name"] == "select_unique_values"
    arguments = call["tool_call"]["arguments"]["unique_array"]
    result = json.loads(call["tool_result"]["content"][0]["text"])
    assert call["tool_result"]["isError"] is False and arguments == result
    assert len(result) == 10 and all(v in record["final_answer"] for v in result)
    gold = [row[1] for row in card["answer_rows"]]
    assert set(gold) != set(result)
    runtime = root / "results/vakra-domain-expansion-v1/cookbook/runtime/environment/m3/python_tools"
    implementation = runtime / "tools/slot_filling_tools.py"
    source = implementation.read_text(encoding="utf-8")
    start = source.index("def select_unique_values(")
    end = source.index("\ndef truncate(", start)
    helper_source = source[start:end].strip()
    assert "return list(dict.fromkeys(unique_array))" in helper_source
    evidence = root / "research/evidence"
    receipt = {
        "scope": "First fully completed domain of the registered 420-episode expansion; full batch incomplete at extraction.",
        "complete_batch": False, "complete_domain": True, "domain": "cookbook",
        "episodes": 120, "distinct_tasks": 20, "successful_worker_exits": 6,
        "archive": archive.relative_to(root).as_posix(), "archive_bytes": archive.stat().st_size,
        "archive_entries": 145, "archive_sha256": expected,
        "deployment_archive_sha256": sha(root / "results/deploy/vakra-expansion-v2.zip"),
        "review": "All 120 finals reviewed by one unblinded assistant; four frozen ambiguous tasks remain excluded from accuracy, not resource accounting.",
        "evidence_sha256": {p.name: sha(p) for p in [
            evidence / "vakra_expansion_cookbook_closed_grid_v1.json",
            evidence / "vakra_expansion_cookbook_annotations_v1.json",
            evidence / "vakra_expansion_cookbook_answer_summary_v1.json"]},
        "script_sha256": sha(Path(__file__)),
    }
    illustration = {
        "purpose": "Post-review illustrative extraction, not a new execution, counterfactual replay, prevalence estimate or formal grounding score.",
        "raw_path": raw.relative_to(root).as_posix(), "raw_sha256": sha(raw),
        "cards_sha256": sha(cards_path), "uuid": record["uuid"],
        "query": record["query"], "step": step["step"],
        "helper_call": call, "final_answer": record["final_answer"],
        "reference_card": card,
        "helper_source_path": implementation.relative_to(root).as_posix(),
        "helper_source_sha256": sha(implementation), "helper_source": helper_source,
        "server_source_sha256": sha(runtime / "mcp/mcp_server.py"),
        "checks": {"successful_helper_output_equals_agent_input": True,
                   "final_repeats_all_ten_helper_values": True,
                   "literal_set_differs_from_reference": True},
        "interpretation": "This helper deduplicates the agent-supplied array. Its successful response adds no independent database retrieval. Even allowing cumin/cinnamon aliases, several substituted ingredients and missing reference ingredients make the answer incorrect.",
        "limits": "No claim that all supplied values are absent from all earlier prose, no hidden-reasoning attribution, no claim that the interface makes every complete-list task impossible. Cookbook retrieve_data returns a handle/preview and must not be equated with the prior publishing domain's full-column getter.",
    }
    for name, value in [("vakra_expansion_cookbook_raw_receipt_v1.json", receipt),
                        ("vakra_cookbook_helper_trace_v1.json", illustration)]:
        (evidence / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archive_verified": True, "episodes": 120, "helper_input_equals_output": True}))


if __name__ == "__main__":
    main()
