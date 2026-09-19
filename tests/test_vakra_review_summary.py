import copy
import unittest

from autolab.vakra_review_summary import summarize_review


class ReviewSummaryTest(unittest.TestCase):
    def fixture(self):
        rules = [dict(domain='d', uuid=str(i), task_index=i,
                      interpretation_stratum='ambiguous' if i == 2 else 'specified_sql_interpretation')
                 for i in range(3)]
        rows, labels, hashes = [], [], {}
        for rule in rules:
            for condition in ('original', 'coverage_check'):
                source = rule['uuid'] + '-' + condition
                failed = rule['uuid'] == '0' and condition == 'original'
                row = dict(rule, model='m', condition=condition, source=source, call_policy='sequential',
                           termination='protocol_error' if failed else 'agent_finished',
                           final_answer=None if failed else 'fixture answer', usage=dict(model_calls=1))
                rows.append(row)
                hashes[source] = source
                verdict = 'ambiguous' if rule['uuid'] == '2' else 'no_answer' if failed else 'correct'
                labels.append(dict(row, source_sha256=source, answer_label=verdict, reason='fixture'))
        return dict(complete=True, domains=['d'], models=['m'], rows=rows, input_sha256=hashes), \
            dict(complete_batch=True, rows=labels), rules

    def test_failed_episode_retained_and_ambiguous_costs_included(self):
        summary, labels, rules = self.fixture()
        result = summarize_review(summary, labels, rules)
        groups = [r for r in result['groups'] if r['domain'] == 'all']
        self.assertEqual([r['accuracy'] for r in groups], [.5, 1.])
        self.assertEqual([r['executions'] for r in groups], [3, 3])
        self.assertEqual([r['all_execution_usage']['model_calls'] for r in groups], [3, 3])
        pair = result['paired'][-1]
        self.assertEqual(pair['gains'], [dict(domain='d', uuid='0')])
        self.assertEqual(pair['difference_percentage_points'], 50.)

    def test_missing_duplicate_and_pending_review_rejected(self):
        summary, labels, rules = self.fixture()
        variants = [labels['rows'][:-1], labels['rows'] + [labels['rows'][0]]]
        pending = copy.deepcopy(labels['rows'])
        pending[0]['answer_label'] = 'pending'
        variants.append(pending)
        for rows in variants:
            with self.assertRaises(ValueError):
                summarize_review(summary, dict(labels, rows=rows), rules)
        with self.assertRaises(ValueError):
            summarize_review(summary, dict(labels, complete_batch=False), rules)

    def test_mask_and_raw_provenance_changes_rejected(self):
        summary, labels, rules = self.fixture()
        for field, value in [('interpretation_stratum', 'ambiguous'), ('source_sha256', 'stale'),
                             ('task_index', 999), ('source', 'different')]:
            changed = copy.deepcopy(labels)
            changed['rows'][0][field] = value
            with self.assertRaises(ValueError):
                summarize_review(summary, changed, rules)

    def test_correct_label_cannot_hide_failure(self):
        summary, labels, rules = self.fixture()
        labels['rows'][0]['answer_label'] = 'correct'
        with self.assertRaises(ValueError):
            summarize_review(summary, labels, rules)

    def test_incomplete_execution_grid_rejected_even_with_matching_review(self):
        summary, labels, rules = self.fixture()
        summary['rows'].pop()
        labels['rows'].pop()
        with self.assertRaises(ValueError):
            summarize_review(summary, labels, rules)

    def test_closed_domain_requires_opt_in_and_never_claims_complete_batch(self):
        summary, labels, rules = self.fixture()
        summary.update(complete=False, closed_domain='d', closed_domain_complete=True)
        labels.update(complete_batch=False, complete_domain=True, review_scope='d')
        with self.assertRaises(ValueError):
            summarize_review(summary, labels, rules)
        result = summarize_review(summary, labels, rules, allow_closed_domain=True)
        self.assertFalse(result['complete_batch'])
        self.assertEqual({r['domain'] for r in result['groups']}, {'d'})
        self.assertEqual(result['executions'], 6)
        labels['complete_batch'] = True
        with self.assertRaises(ValueError):
            summarize_review(summary, labels, rules, allow_closed_domain=True)

    def test_closed_domain_cannot_hide_missing_review_or_scope_mismatch(self):
        summary, labels, rules = self.fixture()
        summary.update(complete=False, closed_domain='d', closed_domain_complete=True)
        labels.update(complete_batch=False, complete_domain=True, review_scope='d')
        for changed in (dict(labels, rows=labels['rows'][:-1]),
                        dict(labels, review_scope='another-domain'),
                        dict(labels, complete_domain=False)):
            with self.assertRaises(ValueError):
                summarize_review(summary, changed, rules, allow_closed_domain=True)


if __name__ == '__main__':
    unittest.main()
