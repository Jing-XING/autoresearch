import itertools
import unittest

import numpy as np

from autolab.risk_development import Difference, METHODS, evaluate, summarize


class RiskDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.target = np.array([[.9, .1], [.2, .8], [.6, .4], [.3, .7]])
        self.proxy = np.array([[.7, .3], [.5, .5], [.1, .9], [.8, .2]])
        self.labels = np.array([0, 0, 1, 1])

    def test_difference_unbiased_over_exhaustive_subsets(self):
        pool = dict(target_probs=self.target, surrogate_probs=self.proxy, n_pool=4, n_classes=2)
        estimates = []
        for indices in itertools.combinations(range(4), 2):
            model = Difference(pool, 2, np.random.default_rng(0))
            for i in indices:
                model.observe(i, int(self.labels[i]))
            estimates.append(model.estimate())
        exact = (-np.log(self.target[np.arange(4), self.labels])).mean()
        self.assertAlmostEqual(float(np.mean(estimates)), float(exact), places=14)

    def test_repeated_queries_cost_budget_and_no_constructor_labels(self):
        class Repeated:
            def __init__(self, pool, budget, rng):
                if set(pool) != {'target_probs', 'surrogate_probs', 'n_pool', 'n_classes'}:
                    raise AssertionError('Unexpected constructor information')
                self.n = 0
            def next_index(self): return 0
            def observe(self, index, label): self.n += 1
            def estimate(self): return self.n
        result = evaluate(Repeated, self.target, self.proxy, self.labels, 3, 7)
        self.assertEqual((result['status'], result['label_calls'], result['distinct_labels']), ('ok', 3, 1))

    def test_failures_retained(self):
        for output in (-1, 4, True, 1.5):
            class Bad:
                def __init__(self, *args): pass
                def next_index(self): return output
            row = evaluate(Bad, self.target, self.proxy, self.labels, 2, 7)
            self.assertEqual(row['status'], 'failed')
            self.assertIsNone(row['squared_error'])
            self.assertEqual(row['label_calls'], 0)

    def test_median_ratios_not_pooled_errors_and_no_case_dropping(self):
        rows = []
        for pool, uniform, difference in [('a', 1., 2.), ('b', 100., 10.)]:
            for method in METHODS:
                rows.append(dict(pool=pool, budget=2, seed=3, method=method, status='ok',
                                 squared_error=difference if method == 'difference' else uniform,
                                 queries=[], permutation_sha256='same'))
        report = summarize(rows, ['a', 'b'], [2], [3])
        self.assertAlmostEqual(report['median_cell_ratio']['difference'], 1.05)
        with self.assertRaises(ValueError): summarize(rows[:-1], ['a', 'b'], [2], [3])
        rows[0]['squared_error'] = 0
        self.assertIsNone(summarize(rows, ['a', 'b'], [2], [3])['median_cell_ratio']['difference'])
        rows[0].update(status='failed', squared_error=None)
        self.assertEqual(summarize(rows, ['a', 'b'], [2], [3])['failures'], 1)


if __name__ == '__main__':
    unittest.main()
