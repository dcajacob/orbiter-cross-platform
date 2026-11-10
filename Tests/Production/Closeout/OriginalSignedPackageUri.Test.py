"""Original APT URI encoding must match literal signed filenames without weakening path/hash guards."""
import unittest
import verify_published_original_pool as replay


class OriginalSignedPackageUriTests(unittest.TestCase):
    PREFIX='https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/'

    def test_actual_original_apt_encoded_plus_and_tilde_match_literal_signed_paths(self):
        for encoded,literal in [('pool/main/a/apparmor/libapparmor1_5.0.2-0ubuntu1%7e26.04.1_amd64.deb','pool/main/a/apparmor/libapparmor1_5.0.2-0ubuntu1~26.04.1_amd64.deb'),('pool/main/libx/libxml2/libxml2-16_2.15.2%2bdfsg-0.1ubuntu0.3_amd64.deb','pool/main/libx/libxml2/libxml2-16_2.15.2+dfsg-0.1ubuntu0.3_amd64.deb')]:
            self.assertEqual(replay.package_path(self.PREFIX+encoded),literal)
            self.assertEqual(replay.package_path(self.PREFIX+literal),literal)

    def test_plus_is_never_a_form_encoded_space_or_an_acceptance_hash_change(self):
        uri=self.PREFIX+'pool/main/a/a/a_1%2b2_amd64.deb';key=replay.package_path(uri);self.assertIn('+',key);self.assertNotIn(' ',key)
        row=[uri,'mirror','a_1+2_amd64.deb','22','a'*64]
        fields=dict(Filename=key,SHA256='a'*64,Size='22',Package='a',Version='1+2');found=set()
        replay.planned_package(fields,{key:row},{'a':'1+2'},found);self.assertEqual(found,{key})
        fields['SHA256']='b'*64
        with self.assertRaises(ValueError):replay.planned_package(fields,{key:row},{'a':'1+2'},set())

    def test_encoded_separators_traversal_nul_double_escape_or_other_archives_cannot_match(self):
        for relative in ('pool/a%2fb.deb','pool/%2e%2e/a.deb','pool/../a.deb','pool/a%00.deb','pool/a%252b.deb','pool/a%zz.deb','pool/a%','pool/a%5cb.deb'):
            with self.assertRaises(ValueError):replay.package_path(self.PREFIX+relative)
        for uri in ('https://archive.ubuntu.com/ubuntu/pool/a.deb',self.PREFIX.replace('20261109','20261110')+'pool/a.deb','http://snapshot.ubuntu.com/ubuntu/20261109T212432Z/pool/a.deb'):
            with self.assertRaises(ValueError):replay.package_path(uri)
