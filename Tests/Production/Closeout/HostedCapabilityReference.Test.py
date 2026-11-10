"""Bounded controls for full initial SDK inventory; no runtime credit."""
import csv
import copy
import json
from pathlib import Path
import tempfile
import unittest
import hosted_capability_reference as reference


class HostedCapabilityReferenceTests(unittest.TestCase):
    def test_initial_sdk_population_is_complete_and_fields_are_original(self):
        self.assertEqual(len(reference.FIELDS),17)
        self.assertIn('remaining_stock_032',reference.CASES);self.assertEqual(len(reference.CASES),9)
        reference.sources()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sdk.csv';fields=['tick','object','class',*reference.FIELDS]
            row=dict(tick='0',object='HST',**{'class':'HST'},**{k:'1' for k in reference.FIELDS})
            with path.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerow(row)
                writer.writerow(dict(row,tick='1'))
            self.assertEqual(reference.initial_signatures(path,{'HST':'HST'},{'HST'}),{('HST',*(1.0 for _ in reference.FIELDS))})

    def test_missing_duplicate_or_nonfinite_original_sdk_population_is_rejected(self):
        for damage in ('missing','duplicate','nonfinite','header'):
            with self.subTest(damage=damage),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'sdk.csv';fields=['tick','object','class',*reference.FIELDS]
                row=dict(tick='0',object='HST',**{'class':'HST'},**{k:'1' for k in reference.FIELDS})
                if damage=='missing':row['object']='other'
                if damage=='nonfinite':row['size']='nan'
                if damage=='header':fields.remove('size');row.pop('size')
                with path.open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerow(row)
                    if damage=='duplicate':writer.writerow(row)
                with self.assertRaises(ValueError):reference.initial_signatures(path,{'HST':'HST'},{'HST'})


    def test_actual_parent_schema_keeps_two_runs_and_per_run_frame_contract(self):
        cases={c['id']:c for c in json.loads((reference.ROOT/'Tests/Production/RemainingStock/cases.json').read_text())['cases']}
        record=dict(status='captured',process_returncode=0,finalized_ticks=961)
        parent=dict(producer_commit=reference.ORIGINAL,protocol='remaining-stock-matched-clock-v2',host='repaired-original-windows',
                    status='captured-awaiting-independent-audit',diagnostic_only=False,failures={},cases_requested=list(cases),
                    configuration='Debug',math_profile='automatic',runtime_variant_unchanged=True,observer_sources_unchanged=True,
                    actual_original_simulation_data_unchanged=True,native_admission_qualified=False,phase6_complete=False,
                    cases={k:dict(runs=[copy.deepcopy(record),copy.deepcopy(record)]) for k in cases},
                    protocol_sha256_lf='1'*64,original_application_and_sdk_source='f725194209634f7fd5d1d44d426cfa9b5e303e37',
                    runtime_variant_manifest_sha256='2'*64)
        variant=dict(protocol=parent['protocol'],protocol_sha256_lf=parent['protocol_sha256_lf'],
                     original_application_and_sdk_source=parent['original_application_and_sdk_source'],producer_commit=reference.ORIGINAL,
                     runtime_variant_manifest_sha256=parent['runtime_variant_manifest_sha256'],frames=960,fixed_step=1/64,
                     capture_tick=800,diagnostic_only=False,cases_requested=list(cases))
        self.assertNotIn('repeats',parent);self.assertNotIn('frames',parent)
        reference.validate_parent(parent,'Debug-automatic',cases);reference.validate_variant(parent,record,variant)
        damaged=copy.deepcopy(parent);next(iter(damaged['cases'].values()))['runs'].pop()
        with self.assertRaises(ValueError):reference.validate_parent(damaged,'Debug-automatic',cases)
        for key,value in [('frames',60),('capture_tick',799),('fixed_step',.25)]:
            damaged=dict(variant);damaged[key]=value
            with self.assertRaises(ValueError):reference.validate_variant(parent,record,damaged)
        with self.assertRaises(ValueError):reference.validate_variant(parent,dict(record,finalized_ticks=960),variant)


    def test_mass_grouping_never_drops_full_exact_variants_or_grants_qualification(self):
        actual=set()
        for i in range(16):
            values=[1.0 for _ in reference.FIELDS];values[reference.FIELDS.index('size')]=float(i)
            actual.add(('family'+str(i%11),*values))
        selected=set(actual)
        for i,row in enumerate(sorted(actual)[:6]):
            values=list(row);values[reference.FIELDS.index('empty_mass')+1]=2.0;actual.add(tuple(values))
            if i==0:selected.add(tuple(values))
        profiles={p:dict(unique_signatures=sorted(actual),selected_case_signatures=sorted(selected)) for p in reference.PROFILES}
        result=reference.inventory_coverage(actual,selected,profiles,{'family'+str(i) for i in range(11)})
        self.assertEqual(result['structural_projection_signature_count'],16)
        self.assertEqual(result['full_17_field_comparison_fields'],list(reference.capabilities.FIELDS))
        self.assertEqual(len(result['full_17_field_variants_not_in_original_nine_cases']),5)
        self.assertTrue(result['full_17_field_additional_variant_audit_pending'])
        self.assertFalse(result['historical_inventory_field_list_recovered'])
        for damage in ('full_mass_variant','selected_variant','structural_variant','profile_variant'):
            a=set(actual);b=set(selected);p=copy.deepcopy(profiles)
            if damage=='full_mass_variant':a.remove(next(iter(actual-selected)))
            if damage=='selected_variant':b.remove(next(iter(selected)))
            if damage=='structural_variant':
                row=next(iter(actual-selected));a.remove(row);values=list(row);values[reference.FIELDS.index('size')+1]=200.0;a.add(tuple(values))
                p={k:dict(unique_signatures=sorted(a),selected_case_signatures=sorted(b)) for k in reference.PROFILES}
            if damage=='profile_variant':next(iter(p.values()))['unique_signatures'].pop()
            with self.subTest(damage=damage),self.assertRaises(ValueError):reference.inventory_coverage(a,b,p,{'family'+str(i) for i in range(11)})
