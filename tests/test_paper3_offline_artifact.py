"""An offline evidence verifier must reject corrupt and incomplete packages."""
import importlib.util
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

spec=importlib.util.spec_from_file_location('paper3_verifier',Path(__file__).resolve().parents[1]/'scripts/verify_paper3_offline_artifact.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class IntegrityTests(unittest.TestCase):
    def package(self,path,*,member=b'unchanged',missing=False,extra=None,alias=None):
        manifest={'format':'paper3-offline-v1','files':{'data.json':{'bytes':9,'sha256':module.sha(b'unchanged')}},'original_path_aliases':alias or {}}
        with ZipFile(path,'w') as z:
            z.writestr('artifact_manifest.json',json.dumps(manifest))
            if not missing:z.writestr('data.json',member)
            if extra:z.writestr(extra,b'payload')

    def test_changed_record_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'artifact.zip';self.package(p,member=b'tampered!')
            with self.assertRaisesRegex(ValueError,'Member mismatch'):module.Artifact(p)

    def test_omitted_record_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'artifact.zip';self.package(p,missing=True)
            with self.assertRaisesRegex(ValueError,'Incomplete or extra'):module.Artifact(p)

    def test_parent_path_rejected_without_extraction(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'artifact.zip';self.package(p,extra='../outside.txt')
            with self.assertRaisesRegex(ValueError,'Unsafe ZIP'):module.Artifact(p)
            self.assertFalse((Path(d).parent/'outside.txt').exists())

    def test_absolute_path_is_only_a_declared_alias(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'artifact.zip';self.package(p,alias={'C:\\original\\data.json':'data.json'})
            a=module.Artifact(p)
            try:
                self.assertEqual(a.read('C:\\original\\data.json'),b'unchanged')
                with self.assertRaisesRegex(ValueError,'Unregistered member'):a.read('C:\\original\\unlisted.json')
            finally:a.zip.close()


class RetailSemanticTests(unittest.TestCase):
    def fixture(self):
        def payment(kind, method):
            return dict(transaction_type=kind,payment_method_id=method,amount=10)
        methods={'a':dict(source='gift_card',balance=4),'b':dict(source='credit_card')}
        order=dict(status='pending',user_id='u',payment_history=[payment('payment','a')])
        source=dict(users={'u':dict(payment_methods=methods)},orders={'o':order})
        selection=dict(total_orders=1,selected=[dict(order_id='o',alternatives=['b'])],excluded=[])
        before=dict(order=deepcopy(order),payment_methods=deepcopy(methods))
        first=order['payment_history']+[payment('payment','b'),payment('refund','a')]
        final=first+[payment('refund','a'),payment('refund','b'),payment('refund','a')]
        def step(history,status,balance,net,tool,args,contract):
            current=deepcopy(order);current.update(payment_history=history,status=status)
            if status=='cancelled':current['cancel_reason']='no longer needed'
            instruments=deepcopy(methods);instruments['a']['balance']=balance
            observation=dict(status=status,signed_net_by_method=net,signed_net_total=str(sum(map(int,net.values()))),
                             ledger_entries=len(history),gift_balances={'a':str(balance)},cancelled=status=='cancelled',
                             per_method_net_zero=all(int(v)==0 for v in net.values()),
                             expected_cancelled_gift_balances_met=balance==14,cancellation_contract_met=contract)
            return dict(tool=tool,arguments=args,result=deepcopy(current),error=None,
                        state=dict(order=current,payment_methods=instruments),measurement=observation)
        cancel_args=dict(order_id='o',reason='no longer needed')
        base=dict(order_id='o',user_id='u',old_payment_method='a',before=before,expected_cancelled_gift_balances={'a':'14'})
        direct=dict(deepcopy(base),new_payment_method=None,kind='cancel_only',steps=[step(
            [payment('payment','a'),payment('refund','a')],'cancelled',14,{'a':'0'},'cancel_pending_order',cancel_args,True)])
        composed=dict(deepcopy(base),new_payment_method='b',kind='change_then_cancel',steps=[
            step(first,'pending',14,{'a':'0','b':'10'},'modify_pending_order_payment',dict(order_id='o',payment_method_id='b'),False),
            step(final,'cancelled',34,{'a':'-20','b':'0'},'cancel_pending_order',cancel_args,False)])
        return [direct,composed],source,selection

    def test_correct_status_does_not_override_unbalanced_ledger(self):
        rows,source,selection=self.fixture()
        report=module.retail_records(rows,source,selection)
        self.assertEqual(report['counts']['cancel_only_contract_met'],1)
        self.assertEqual(report['counts']['change_then_cancel_contract_met'],0)
        rows[1]['steps'][-1]['measurement']['cancellation_contract_met']=True
        with self.assertRaisesRegex(ValueError,'reported contract'):
            module.retail_records(rows,source,selection)

    def test_missing_alternative_and_altered_balance_rejected(self):
        rows,source,selection=self.fixture()
        with self.assertRaisesRegex(ValueError,'path grid'):
            module.retail_records(rows[:1],source,selection)
        rows[1]['steps'][-1]['state']['payment_methods']['a']['balance']=14
        with self.assertRaisesRegex(ValueError,'instrument state'):
            module.retail_records(rows,source,selection)


if __name__=='__main__':unittest.main()
