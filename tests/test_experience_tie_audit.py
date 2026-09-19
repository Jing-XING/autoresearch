import unittest

from autolab.experience_memory_bank import FixedMemoryBank
from autolab.experience_tie_audit import ORDERS, TieAuditMemoryBank


def bank_value():
    return {'schema': 'autolab.fixed_experience_bank.v1', 'source_task_ids': ['source'],
            'records': [{'record_id': key, 'ticket': ticket,
                         'memories': {'full_metadata': key + ':full', 'boundary_aware': key + ':boundary'}}
                        for key, ticket in [('c', 'repair network'), ('a', 'repair network'),
                                            ('b', 'repair network'), ('z', 'replace battery')]]}


class TieChoiceTests(unittest.TestCase):
    def test_control_matches_original_retrieval(self):
        data = bank_value()
        for condition in ('full_metadata', 'boundary_aware'):
            prior = FixedMemoryBank(data).retrieve('repair network', condition)
            new = TieAuditMemoryBank(data, 'record_id').retrieve('repair network', condition)
            self.assertEqual(prior, {key: new[key] for key in prior})

    def test_alternatives_stay_within_exact_ties_and_ignore_condition(self):
        choices = []
        for order in ORDERS:
            bank = TieAuditMemoryBank(bank_value(), order)
            x = bank.retrieve('repair network', 'full_metadata')
            y = bank.retrieve('repair network', 'boundary_aware')
            self.assertEqual(x['record_id'], y['record_id'])
            self.assertEqual(x['tied_record_ids'], ['a', 'b', 'c'])
            self.assertAlmostEqual(x['similarity'], 1)
            choices.append(x['record_id'])
        self.assertEqual(set(choices), {'a', 'b', 'c'})

    def test_source_storage_order_does_not_change_choice(self):
        data, reversed_data = bank_value(), bank_value()
        reversed_data['records'].reverse()
        for order in ORDERS:
            self.assertEqual(TieAuditMemoryBank(data, order).retrieve('repair network', 'full_metadata'),
                             TieAuditMemoryBank(reversed_data, order).retrieve('repair network', 'full_metadata'))

    def test_insufficient_ties_rejected(self):
        with self.assertRaises(ValueError):
            TieAuditMemoryBank(bank_value(), 'alternative_1').retrieve('replace battery', 'full_metadata')


if __name__ == '__main__':
    unittest.main()
