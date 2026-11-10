"""Negative controls for complete full SDK coverage and original exact field/port comparisons."""
import copy
import csv
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT,load
import hosted_full_sdk_audit as hosted


class HostedFullSDKTests(unittest.TestCase):
    def test_all_original_capability_and_prior_full_raw_source_guards_are_conserved(self):
        self.assertEqual(len(hosted.original_sources()),12)
        self.assertEqual(len(hosted.reference.FIELDS),17)

    def test_dropped_mass_variant_case_repeat_or_pending_original_controls_cannot_hide_coverage(self):
        signatures=set()
        for i in range(22):
            values=[1.0 for _ in hosted.reference.FIELDS];values[hosted.reference.FIELDS.index('empty_mass')]=float(i)
            signatures.add(('HST',*values))
        cases={c['id']:[dict(repeat=r,all_17_fields_exact=True,original_port_budgets_unchanged=True,actual_capabilities={'fixture':1}) for r in (1,2)]
               for c in load(ROOT/'Tests/Production/RemainingStock/cases.json')['cases']}
        inventory=dict(profiles={'Debug-automatic':dict(unique_signatures=sorted(signatures))},
                       full_17_field_variants_not_in_original_nine_cases=sorted(signatures)[:5],
                       proposed_native_cases=hosted.reference.CASES,fields=list(hosted.reference.FIELDS))
        result=hosted.coverage('Debug-automatic',cases,signatures,signatures,inventory)
        self.assertTrue(result['original_nine_scene_144_process_controls_pending']);self.assertFalse(result['complete_class_eligibility_qualified'])
        self.assertEqual(result['actual_initial_pairs'],76);self.assertEqual(result['new_simulator_processes'],0)
        for damage in ('mass','case','repeat','comparison','port'):
            a=set(signatures);b=copy.deepcopy(cases)
            if damage=='mass':a.pop()
            if damage=='case':b.pop(next(iter(b)))
            if damage=='repeat':next(iter(b.values())).pop()
            if damage=='comparison':next(iter(b.values()))[0]['all_17_fields_exact']=False
            if damage=='port':next(iter(b.values()))[0]['original_port_budgets_unchanged']=False
            with self.subTest(damage=damage),self.assertRaises(ValueError):hosted.coverage('Debug-automatic',b,a,signatures,inventory)

    def test_original_empty_mass_and_docking_remain_exact_and_attachment_budgets_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);left=base/'native';right=base/'original';left.mkdir();right.mkdir()
            fields=['tick','object','class',*hosted.reference.FIELDS]
            sdk=dict(tick='0',object='HST',**{'class':'HST'},**{k:'1' for k in hosted.reference.FIELDS})
            dock=dict(tick='0',object='HST',index='0',docked='none',**{k:'0' for k in ('x','y','z','dx','dy','dz','rx','ry','rz')})
            attachment=dict(tick='0',object='HST',to_parent='0',index='0',attached='none',**{k:'0' for k in ('x','y','z','dx','dy','dz','rx','ry','rz')})
            def write(folder,name,row,keys=None):
                with (folder/name).open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=keys or list(row));writer.writeheader();writer.writerow(row)
            for folder in (left,right):
                write(folder,'stock-vessel-state.csv',sdk,fields);write(folder,'stock-vessel-docks.csv',dock);write(folder,'stock-vessel-attachments.csv',attachment)
            case=dict(declared_vessels={'HST':'HST'});budgets=load(ROOT/'Tests/Production/RemainingStock/cases.json')['budgets']
            hosted.compare_initial(left,right,case,budgets,{'HST'})
            write(left,'stock-vessel-state.csv',dict(sdk,empty_mass='1.000000001'),fields)
            with self.assertRaisesRegex(ValueError,'empty_mass'):hosted.compare_initial(left,right,case,budgets,{'HST'})
            write(left,'stock-vessel-state.csv',sdk,fields);write(left,'stock-vessel-docks.csv',dict(dock,x='0.000000000001'))
            with self.assertRaisesRegex(ValueError,'port geometry'):hosted.compare_initial(left,right,case,budgets,{'HST'})
            write(left,'stock-vessel-docks.csv',dock)
            write(left,'stock-vessel-attachments.csv',dict(attachment,x=str(budgets['position_m']/2)))
            hosted.compare_initial(left,right,case,budgets,{'HST'})
            write(left,'stock-vessel-attachments.csv',dict(attachment,x=str(budgets['position_m']*2)))
            with self.assertRaisesRegex(ValueError,'port geometry'):hosted.compare_initial(left,right,case,budgets,{'HST'})
