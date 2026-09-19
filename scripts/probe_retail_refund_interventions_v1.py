"""Matched three-implementation census over the frozen native retail population."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
helper_spec = importlib.util.spec_from_file_location("retail_intervention_helpers", ROOT / "autolab/retail_interventions.py")
helper_module = importlib.util.module_from_spec(helper_spec)
helper_spec.loader.exec_module(helper_module)
replace_refund_iterator = helper_module.replace_refund_iterator


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(initial):
    selected, excluded = [], []
    for oid, order in sorted(initial["orders"].items()):
        if order["status"] != "pending":
            excluded.append({"order_id": oid, "reason": "not_pending"})
            continue
        history = order["payment_history"]
        methods = initial["users"][order["user_id"]]["payment_methods"]
        assert len(history) == 1 and history[0]["transaction_type"] == "payment" and history[0]["amount"] > 0
        old = history[0]["payment_method_id"]
        assert old in methods
        amount = Decimal(str(history[0]["amount"]))
        alternatives = [k for k, v in sorted(methods.items()) if k != old and
                        (v["source"] != "gift_card" or Decimal(str(v["balance"])) >= amount)]
        selected.append({"order_id": oid, "alternatives": alternatives})
    return {"total_orders": len(initial["orders"]), "selected": selected, "excluded": excluded}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="Retained native-retail-composition-v1 deployment")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base, output = args.base.resolve(), args.output.resolve()
    upstream = base / "tau"
    probe_path = base / "scripts/probe_tau_retail_payment_cancel_v1.py"
    assert sha(probe_path) == "aa5cd48864960f93732f260e2554524cac7b4f50700c65ac68bc895f07c0440c"
    spec = importlib.util.spec_from_file_location("original_retail_measurement", probe_path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    manifest = json.loads((base / "research/evidence/tau2_source_manifest.json").read_bytes())
    assert probe.digest(manifest) == "d07cc342f43894f866d1fd151fdd1ed996976cb194299e2d87913bc5bc8ee349"
    verified = {p: h for p, h in manifest.items() if p.startswith("src/") or p in
                ("data/tau2/domains/retail/db.json", "data/tau2/domains/retail/policy.md")}
    for rel, digest in verified.items():
        assert sha(upstream / rel) == digest, rel
    os.environ.update(PYTHON_DOTENV_DISABLED="1", LITELLM_LOCAL_MODEL_COST_MAP="True", TAU2_DATA_DIR=str(upstream / "data"))
    connections = []
    def offline(event, values):
        if event == "socket.connect":
            connections.append(str(values[1]))
            raise PermissionError("Offline retail intervention diagnostic")
    sys.addaudithook(offline)
    sys.path.insert(0, str(upstream / "src"))
    from loguru import logger
    logger.remove()
    import tau2
    assert Path(tau2.__file__).resolve().is_relative_to(upstream)
    from tau2.domains.retail.data_model import RetailDB
    from tau2.domains.retail.tools import RetailTools
    tools = RetailTools(RetailDB.load(upstream / "data/tau2/domains/retail/db.json"))
    initial = tools.db.model_dump(mode="json")
    selection = select(initial)
    assert len(selection["selected"]) == 423 and sum(len(x["alternatives"]) for x in selection["selected"]) == 120
    output.mkdir(parents=True, exist_ok=False)
    (output / "selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    native = RetailTools.cancel_pending_order
    methods = {"native": native}
    intervention_metadata = {}
    for mode in ("payment_only", "net_by_method"):
        methods[mode], intervention_metadata[mode] = replace_refund_iterator(native, mode)
    (output / "interventions.json").write_text(json.dumps(intervention_metadata, indent=2) + "\n", encoding="utf-8")
    counts = defaultdict(Counter)
    started = time.monotonic()
    with (output / "records.jsonl").open("x", encoding="utf-8") as stream:
        for entry in selection["selected"]:
            oid = entry["order_id"]
            uid = initial["orders"][oid]["user_id"]
            original_order = tools.db.orders[oid].model_copy(deep=True)
            original_user = tools.db.users[uid].model_copy(deep=True)
            before = {"order": original_order.model_dump(mode="json"), "payment_methods": original_user.model_dump(mode="json")["payment_methods"]}
            original_payment = before["order"]["payment_history"][0]
            old, amount = original_payment["payment_method_id"], Decimal(str(original_payment["amount"]))
            expected_gift = {k: str(Decimal(str(v["balance"])) + (amount if k == old else 0))
                             for k, v in before["payment_methods"].items() if v["source"] == "gift_card"}
            for new in [None] + entry["alternatives"]:
                for mode, cancel in methods.items():
                    tools.db.orders[oid] = original_order.model_copy(deep=True)
                    tools.db.users[uid] = original_user.model_copy(deep=True)
                    kind = "cancel_only" if new is None else "change_then_cancel"
                    calls = []
                    if new is not None:
                        calls.append(("modify_pending_order_payment", tools.modify_pending_order_payment, {"order_id": oid, "payment_method_id": new}))
                    calls.append(("cancel_pending_order", lambda **kw: cancel(tools, **kw), {"order_id": oid, "reason": "no longer needed"}))
                    steps = []
                    for name, operation, kwargs in calls:
                        result = error = None
                        try:
                            result = operation(**kwargs).model_dump(mode="json")
                        except Exception as exc:
                            error = {"type": type(exc).__name__, "message": str(exc)}
                        state = {"order": tools.db.orders[oid].model_dump(mode="json"),
                                 "payment_methods": tools.db.users[uid].model_dump(mode="json")["payment_methods"]}
                        measurement = probe.measure(state["order"], state["payment_methods"], expected_gift)
                        steps.append({"tool": name, "arguments": kwargs, "result": result, "error": error, "state": state, "measurement": measurement})
                        counts[mode]["calls"] += 1
                        if error:
                            counts[mode]["exceptions"] += 1
                            break
                    counts[mode][kind] += 1
                    counts[mode][kind + "_normal_return"] += all(s["error"] is None for s in steps)
                    counts[mode][kind + "_contract_met"] += steps[-1]["measurement"]["cancellation_contract_met"]
                    counts[mode][kind + "_gift_mismatch"] += not steps[-1]["measurement"]["expected_cancelled_gift_balances_met"]
                    row = {"mode": mode, "order_id": oid, "user_id": uid, "kind": kind,
                           "old_payment_method": old, "new_payment_method": new, "before": before,
                           "expected_cancelled_gift_balances": expected_gift, "steps": steps}
                    stream.write(json.dumps(row, separators=(",", ":")) + "\n")
                tools.db.orders[oid] = original_order.model_copy(deep=True)
                tools.db.users[uid] = original_user.model_copy(deep=True)
            tools.db.orders[oid] = original_order
            tools.db.users[uid] = original_user
    restored = probe.digest(tools.db.model_dump(mode="json"))
    assert restored == probe.digest(initial)
    assert RetailTools.cancel_pending_order is native
    summary = {"scope": "Source-informed matched intervention diagnostic; not agent outcomes, novel compensation method or production fix",
        "counts": dict(counts), "paths": sum(c["cancel_only"] + c["change_then_cancel"] for c in counts.values()),
        "unique_orders": 423, "unique_orders_with_alternatives": sum(bool(x["alternatives"]) for x in selection["selected"]),
        "elapsed_seconds": time.monotonic() - started, "python": sys.version,
        "packages": {p: importlib.metadata.version(p) for p in ("pydantic", "loguru", "litellm")},
        "source_files_verified": len(verified), "database_sha256": sha(upstream / "data/tau2/domains/retail/db.json"),
        "initial_database_model_sha256": probe.digest(initial), "restored_database_model_sha256": restored,
        "source_sha256": {p: sha(ROOT / p) for p in ("autolab/retail_interventions.py", "scripts/probe_retail_refund_interventions_v1.py", "research/retail_refund_intervention_protocol_v1.md")},
        "output_sha256": {p: sha(output / p) for p in ("selection.json", "interventions.json", "records.jsonl")},
        "model_calls": 0, "external_connection_attempts": connections, "original_class_method_unchanged": True}
    with (output / "summary.json").open("x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({"paths": summary["paths"], "counts": counts, "elapsed_seconds": summary["elapsed_seconds"]}))
    if connections or any(c["exceptions"] for c in counts.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
