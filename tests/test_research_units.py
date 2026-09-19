import copy
import json
import unittest
from autolab.research_units import VIEWS, account, build_example, score


class ResearchUnitsTest(unittest.TestCase):
    def test_designs_and_repeated_information(self):
        values=[[j/100,(j-10)/200] for j in range(24)]
        expected=[(4,4,4,0,'paired'),(4,4,4,16,'paired'),
                  (12,12,12,0,'paired'),(12,12,0,0,'disjoint'),(12,12,4,0,'partial')]
        cases=[]
        for view,want in zip(VIEWS,expected):
            item,origins=build_example('dev00',values,view)
            self.assertEqual(tuple(account(item).values()),want)
            self.assertEqual(len(origins),want[0]+want[1]);cases.append(item)
        key=lambda r:(r['evaluation_id'],r['arm'],r['resample_id'],r['squared_error'])
        self.assertEqual({key(r) for r in cases[0]['reports']},{key(r) for r in cases[1]['reports']})
        self.assertEqual(len({r['resample_id'] for r in cases[0]['reports']}),4)
        self.assertEqual(len({r['evaluation_id'] for r in cases[0]['reports']}),8)

    def test_equal_values_not_duplicate_and_conflicts_rejected(self):
        item,_=build_example('dev00',[[0.,0.]]*24,'larger_paired')
        self.assertEqual(account(item)['unique_a'],12)
        bad=copy.deepcopy(item);row=copy.deepcopy(bad['reports'][0]);row['report_id']='new';row['squared_error']=1
        bad['reports'].append(row)
        with self.assertRaises(ValueError):account(bad)
        row['evaluation_id']='new'
        with self.assertRaises(ValueError):account(bad)
        bad=copy.deepcopy(item);bad['reports'].append(bad['reports'][0])
        with self.assertRaises(ValueError):account(bad)

    def test_strict_scoring(self):
        expected=dict(unique_a=4,unique_b=4,matched_pairs=4,redundant_reports=16,design='paired')
        self.assertTrue(score(json.dumps(expected),expected)['correct'])
        for bad in [None,'[]','```json\n'+json.dumps(expected)+'\n```',json.dumps(dict(expected,unique_a=True)),
                    json.dumps(dict(expected,extra=0)),json.dumps(expected)[:-1]+',"unique_a":4}']:
            self.assertFalse(score(bad,expected)['valid'])
        x=score(json.dumps(dict(expected,unique_a=12)),expected)
        self.assertTrue(x['valid']);self.assertFalse(x['correct']);self.assertTrue(x['fields']['unique_b'])

    def test_worker_uses_one_call_and_retains_failure(self):
        from autolab.research_unit_pilot import run_one, SETTINGS
        from autolab.tool_agent import ModelReply
        item,_=build_example('dev00',[[0.,0.]]*24,'small_paired')
        class Fake:
            def __init__(self,fail=False):self.calls=[];self.fail=fail
            def generate_tools(self,messages,tools,limit):
                self.calls.append((messages,tools,limit))
                if self.fail:raise ValueError('fixture failure')
                return ModelReply('{}',300,2,0.01)
        for fail in (False,True):
            model=Fake(fail);result=run_one(model,item)
            self.assertEqual(len(model.calls),1)
            self.assertEqual(model.calls[0][1:],([],384))
            self.assertEqual(json.loads(model.calls[0][0][1]['content']),item)
            self.assertEqual(result['status'],'generation_error' if fail else 'returned')
            self.assertFalse(result['scored'])
            self.assertEqual('reply' in result,not fail)


if __name__=='__main__':unittest.main()
