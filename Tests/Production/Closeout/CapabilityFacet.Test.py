"""Negative controls for combining completed independent capability receipts without runtime credit."""
import copy
import json
import unittest
from contracts import ROOT,PROFILES
import final_hosted_class_capabilities as final


class CapabilityFacetTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT/'Tests/Production/Closeout/capability-facet-api.fixture.json').read_text())

    def test_final_input_roster_requires_every_completed_public_standard_job_and_exact_archive(self):
        original=self.fixture();pin=final.load(final.LOCK)['observers']['Debug-automatic'];before=copy.deepcopy(original)
        final.validate_api(original,pin);self.assertEqual(original,before)
        for mutate in (lambda r:r['run'].update(status='in_progress'),lambda r:r['run'].update(head_sha='e'*40),
                       lambda r:r['run']['repository'].update(private=True),lambda r:r['jobs'].pop(),
                       lambda r:r['jobs'][0].update(labels=['self-hosted']),lambda r:r['jobs'][0].update(conclusion='failure'),
                       lambda r:r['artifact'].update(digest='sha256:'+'0'*64),lambda r:r['artifact'].update(size_in_bytes=1),
                       lambda r:r['artifact'].update(expired=True)):
            value=copy.deepcopy(original);mutate(value)
            with self.assertRaises(ValueError):final.validate_api(value,pin)

    def scopes(self):
        # Synthetic join fixture only: no simulator or historical capture is created or relabelled.
        signatures=[['fixture',*(float(i) for i in range(17))] for n in range(22)]
        for index,row in enumerate(signatures):row[1]=float(index)
        inventory=dict(profiles={p:dict(unique_signatures=copy.deepcopy(signatures),selected_case_signatures=copy.deepcopy(signatures[:17])) for p in PROFILES},
                       full_17_field_variants_not_in_original_nine_cases=copy.deepcopy(signatures[17:]))
        observed={p:dict(profile=p,actual_processes=36,cases=final.reader.original.CASES,repeats=2,observer_lanes=['off','on'],
                        full_17_field_signatures=copy.deepcopy(signatures[:17]),non_mass_structural_combinations=16,
                        compiled_runtime_source=final.reader.original.COMPILED,new_simulator_processes=0) for p in PROFILES}
        sdk={p:dict(profile=p,repeats=2,new_simulator_processes=0,full_17_field_signatures=copy.deepcopy(signatures),
                    additional_full_variants_observed=copy.deepcopy(signatures[17:]),actual_initial_pairs=76,complete_scenes=38,
                    all_original_17_fields_exact=True,docking_geometry_budget=0,attachment_budgets_unchanged=True,
                    **{k:False for k in final.FLAGS}) for p in PROFILES}
        return observed,sdk,inventory

    def test_join_preserves_all_original_cells_and_exact_full_variant_superset_without_promoting_wider_acceptance(self):
        observed,sdk,inventory=self.scopes();before=copy.deepcopy((observed,sdk,inventory))
        result=final.combine(observed,sdk,inventory)
        self.assertEqual(result['original_observer_processes'],144);self.assertEqual(result['exact_initial_SDK_pairs'],304)
        self.assertEqual(result['new_simulator_processes'],0);self.assertEqual(len(result['exact_SDK_fields']),17)
        self.assertEqual((observed,sdk,inventory),before)

    def test_missing_profile_repeat_lane_variant_field_and_source_cannot_close_scope(self):
        for mutate in (lambda o,s,i:o.pop(PROFILES[0]),lambda o,s,i:s.pop(PROFILES[-1]),
                       lambda o,s,i:o[PROFILES[0]].update(repeats=1),lambda o,s,i:o[PROFILES[0]].update(observer_lanes=['on']),
                       lambda o,s,i:o[PROFILES[0]].update(actual_processes=35),
                       lambda o,s,i:o[PROFILES[0]].update(compiled_runtime_source='e'*40),
                       lambda o,s,i:s[PROFILES[0]]['full_17_field_signatures'].pop(),
                       lambda o,s,i:o[PROFILES[0]]['full_17_field_signatures'][0].pop(),
                       lambda o,s,i:s[PROFILES[0]].update(docking_geometry_budget=1e-8),
                       lambda o,s,i:s[PROFILES[0]].update(attachment_budgets_unchanged=False),
                       lambda o,s,i:s[PROFILES[0]].update(normal_admission_qualified=True),
                       lambda o,s,i:s[PROFILES[0]].update(new_simulator_processes=1)):
            observed,sdk,inventory=self.scopes();mutate(observed,sdk,inventory)
            with self.assertRaises(ValueError):final.combine(observed,sdk,inventory)

    def test_immutable_source_guard_rejects_paths_outside_the_original_test_source_tree(self):
        for name in ('../runtime.py','/tmp/override.py','Tests/../runtime.py','Source/Orbiter.cpp'):
            with self.assertRaises(ValueError):final.gitsha('e'*40,name)
