from unittest import TestCase
from contracts import ROOT,load
import hosted_frozen_cockpit_component as core


class FrozenCockpitComponent(TestCase):
    def test_conserved_complete_providers_and_exact_original_fixtures(self):
        old=core.original_setup.prepared_body();new=core.prepared_body()
        self.assertIn(old[old.index("        providers=ROOT"):old.index("        build=ROOT")],new.replace(core.X11_BEFORE_RUNTIME,"",1))
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

    def test_x11_is_installed_after_original_inventory_and_before_final_inventory_seal(self):
        body=core.prepared_body()
        self.assertEqual(body.count(core.X11_BEFORE_RUNTIME),1)
        original=body.index("require(package_inventory(actual)==inventory,")
        x11=body.index(core.X11_BEFORE_RUNTIME)
        seal=body.index("report['native_host_dependencies']=install_native_runtime(")
        fixtures=body.index("for key,file,extra in [")
        final=body.index("require(verify_native_runtime(output/'native-runtime-dependencies.json')==report['native_host_dependencies']")
        self.assertLess(original,x11)
        self.assertLess(x11,seal)
        self.assertLess(seal,fixtures)
        self.assertLess(fixtures,final)
        self.assertEqual(body.count('install_x11(output,run)'),1)
        self.assertIn("x11=load(output/'x11.json');require(x11==report['x11']",body)
        self.assertIn('verify_x11(x11)',body[fixtures:final])
        old=core.original_setup.prepared_body()
        guard=old[old.index("        require(verify_native_runtime(output/"):old.index("        report.update(status='captured-and-independently-audited-native-writers-only'")]
        self.assertIn(guard,body)
