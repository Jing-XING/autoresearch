import unittest

from autolab.memory_tie_sensitivity import describe_tie_sensitivity


class TieSensitivityTest(unittest.TestCase):
    def fixture(self):
        reg = dict(tie_orders=['record_id', 'alternative_1', 'alternative_2'],
                   selected_task_ids=['a', 'b', 'c'], models=['m'],
                   memory_conditions=['full_metadata', 'boundary_aware'],
                   rows=[dict(task_id=t, ticket_sha256='one' if t == 'a' else 'two') for t in 'abc'])
        rows = [dict(model='m', task_id=t, tie_order=tie, condition=c,
                     ticket_sha256='one' if t == 'a' else 'two', reward=0)
                for tie in reg['tie_orders'] for c in reg['memory_conditions'] for t in 'abc']
        return reg, rows

    def test_group_weighting_and_error_retention(self):
        reg, rows = self.fixture()
        for row in rows:
            if row['condition'] == 'boundary_aware':
                row['reward'] = 1 if row['task_id'] == 'a' else None
        result = describe_tie_sensitivity(rows, reg)
        first = result['treatment_effects'][0]
        self.assertAlmostEqual(first['micro_difference'], 1 / 3)
        self.assertEqual(first['uniform_ticket_macro_difference'], 0.5)
        groups = {r['ticket_sha256']: r for r in first['ticket_groups']}
        self.assertEqual(groups['one']['leave_this_ticket_out_difference'], 0)
        self.assertEqual(groups['two']['leave_this_ticket_out_difference'], 1)
        self.assertTrue(all(x['changed_tasks'] == 0 for x in result['within_condition_tie_changes']))

    def test_opposite_tie_effects_are_not_pooled_away(self):
        reg, rows = self.fixture()
        for row in rows:
            if row['task_id'] == 'a':
                row['reward'] = int((row['tie_order'], row['condition']) in
                                   [('record_id', 'boundary_aware'), ('alternative_1', 'full_metadata')])
        result = describe_tie_sensitivity(rows, reg)
        self.assertEqual([r['micro_difference'] for r in result['treatment_effects']], [1 / 3, -1 / 3, 0])
        changes = next(x for x in result['within_condition_tie_changes']
                       if x['condition'] == 'full_metadata' and x['right'] == 'alternative_1')
        self.assertEqual(changes['gains'], ['a'])
        self.assertEqual(changes['losses'], [])

    def test_missing_duplicate_and_changed_groups_rejected(self):
        reg, rows = self.fixture()
        for bad in (rows[:-1], rows + [rows[0]], [dict(rows[0], ticket_sha256='wrong')] + rows[1:]):
            with self.assertRaises(ValueError):
                describe_tie_sensitivity(bad, reg)

    def test_identical_lessons_keep_reproducibility_disagreement_visible(self):
        reg, rows = self.fixture()
        for row in rows:
            if row['task_id'] == 'a' and row['condition'] == 'full_metadata' and row['tie_order'] != 'record_id':
                row['memory_text_sha256'] = 'same-lesson'
                row['model_io_sha256'] = row['tie_order']
        checks = describe_tie_sensitivity(rows, reg)['duplicate_content_checks']
        self.assertEqual(len(checks), 1)
        self.assertFalse(checks[0]['identical_model_io'])
        self.assertTrue(checks[0]['identical_recorded_rewards'])


if __name__ == '__main__':
    unittest.main()
