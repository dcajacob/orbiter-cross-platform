from unittest import TestCase
from contracts import ROOT,load
import hosted_frozen_cockpit_component as core


class FrozenCockpitComponent(TestCase):
    def test_conserved_complete_providers_and_exact_original_fixtures(self):
        old=core.original_setup.prepared_body();new=core.prepared_body()
        self.assertIn(old[old.index("        providers=ROOT"):old.index("        build=ROOT")],new)
        compile(new,'original-frozen-cockpit-capture','exec')
        for path in core.FIXTURES:self.assertIn(path,new)
        self.assertNotIn('--case',new)
        self.assertIn("ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0'",new)
        self.assertIn("LSAN_OPTIONS=''",new)

    def test_original_fixture_matrix_and_image_tolerances_remain_complete(self):
        for name,expected in [('Cockpit',9),('CockpitUI',3)]:
            spec=load(ROOT/'Tests/Production'/name/'cases.json')
            self.assertEqual(len({c['id'] for c in spec['cases']}),expected)
            self.assertEqual(spec['image_ssim_minimum'],.98)
            self.assertEqual(spec['frames'],60)
