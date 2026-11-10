"""The actual host compiler bridge cannot alter original fixture commands or execute arbitrary requests."""
import copy
from pathlib import Path
import tempfile
import unittest
import rejection_fixture_compiler_bridge as bridge


class FixtureCompilerBridgeTests(unittest.TestCase):
    def test_every_original_argument_source_variant_sanitizer_and_output_are_exact(self):
        root=Path('/actual-original-workspace')
        for profile in bridge.PROFILES:
            for index in range(7):
                argv=bridge.expected_argv(profile,index,root);self.assertEqual(argv[0],'/usr/bin/c++');self.assertIn('-std=c++17',argv);self.assertIn('-fsanitize=address,undefined',argv);self.assertIn('-DPHASE6_REJECTED_METADATA='+str(index),argv);self.assertEqual(argv[-1],str(root/'out/native-class-rejections'/profile/'fixtures'/('metadata-'+str(index)+'.so')))
                self.assertNotIn('-D__VERSION__',argv);self.assertNotIn('-D__GLIBCXX__',argv)
                self.assertEqual(bridge.validate_request(dict(profile=profile,index=index,argv=argv),profile,set(range(index)),root),index)

    def test_changed_source_language_flags_profile_output_and_additional_arguments_are_rejected(self):
        profile='Debug-sse2';request=dict(profile=profile,index=0,argv=bridge.expected_argv(profile,0))
        for change in (lambda r:r['argv'].append('--version'),lambda r:r['argv'].__setitem__(1,'-std=c++20'),lambda r:r['argv'].__setitem__(-1,'/tmp/unowned.so'),lambda r:r.update(profile='Release-sse2'),lambda r:r.update(index=True),lambda r:r['argv'].__setitem__(-3,'/tmp/changed.cpp')):
            value=copy.deepcopy(request);change(value)
            with self.assertRaises(ValueError):bridge.validate_request(value,profile,set())

    def test_duplicates_skipped_variants_and_invented_fields_cannot_execute(self):
        profile='Debug-automatic';request=dict(profile=profile,index=0,argv=bridge.expected_argv(profile,0))
        with self.assertRaises(ValueError):bridge.validate_request(request,profile,{0})
        request.update(index=1,argv=bridge.expected_argv(profile,1))
        with self.assertRaises(ValueError):bridge.validate_request(request,profile,set())
        request['command']='arbitrary'
        with self.assertRaises(ValueError):bridge.validate_request(request,profile,{0})

    def test_socket_path_is_relative_to_same_root_without_exceeding_Unix_path_limit(self):
        for profile in bridge.PROFILES:
            relative=str((bridge.ROOT/'out/rejection-fixture-compiler'/profile/'bridge.sock').relative_to(bridge.ROOT));self.assertLess(len(relative.encode()),104)
