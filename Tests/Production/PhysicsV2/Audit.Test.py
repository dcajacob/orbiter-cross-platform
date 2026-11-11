import copy,csv,sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import audit_native
from audit_contact_component_trial import HEADER


class PublishedFailureDisposition(unittest.TestCase):
    def fixture(self,root):
        folder=root/'007';folder.mkdir();rows=[]
        for tick in range(61):
            row={n:'0' for n in HEADER};row.update(tick=str(tick),frame=str(tick),seconds=str(tick*.25),object='Ship',**{'class':'ShuttlePB'},dock='',focus='Ship',attached='');rows.append(row)
        with (folder/'flight-state.csv').open('w') as stream:
            writer=csv.DictWriter(stream,fieldnames=HEADER);writer.writeheader();writer.writerows(rows)
        report=dict(cases={'original.scn':dict(output='007')})
        collection=dict(status='failed-or-incomplete-unqualified',error="could not convert string to float: ''",commands=[dict(label=n,actual_returncode=0) for n in ('normal-host-all-157-original-stock-scenarios','unchanged-independent-full-stock-auditor')])
        return collection,report,rows

    def test_exact_old_type_error_can_be_preserved_as_a_separate_disposition(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);collection,report,rows=self.fixture(root);before=copy.deepcopy(collection)
            result=audit_native.completed_collection(collection,'failure',{},root,report,{'original.scn':'007'})
            self.assertEqual(collection,before);self.assertEqual(result['original_status'],'failed-or-incomplete-unqualified');self.assertTrue(result['original_failed_statuses_unchanged'])

    def test_failed_original_collector_can_never_become_bookkeeping_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);collection,report,_=self.fixture(root);collection['commands'][0]['actual_returncode']=1
            with self.assertRaises(ValueError):audit_native.completed_collection(collection,'failure',{},root,report,{'original.scn':'007'})

    def test_nonfinite_numeric_state_cannot_be_hidden_by_a_text_field_error(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);collection,report,rows=self.fixture(root);rows[0]['rx']='nan'
            with (root/'007/flight-state.csv').open('w') as stream:
                writer=csv.DictWriter(stream,fieldnames=HEADER);writer.writeheader();writer.writerows(rows)
            with self.assertRaises(ValueError):audit_native.completed_collection(collection,'failure',{},root,report,{'original.scn':'007'})

    def test_any_other_original_failure_stays_unqualified(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);collection,report,_=self.fixture(root);collection['error']='Original collector timed out'
            with self.assertRaises(ValueError):audit_native.completed_collection(collection,'failure',{},root,report,{'original.scn':'007'})
