from dataclasses import dataclass
from types import SimpleNamespace
import unittest

from autolab.retail_interventions import refund_entries, replace_refund_iterator


@dataclass
class OrderPayment:
    transaction_type: str
    amount: float
    payment_method_id: str


def fixture_cancel(self, order):
    if order.status != "pending":
        raise ValueError("state guard")
    added = []
    for payment in order.payment_history:
        added.append((payment.payment_method_id, payment.amount))
    self.marker = "body executed"
    return added


class InterventionTest(unittest.TestCase):
    def test_old_refund_is_neither_a_new_charge_nor_an_outstanding_charge(self):
        history = [OrderPayment("payment", .3, "old"), OrderPayment("payment", .3, "new"),
                   OrderPayment("refund", .3, "old")]
        self.assertEqual([(p.payment_method_id, p.amount) for p in refund_entries(history, "payment_only", OrderPayment)], [("old", .3), ("new", .3)])
        self.assertEqual([(p.payment_method_id, p.amount) for p in refund_entries(history, "net_by_method", OrderPayment)], [("new", .3)])
        self.assertEqual(len(history), 3)

    def test_partial_refund_and_negative_balance_scope(self):
        history = [OrderPayment("payment", .3, "a"), OrderPayment("refund", .1, "a")]
        self.assertEqual(refund_entries(history, "net_by_method", OrderPayment)[0].amount, .2)
        with self.assertRaisesRegex(ValueError, "Negative outstanding"):
            refund_entries([OrderPayment("refund", .1, "a")], "net_by_method", OrderPayment)

    def test_ast_intervention_preserves_state_guard_and_body(self):
        operation, metadata = replace_refund_iterator(fixture_cancel, "net_by_method")
        actor = SimpleNamespace()
        order = SimpleNamespace(status="pending", payment_history=[OrderPayment("payment", 10, "a"), OrderPayment("refund", 10, "a")])
        self.assertEqual(operation(actor, order), [])
        self.assertEqual(actor.marker, "body executed")
        self.assertNotEqual(metadata["original_ast_sha256"], metadata["intervention_ast_sha256"])
        order.status = "cancelled"
        with self.assertRaisesRegex(ValueError, "state guard"):
            operation(actor, order)
        self.assertEqual(fixture_cancel(SimpleNamespace(), SimpleNamespace(status="pending", payment_history=order.payment_history)), [("a", 10), ("a", 10)])


if __name__ == "__main__":
    unittest.main()
