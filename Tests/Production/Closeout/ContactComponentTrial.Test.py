from unittest import TestCase
from contracts import ROOT
import hosted_contact_component_trial as trial


class ContactComponentTrial(TestCase):
    def test_original_component_conserves_both_complete_production_method_bodies(self):
        generated,record=trial.source_variant('original-methods');body=(ROOT/'Src/Orbiter/SuperVessel.cpp').read_text()
        for i,signature in enumerate(('void SuperVessel::GetIntermediateMoments (','bool SuperVessel::AddSurfaceForces (')):
            actual=trial.method(generated,signature).replace('\n    contact_trial_call('+str(i)+');','',1)
            self.assertEqual(actual,trial.method(body,signature))
        self.assertFalse(record['production_source_modified'])
        self.assertFalse(record['qualification_granted'])

    def test_prototype_has_only_two_exact_changes_and_never_edits_production(self):
        before=(ROOT/'Src/Orbiter/SuperVessel.cpp').read_bytes()
        original,_=trial.source_variant('original-methods');fixed,record=trial.source_variant('collision-retry-prototype')
        self.assertEqual(fixed.replace(trial.AFTER,trial.BEFORE,1).replace(trial.FIXED_CALL,trial.CALL,1),original)
        self.assertEqual((ROOT/'Src/Orbiter/SuperVessel.cpp').read_bytes(),before)
        self.assertEqual(len(record['changes']),2)
        with self.assertRaises(ValueError):trial.source_variant('untracked-algorithm')

    def test_complete_original_provider_and_final_dependency_guards_remain(self):
        old=trial.original_setup.prepared_body();new=trial.prepared_body();compile(new,'original-full-provider-setup','exec')
        self.assertIn(old[old.index('        providers=ROOT'):old.index('        build=ROOT')],new)
        self.assertIn("require(verify_native_runtime(output/'native-runtime-dependencies.json')==report['native_host_dependencies']",new)
        self.assertIn('original_source_guards_unchanged=True',new)
