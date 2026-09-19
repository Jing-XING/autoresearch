import unittest
from scripts.audit_retail_archive_composition_v1 import extract, ledger


def call(i,name):return {'id':i,'name':name,'arguments':{'order_id':'o'},'requestor':'assistant'}
def response(i,status,history):
    import json
    return {'role':'tool','id':i,'requestor':'assistant','error':False,
            'content':json.dumps({'order_id':'o','status':status,'payment_history':history})}


class ArchiveTests(unittest.TestCase):
    def test_aggregate_zero_does_not_hide_instrument_errors(self):
        h=[{'transaction_type':'payment','payment_method_id':'a','amount':5},
           {'transaction_type':'refund','payment_method_id':'b','amount':5}]
        self.assertFalse(ledger({'payment_history':h})['all_methods_zero'])

    def test_result_order_controls_composition(self):
        change=call('a','modify_pending_order_payment');cancel=call('b','cancel_pending_order')
        msgs=[{'role':'assistant','tool_calls':[change]},response('a','pending',[]),
              {'role':'assistant','tool_calls':[cancel]},response('b','cancelled',[])]
        self.assertEqual(extract({'messages':msgs})[-1]['qualifying_change_indices'],[0])
        msgs=[{'role':'assistant','tool_calls':[change,cancel]},response('a','pending',[]),response('b','cancelled',[])]
        self.assertEqual(extract({'messages':msgs})[-1]['qualifying_change_indices'],[])

    def test_duplicate_result_is_not_chosen(self):
        c=call('a','cancel_pending_order');r=response('a','cancelled',[])
        row=extract({'messages':[{'role':'assistant','tool_calls':[c]},r,r]})[0]
        self.assertEqual(row['association'],'multiple_results');self.assertIsNone(row['order'])


if __name__=='__main__':unittest.main()
