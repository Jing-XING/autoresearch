import json
import unittest
from autolab.tool_evidence_ledger import EvidenceLedger


def peek(handle, n, column='Language'):
    return {'handle':handle,'num_records':n,'key_details':[
        {'name':column,'first_3_values':['x']*min(n,3)}]}


def result(value, error=False):
    return {'isError':error,'content':[{'type':'text','text':json.dumps(value)}]}


def call(name, handle='root', **kwargs):
    return {'name':name,'arguments':{'data_label':handle,**kwargs}}


class TestEvidenceLedger(unittest.TestCase):
    def ledger(self):
        return EvidenceLedger(peek('root',8),'u1',['get_Languages'])

    def test_preview_is_not_full_column_and_getter_can_complete_it(self):
        ledger = self.ledger()
        ledger.observe(call('select_data_equal_to',key_name='Language',value='x'),result(peek('subset',4)))
        self.assertFalse(ledger.handles['subset']['columns']['Language']['complete_column_observed'])
        ledger.observe(call('get_Languages','subset'),result(['a','b','c','d']))
        self.assertTrue(ledger.handles['subset']['columns']['Language']['complete_column_observed'])
        self.assertFalse(ledger.handles['root']['columns']['Language']['complete_column_observed'])

    def test_parallel_branch_does_not_inherit_other_branch_predicate(self):
        ledger = self.ledger()
        ledger.observe(call('select_data_greater_than',key_name='Language',value=80),result(peek('percent',5)))
        ledger.observe(call('select_data_equal_to',key_name='Language',value='Estonia'),result(peek('country',4)))
        self.assertEqual(len(ledger.handles['country']['predicates']),1)
        self.assertEqual(ledger.handles['country']['predicates'][0]['value'],'Estonia')

    def test_error_payload_with_false_flag_cannot_add_evidence(self):
        ledger=self.ledger()
        before=ledger.snapshot()['handles']
        event=ledger.observe(call('get_Languages'),{'isError':False,'content':[
            {'type':'text','text':"Input validation error: 'Language'"}]})
        self.assertEqual(event['status'],'error')
        self.assertEqual(before,ledger.snapshot()['handles'])

    def test_unknown_transformation_cannot_keep_certified_predicate(self):
        ledger=self.ledger()
        ledger.observe(call('select_data_equal_to',key_name='Language',value='x'),result(peek('subset',4)))
        ledger.observe(call('transform_data','subset'),result(peek('changed',4)))
        ledger.observe(call('select_data_equal_to','changed',key_name='Language',value='y'),result(peek('later',1)))
        self.assertEqual(ledger.handles['later']['lineage_status'],'unknown_operation')
        self.assertEqual(ledger.handles['later']['predicates'],[])

    def test_new_universe_invalidates_handles_and_zero_rows_complete(self):
        ledger=self.ledger()
        ledger.observe({'name':'get_data','arguments':{'tool_universe_id':'u2'}},result(peek('new',0)))
        self.assertNotIn('root',ledger.handles)
        self.assertTrue(ledger.handles['new']['columns']['Language']['complete_column_observed'])
        self.assertEqual(ledger.universe_id,'u2')

    def test_wrong_length_getter_does_not_certify_completeness(self):
        ledger=self.ledger()
        e=ledger.observe(call('get_Languages'),result(['x']))
        self.assertFalse(e['column_observation']['matches_handle_cardinality'])
        self.assertFalse(ledger.handles['root']['columns']['Language']['complete_column_observed'])


if __name__=='__main__':
    unittest.main()
