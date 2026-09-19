import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('retail_probe', Path(__file__).resolve().parents[1]/'scripts/probe_tau_retail_payment_cancel_v1.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class MeasurementTests(unittest.TestCase):
    def test_opposite_instrument_balances_do_not_cancel_each_other(self):
        order = dict(status='cancelled', payment_history=[
            dict(transaction_type='payment', amount=10, payment_method_id='a'),
            dict(transaction_type='refund', amount=10, payment_method_id='b')])
        result = probe.measure(order, {}, {})
        self.assertEqual(result['signed_net_total'], '0')
        self.assertFalse(result['cancellation_contract_met'])

    def test_history_need_not_be_erased_and_gift_balance_is_independent(self):
        order = dict(status='cancelled', payment_history=[
            dict(transaction_type='payment', amount=.1, payment_method_id='a'),
            dict(transaction_type='refund', amount=.1, payment_method_id='a')])
        methods = {'a':dict(source='gift_card',balance=3.1)}
        self.assertTrue(probe.measure(order, methods, {'a':'3.1'})['cancellation_contract_met'])
        self.assertFalse(probe.measure(order, methods, {'a':'3.0'})['cancellation_contract_met'])

    def test_transaction_type_validation(self):
        with self.assertRaises(ValueError):
            probe.signed_balances([dict(transaction_type='unknown',amount=1,payment_method_id='a')])


if __name__ == '__main__': unittest.main()
