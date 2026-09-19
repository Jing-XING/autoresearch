"""Development-only controlled pilot. Synthetic tasks cannot establish paper claims."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import random
import sqlite3

from autolab.local_smoke import LocalTransformersModel, sha256_file
from autolab.tool_agent import Budget, run_episode, write_episode


class SQLTask:
    """Read-only synthetic database with a separate, exact integer evaluator."""
    def __init__(self, seed: int, family: int):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("CREATE TABLE accounts(id INTEGER, region TEXT); "
                              "CREATE TABLE orders(id INTEGER, account_id INTEGER, cents INTEGER, status TEXT);")
        rng = random.Random(seed)
        accounts = [(i, rng.choice(["north", "south", "west"])) for i in range(1, 21)]
        orders = [(i, rng.randint(1, 20), rng.randint(1, 500)*100,
                   rng.choice(["paid", "cancelled", "pending"])) for i in range(1, 121)]
        self.db.executemany("INSERT INTO accounts VALUES (?,?)", accounts)
        self.db.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
        region = rng.choice(["north", "south", "west"])
        target = {a for a, r in accounts if r == region}
        selected = [o for o in orders if o[1] in target and o[3] == "paid"]
        prompts = [f"Report total paid order cents for accounts in {region}.",
                   f"Report the number of distinct accounts in {region} with a paid order.",
                   f"Report the largest paid order amount in cents for accounts in {region}; use 0 if none."]
        self.expected = [sum(o[2] for o in selected), len({o[1] for o in selected}),
                         max([o[2] for o in selected], default=0)][family % 3]
        self.task = prompts[family % 3] + " Inspect the database as needed and submit the integer with submit_answer."
        self.answer = None
        self.db.set_authorizer(lambda action, *args: sqlite3.SQLITE_OK
                               if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
                                             sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE} else sqlite3.SQLITE_DENY)

    def tools(self):
        return [{"name": "schema", "arguments": {}, "description": "Return SQL table schemas."},
                {"name": "query", "arguments": {"sql": "one SQLite SELECT query"},
                 "description": "Read-only SQL; returns at most 30 rows. Amounts are integer cents."},
                {"name": "submit_answer", "arguments": {"value": "integer"},
                 "description": "Submit the answer. No correctness feedback is supplied."}]

    def execute(self, name, arguments):
        if name == "schema" and not arguments:
            return {"tables": ["accounts(id INTEGER, region TEXT)",
                               "orders(id INTEGER, account_id INTEGER, cents INTEGER, status TEXT)"],
                    "join": "orders.account_id = accounts.id"}
        if name == "query" and set(arguments) == {"sql"} and isinstance(arguments["sql"], str):
            remaining = 100
            def stop():
                nonlocal remaining
                remaining -= 1
                return int(remaining <= 0)
            self.db.set_progress_handler(stop, 1000)
            try:
                cur = self.db.execute(arguments["sql"])
                rows = cur.fetchmany(31)
                return {"columns": [c[0] for c in cur.description], "rows": rows[:30],
                        "truncated": len(rows) > 30}
            except sqlite3.Error as exc:
                return {"error": str(exc)}
            finally:
                self.db.set_progress_handler(None, 0)
        if name == "submit_answer" and set(arguments) == {"value"} and type(arguments["value"]) is int:
            self.answer = arguments["value"]
            return {"status": "recorded"}
        return {"error": "invalid_arguments"}

    def evaluate(self):
        return {"success": self.answer == self.expected, "submitted": self.answer,
                "expected": self.expected}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-path", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=4)
    args = p.parse_args()
    if args.shards < 1 or not 0 <= args.shard < args.shards:
        p.error("invalid shard")
    model = LocalTransformersModel(args.model_path)
    metadata = {"purpose": "synthetic_development_screening_only", "seed": 20260919,
                "source_sha256": sha256_file(Path(__file__)), "shard": args.shard,
                "model": str(args.model_path), "torch": model.torch.__version__}
    write_episode(metadata, args.output, f"shard-{args.shard}-manifest")
    # Fixed before observing results; all cases retained, including source successes.
    for case in range(args.shard, 12, args.shards):
        source = SQLTask(7000 + case, case)
        source_budget = Budget(model_calls=6, tool_calls=2 if case < 6 else 4, max_new_tokens=192)
        result = run_episode(model, source, source.task, source_budget, {**metadata, "case": case, "phase": "source"})
        write_episode(result, args.output, f"case-{case:02d}-source")
        source.db.close()
        # Both curators see identical observable evidence, including the cutoff and budget.
        # The oracle answer is not exposed to either curator.
        evidence = {"task": source.task, "trace": result["trace"], "budget": asdict(source_budget),
                    "termination": result["termination"], "success": result["evaluation"]["success"]}
        memories = {"none": "", "raw": json.dumps(evidence)}
        for condition, instruction in [
            ("reflection", "Write a concise reusable lesson from this experience for related future tasks."),
            ("scoped", "Write a concise reusable lesson. State what the observations establish, distinguish resource cutoff from method failure, and specify when a different task budget would invalidate any negative conclusion.")]:
            reply = model.generate([{"role": "system", "content": instruction + " Do not invent evidence or future answers."},
                                    {"role": "user", "content": json.dumps(evidence)}], 256)
            memories[condition] = reply.text
            write_episode({"metadata": metadata, "condition": condition, "evidence": evidence,
                           "instruction": instruction, "reply": asdict(reply)}, args.output,
                          f"case-{case:02d}-memory-{condition}")
        for condition, memory in memories.items():
            target = SQLTask(9000 + case, case)
            trial = run_episode(model, target, target.task,
                                Budget(model_calls=10, tool_calls=7, max_new_tokens=192),
                                {**metadata, "case": case, "phase": "target", "condition": condition}, memory)
            write_episode(trial, args.output, f"case-{case:02d}-target-{condition}")
            target.db.close()
            print(json.dumps({"case": case, "condition": condition,
                              "success": trial["evaluation"]["success"], "termination": trial["termination"]}), flush=True)
    print("PILOT_SHARD_COMPLETE", args.shard, flush=True)


if __name__ == "__main__":
    main()
