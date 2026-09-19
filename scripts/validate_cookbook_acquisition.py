"""Independently recompute the selected-task control from saved MCP responses."""
import hashlib
import json
from pathlib import Path
import sqlite3
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = ROOT / "research/evidence/vakra_cookbook_acquisition_control_v1.json"
    report = json.loads(p.read_bytes())
    assert report["histories"] == 6 and report["independent_tasks"] == 1
    assert sha(ROOT / "autolab/preview_cursor.py") == report["controller_sha256"]
    assert sha(ROOT / "scripts/probe_cookbook_acquisition.py") == report["script_sha256"]
    assert sha(ROOT / "research/cookbook_acquisition_control.md") == report["protocol_sha256"]
    cards_path = ROOT / "research/evidence/vakra_domain_expansion_sql_cards_v1.json"
    assert sha(cards_path) == report["frozen_cards_sha256"]
    card = next(c for c in json.loads(cards_path.read_bytes())["cards"] if c["domain"] == "cookbook" and c["task_index"] == 15)
    database = ROOT / "results/vakra-domain-expansion-v1/cookbook/cookbook.sqlite"
    assert sha(database) == report["database_sha256"] == card["database_sha256"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as con:
        required_rows = [list(row) for row in con.execute(card["sql"]).fetchall()]
    assert required_rows == card["answer_rows"]
    assert sorted({r[1] for r in required_rows}) == report["required_values"]
    rawdir = ROOT / "results/probes/cookbook-acquisition-v1"
    raws = sorted(rawdir.glob("*.json"))
    assert len(raws) == 6
    assert len({r["source"] for r in report["rows"]}) == 6
    results = []
    for raw in raws:
        row = json.loads(raw.read_bytes())
        annotated = next(r for r in report["rows"] if r["source"] == row["source"])
        assert {k: v for k, v in annotated.items() if k != "matches_frozen_sql"} == row
        source = ROOT / row["source"]
        assert sha(source) == row["source_sha256"]
        assert sha(source.parent / "startup.json") == row["startup_sha256"]
        assert all(sha(source.parent / name) == digest for name, digest in row["prior_sha256"].items())
        assert row["exact_replay"]["prior_episodes"] == 15
        entries = row["added_calls"]
        assert len(entries) == 4 and entries[0]["call"]["name"] == "sort_data"
        assert entries[0]["call"]["arguments"]["ascending"] is True
        observed = []
        previous = None
        remaining = []
        for entry in entries:
            response = entry["result"]
            assert response["isError"] is False and len(response["content"]) == 1
            peek = json.loads(response["content"][0]["text"])
            values = next(c["first_3_values"] for c in peek["key_details"] if c["name"] == "Ingredient_name")
            assert values == sorted(values) and len(values) == min(3, peek["num_records"])
            if previous:
                prior_peek, prior_values = previous
                assert entry["call"] == {"name": "filter_data", "arguments": {
                    "data_label": prior_peek["handle"], "key_name": "Ingredient_name",
                    "condition": "greater_than", "value": prior_values[-1]}}
                assert all(v > prior_values[-1] for v in values)
            observed.extend(values)
            remaining.append(peek["num_records"])
            previous = peek, values
        assert remaining == [10, 7, 4, 1]
        assert observed == report["required_values"] == row["control"]["values"]
        assert len(observed) == len(set(observed)) == 10
        assert row["control"]["complete"] and row["target_calls_total"] == len(row["target_prefix"]) + 4 <= 20
        results.append({"raw": raw.relative_to(ROOT).as_posix(), "sha256": sha(raw),
                        "target_calls": row["target_calls_total"], "additional_calls": 4,
                        "observed_complete_ingredients": 10, "remaining_rows": remaining})
    files = [*sorted(rawdir.iterdir()), p, ROOT / "research/cookbook_acquisition_control.md",
             ROOT / "autolab/preview_cursor.py", ROOT / "scripts/probe_cookbook_acquisition.py",
             ROOT / "scripts/validate_cookbook_acquisition.py",
             ROOT / "results/vakra-domain-expansion-v1/cookbook/preparation_manifest.json"]
    archive = ROOT / "results/remote/vakra-cookbook-acquisition-v1-evidence.zip"
    with ZipFile(archive, "x", ZIP_DEFLATED) as z:
        for path in files:
            z.write(path, path.relative_to(ROOT).as_posix())
    with ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(path.relative_to(ROOT).as_posix())).hexdigest() == sha(path) for path in files)
    out = {"purpose": __doc__, "validated": True, "independent_tasks": 1, "histories": results,
           "report_sha256": sha(p), "validator_sha256": sha(Path(__file__)),
           "archive": archive.relative_to(ROOT).as_posix(), "archive_bytes": archive.stat().st_size,
           "archive_entries": len(files), "archive_sha256": sha(archive),
           "limits": "Checks the saved native MCP trace, not an independent model run or proof for unseen data/tool semantics."}
    target = ROOT / "research/evidence/vakra_cookbook_acquisition_validation_v1.json"
    with target.open("x", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"validated_histories": 6, "independent_tasks": 1, "archive_sha256": out["archive_sha256"]}))


if __name__ == "__main__":
    main()
