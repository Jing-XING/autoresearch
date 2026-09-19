"""Source-localized diagnostic interventions, not an agent recovery algorithm."""
import ast
import copy
from decimal import Decimal
import hashlib
import inspect
import textwrap


def refund_entries(history, mode, payment_type):
    if mode == "payment_only":
        return [p for p in history if p.transaction_type == "payment"]
    if mode != "net_by_method":
        raise ValueError("Unknown intervention")
    balances = {}
    for p in history:
        if p.transaction_type not in ("payment", "refund"):
            raise ValueError("Unknown transaction type")
        amount = Decimal(str(p.amount))
        if not amount.is_finite() or amount < 0:
            raise ValueError("Invalid unsigned amount")
        mid = p.payment_method_id
        balances[mid] = balances.get(mid, Decimal(0)) + amount * (1 if p.transaction_type == "payment" else -1)
    if any(v < 0 for v in balances.values()):
        raise ValueError("Negative outstanding balance outside diagnostic repair scope")
    return [payment_type(transaction_type="payment", amount=float(v), payment_method_id=k)
            for k, v in sorted(balances.items()) if v > 0]


def replace_refund_iterator(original, mode):
    """Replace exactly one loop iterable; retain guards and effect statements."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(original)))
    original_tree = copy.deepcopy(tree)
    expected = ast.dump(ast.parse("order.payment_history", mode="eval").body)
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For) and ast.dump(node.iter) == expected]
    if len(loops) != 1 or mode not in ("payment_only", "net_by_method"):
        raise ValueError("Intervention does not identify one registered loop")
    replacement = ast.parse("_diagnostic_refund_entries(order.payment_history)", mode="eval").body
    loops[0].iter = replacement
    ast.fix_missing_locations(tree)
    # Verify that reverting that single node yields precisely the original AST.
    restored = copy.deepcopy(tree)
    changed = [n for n in ast.walk(restored) if isinstance(n, ast.For)
               and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Name)
               and n.iter.func.id == "_diagnostic_refund_entries"]
    if len(changed) != 1:
        raise ValueError("Unexpected transformed loop")
    changed[0].iter = ast.parse("order.payment_history", mode="eval").body
    if ast.dump(restored) != ast.dump(original_tree):
        raise ValueError("Change exceeds the refund iterator")
    namespace = dict(original.__globals__)
    namespace["_diagnostic_refund_entries"] = lambda h: refund_entries(h, mode, namespace["OrderPayment"])
    exec(compile(tree, "<registered-retail-refund-intervention>", "exec"), namespace)
    return namespace[original.__name__], {
        "mode": mode, "changed_ast_nodes": "one For.iter expression only",
        "original_ast_sha256": hashlib.sha256(ast.dump(original_tree).encode()).hexdigest(),
        "intervention_ast_sha256": hashlib.sha256(ast.dump(tree).encode()).hexdigest(),
        "intervention_source": ast.unparse(tree),
        "scope": "Research copy; unchanged source files; normal native guards and mutations retained"}
