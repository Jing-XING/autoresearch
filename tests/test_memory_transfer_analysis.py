import unittest
from autolab.analyze_memory_transfer import paired_contrast


class PairedMemoryAnalysisTests(unittest.TestCase):
    def row(self, task, reward):
        return {'model': 'm', 'task_id': task, 'reward': reward}

    def test_task_alignment_and_errors_retained(self):
        treatment = [self.row('b', None), self.row('a', 1), self.row('c', 1)]
        control = [self.row('a', 0), self.row('c', 0), self.row('b', 1)]
        result = paired_contrast(treatment, control)[0]
        self.assertEqual(result['wins'], ['a', 'c'])
        self.assertEqual(result['losses'], ['b'])
        self.assertEqual(result['tasks'], 3)
        self.assertAlmostEqual(result['success_difference'], 1/3)

    def test_missing_target_cannot_be_silently_intersected(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            paired_contrast([self.row('a', 1)], [self.row('a', 1), self.row('b', 0)])

    def test_duplicate_and_pending_observations_rejected(self):
        for values in ([self.row('a', 1), self.row('a', 0)],
                       [dict(self.row('a', None), pending=True)]):
            with self.assertRaisesRegex(ValueError, 'Duplicate or pending'):
                paired_contrast(values, [self.row('a', 1)])


if __name__ == '__main__':
    unittest.main()
