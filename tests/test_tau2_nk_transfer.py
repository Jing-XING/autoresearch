import copy
import hashlib
from types import SimpleNamespace
import unittest

from autolab.nk_prefix_bank import NKMemoryBank
from autolab.nk_prefix_comparator import CONDITIONS
from autolab.tau2_nk_transfer import verify_choices


class NKTargetSelectionTests(unittest.TestCase):
    def fixture(self):
        value = {'schema': 'autolab.fixed_experience_bank.v1', 'adaptation': 'autolab.nk_prefix_bank.v1',
                 'source_task_ids': ['train'], 'records': [
                     {'record_id': 'source', 'ticket': 'visible ticket',
                      'memories': {'raw': 'raw', **{c: '' for c in CONDITIONS}},
                      'curation': {c: {'status': 'generation_error'} for c in CONDITIONS}}]}
        bank = NKMemoryBank(value)
        tasks = [SimpleNamespace(id=uid, ticket='visible ticket') for uid in ('target1', 'target2')]
        choice = bank.retrieve(tasks[0].ticket, CONDITIONS[0])
        selection = {'rows': [{'task_id': t.id, 'ticket_sha256': hashlib.sha256(t.ticket.encode()).hexdigest(),
                              'source_choice': {k: choice[k] for k in ('record_id', 'similarity', 'tied_candidates', 'pool_size')}}
                             for t in tasks]}
        return tasks, bank, selection

    def test_official_loader_order_does_not_change_registered_order(self):
        tasks, bank, selection = self.fixture()
        actual = verify_choices(tasks[::-1], bank, selection, CONDITIONS[0])
        self.assertEqual([t.id for t in actual], [t.id for t in tasks])

    def test_missing_or_duplicate_task_is_rejected(self):
        tasks, bank, selection = self.fixture()
        for invalid in (tasks[:1], [tasks[0], tasks[0]]):
            with self.assertRaisesRegex(ValueError, 'coverage'):
                verify_choices(invalid, bank, selection, CONDITIONS[0])

    def test_changed_ticket_or_source_choice_is_rejected(self):
        tasks, bank, selection = self.fixture()
        changed = copy.deepcopy(tasks)
        changed[0].ticket = 'changed'
        with self.assertRaisesRegex(ValueError, 'ticket changed'):
            verify_choices(changed, bank, selection, CONDITIONS[0])
        selection['rows'][0]['source_choice']['record_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'Source selection'):
            verify_choices(tasks, bank, selection, CONDITIONS[0])

    def test_invalid_curation_does_not_remove_any_target(self):
        tasks, bank, selection = self.fixture()
        for condition in CONDITIONS:
            self.assertEqual(len(verify_choices(tasks, bank, selection, condition)), 2)


if __name__ == '__main__':
    unittest.main()
