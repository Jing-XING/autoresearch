"""Independent rational-arithmetic audit; does not import measured tool code."""
import argparse
from collections import Counter, defaultdict
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def check(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_zip(path, expected):
    data = path.read_bytes()
    check(sha(data) == expected, "Archive hash mismatch")
    with zipfile.ZipFile(path) as z:
        check(len(z.namelist()) == len(set(z.namelist())), "Duplicate member")
        return {n: z.read(n) for n in z.namelist()}


def net(history):
    balance = defaultdict(Fraction)
    for p in history:
        check(p["transaction_type"] in ("payment", "refund"), "Unknown sign")
        balance[p["payment_method_id"]] += Fraction(str(p["amount"])) * (1 if p["transaction_type"] == "payment" else -1)
    return dict(balance)


def audit(archive, expected_hash):
    files = read_zip(archive, expected_hash)
    report = json.loads(files["run/summary.json"])
    execution = json.loads(files["execution.json"])
    check(execution["returncode"] == 0 and execution["timeout"] is False, "Execution incomplete")
    deployment = json.loads(files["deployment.json"])
    check(deployment["commit"] == "478a06f9c6ccc07eb02e8ed4538a0ba4d80319e1", "Wrong frozen execution commit")
    for name, digest in deployment["files_sha256"].items():
        check(sha(files[name]) == digest == sha((ROOT / name).read_bytes()), "Code differs: " + name)
    for name, digest in report["output_sha256"].items():
        check(sha(files["run/" + name]) == digest, "Saved output hash differs")
    for name, digest in report["source_sha256"].items():
        check(sha(files[name]) == digest, "Experiment source differs")
    expected_files = set(deployment["files_sha256"]) | {"deployment.json", "execution.json", "stdout.log", "stderr.log",
                "run/summary.json", "run/selection.json", "run/interventions.json", "run/records.jsonl"}
    check(set(files) == expected_files, "Missing or extra archive member")
    old_files = read_zip(ROOT / "results/remote/native-retail-composition-v1-results.zip",
        "2586fb106a936211f5c6140f6da7271d91a40c4aabc663a17986df1a95397da5")
    old_rows = [json.loads(x) for x in old_files["run/records.jsonl"].splitlines()]
    old_by_key = {(r["order_id"], r["new_payment_method"]): r for r in old_rows}
    selection = json.loads(files["run/selection.json"])
    check(selection == json.loads(old_files["run/selection.json"]), "Selection changed")
    db_bytes = (ROOT / "results/third_party/tau2-bench/data/tau2/domains/retail/db.json").read_bytes()
    check(sha(db_bytes) == report["database_sha256"] == "dbde692e380bb4ad17f9f7841172cf1e69bebad2daa405628ccdc52a42b3b9b0", "Initial DB changed")
    db = json.loads(db_bytes)
    expected_pairs = set()
    for oid, order in db["orders"].items():
        if order["status"] != "pending":
            continue
        methods = db["users"][order["user_id"]]["payment_methods"]
        check(len(order["payment_history"]) == 1, "Unregistered history")
        payment = order["payment_history"][0]
        expected_pairs.add((oid, None))
        expected_pairs.update((oid, k) for k, m in methods.items() if k != payment["payment_method_id"] and
                    (m["source"] != "gift_card" or Fraction(str(m["balance"])) >= Fraction(str(payment["amount"]))))
    check(set(old_by_key) == expected_pairs and len(expected_pairs) == 543, "Pair population differs")
    rows = [json.loads(x) for x in files["run/records.jsonl"].splitlines()]
    by_key = {(r["mode"], r["order_id"], r["new_payment_method"]): r for r in rows}
    modes = ("native", "payment_only", "net_by_method")
    check(len(rows) == len(by_key) == 1629 and set(by_key) == {(m, o, p) for m in modes for o, p in expected_pairs}, "Incomplete matched grid")
    counts = defaultdict(Counter)
    direct_equal = prefix_equal = original_equal = 0
    signatures = defaultdict(Counter)
    for (mode, oid, new), row in by_key.items():
        old = old_by_key[oid, new]
        check(row["before"] == old["before"], "Initial affected state differs")
        check(all(row["before"]["order"][k] == v for k, v in db["orders"][oid].items()), "Order differs from public initial DB")
        check(row["before"]["payment_methods"] == db["users"][row["user_id"]]["payment_methods"], "Payment methods differ from initial DB")
        if mode == "native":
            check({k: v for k, v in row.items() if k != "mode"} == old, "Native rerun differs from earlier census")
            original_equal += 1
        check(row["kind"] == ("cancel_only" if new is None else "change_then_cancel"), "Wrong path kind")
        check([s["tool"] for s in row["steps"]] == (["cancel_pending_order"] if new is None else ["modify_pending_order_payment", "cancel_pending_order"]), "Wrong operations")
        if new is None:
            check(row["steps"] == old["steps"], "Direct cancellation differs across implementations")
            direct_equal += 1
            previous = row["before"]
        else:
            check(row["steps"][0] == old["steps"][0], "Payment-change prefix differs")
            prefix_equal += 1
            previous = row["steps"][0]["state"]
        history = previous["order"]["payment_history"]
        if mode == "native":
            entries = history
        elif mode == "payment_only":
            entries = [p for p in history if p["transaction_type"] == "payment"]
        else:
            balances = net(history)
            check(all(v >= 0 for v in balances.values()), "Negative net outside repair scope")
            entries = [{"payment_method_id": k, "amount": float(v)} for k, v in sorted(balances.items()) if v > 0]
        expected_state = copy.deepcopy(previous)
        refunds = [dict(transaction_type="refund", amount=p["amount"], payment_method_id=p["payment_method_id"]) for p in entries]
        expected_state["order"].update(status="cancelled", cancel_reason="no longer needed", payment_history=history + refunds)
        for mid, method in expected_state["payment_methods"].items():
            if method["source"] == "gift_card":
                added = sum((Fraction(str(p["amount"])) for p in refunds if p["payment_method_id"] == mid), Fraction())
                method["balance"] = float(Fraction(str(method["balance"])) + added)
        last = row["steps"][-1]
        check(last["arguments"] == {"order_id": oid, "reason": "no longer needed"}, "Cancel arguments differ")
        check(last["state"] == expected_state and last["result"] == expected_state["order"], "Saved cancellation effects differ from independent reconstruction")
        check(all(s["error"] is None for s in row["steps"]), "Recorded exception")
        balances = net(expected_state["order"]["payment_history"])
        original_payment = row["before"]["order"]["payment_history"][0]
        amount = Fraction(str(original_payment["amount"]))
        expected_gift = {k: Fraction(str(v["balance"])) + (amount if k == row["old_payment_method"] else 0)
                         for k, v in row["before"]["payment_methods"].items() if v["source"] == "gift_card"}
        check({k: Fraction(v) for k, v in row["expected_cancelled_gift_balances"].items()} == expected_gift, "Declared gift target differs")
        gift_delta = {k: Fraction(str(expected_state["payment_methods"][k]["balance"])) - v for k, v in expected_gift.items()}
        gift_ok = all(abs(v) <= Fraction(1, 1000000) for v in gift_delta.values())
        contract = all(v == 0 for v in balances.values()) and gift_ok
        measured = last["measurement"]
        check({k: Fraction(v) for k, v in measured["signed_net_by_method"].items()} == balances, "Reported net differs")
        check(measured["cancellation_contract_met"] == contract and measured["expected_cancelled_gift_balances_met"] == gift_ok, "Reported contract differs")
        kind = row["kind"]
        counts[mode][kind] += 1
        counts[mode][kind + "_normal_return"] += 1
        counts[mode][kind + "_contract_met"] += contract
        counts[mode][kind + "_gift_mismatch"] += not gift_ok
        counts[mode]["calls"] += len(row["steps"])
        if new is not None:
            signature = (str(balances[row["old_payment_method"]] / amount), str(balances[new] / amount), len(expected_state["order"]["payment_history"]))
            signatures[mode][signature] += 1
    for mode in modes:
        check(dict(counts[mode]) == report["counts"][mode], "Summary count mismatch")
    check(report["initial_database_model_sha256"] == report["restored_database_model_sha256"] and
          report["original_class_method_unchanged"] is True and report["model_calls"] == 0 and not report["external_connection_attempts"], "Runtime scope mismatch")
    return {"status": "independently-recomputed", "counts": dict(counts), "native_paths_equal_to_prior_census": original_equal,
        "direct_paths_equal_including_native": direct_equal, "payment_change_prefixes_equal_including_native": prefix_equal,
        "composition_signatures": {m: [{"old_net_over_amount": k[0], "new_net_over_amount": k[1], "ledger_entries": k[2], "paths": v} for k, v in c.items()] for m, c in signatures.items()},
        "archive_sha256": expected_hash, "archive_bytes": archive.stat().st_size, "archive_members": len(files),
        "execution": execution, "source_sha256": sha(Path(__file__).read_bytes()),
        "scope": "Saved-state reconstruction with rational arithmetic; no native/model execution; whole-DB restoration is a retained runtime assertion"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = audit(args.archive, args.sha256)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
