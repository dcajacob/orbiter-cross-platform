"""An official-pool transport may supply only exact SHA256-bound original snapshot blobs."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from contracts import ROOT


class OriginalPackagePoolPlanTests(unittest.TestCase):
    def check(self,body):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'signed-plan.txt';target=Path(temp)/'validated.tsv';source.write_text(body)
            done=subprocess.run(['bash',str(ROOT/'Tests/Production/Closeout/prepare_original_packages_from_official_pool.sh'),'--validate-plan-only',str(source),str(target)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            return done.returncode,target.read_text() if target.exists() else ''

    def line(self):return "'https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/pool/main/x/xfonts-base/xfonts-base_1.0.5%2bnmu1build1_all.deb' xfonts-base_1.0.5+nmu1build1_all.deb 123 SHA256:"+'a'*64+'\n'

    def test_same_exact_snapshot_path_filename_size_and_sha256_are_retained(self):
        code,text=self.check('Original apt plan header\n'+self.line());self.assertEqual(code,0);fields=text.strip().split('\t');self.assertEqual(fields[0],self.line().split("'")[1]);self.assertEqual(fields[1],fields[0].replace('snapshot.ubuntu.com/ubuntu/20261109T212432Z/','archive.ubuntu.com/ubuntu/'));self.assertEqual(fields[-2:],['123','a'*64])

    def test_wrong_host_snapshot_insecure_or_traversing_uris_cannot_be_prefetched(self):
        for old,new in (('https:','http:'),('snapshot.ubuntu.com','unowned.invalid'),('20261109T212432Z','20261110T000000Z'),('/pool/main/','/pool/../')):
            self.assertNotEqual(self.check(self.line().replace(old,new))[0],0)

    def test_missing_weak_or_malformed_hash_and_false_size_cannot_be_accepted(self):
        for value in (self.line().replace('SHA256:','MD5Sum:'),self.line().replace('a'*64,'a'*63),self.line().replace('123 SHA256:','0 SHA256:'),self.line().replace('a'*64,'g'*64)):
            self.assertNotEqual(self.check(value)[0],0)

    def test_destination_escape_duplicates_and_extra_shell_fields_are_rejected(self):
        for value in (self.line().replace(' xfonts-base_',' ../xfonts-base_'),self.line()+self.line(),self.line().rstrip()+' extra\n'):
            self.assertNotEqual(self.check(value)[0],0)

    def test_original_network_trust_snapshot_and_preflight_guards_remain_unchanged(self):
        original=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejections_network_v3.sh').read_text();actual=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_original_pool_network.sh').read_text();self.assertEqual(actual.replace('prepare_hosted_class_official_pool_preflight.sh|','prepare_hosted_class_rejections_sdk.sh|'),original)
        body=(ROOT/'Tests/Production/Closeout/prepare_original_packages_from_official_pool.sh').read_text();self.assertIn('apt-get update',body);self.assertIn('apt-get --no-download install -y --no-install-recommends "${pins[@]}"',body);self.assertIn('actual="$(sha256sum "$cache"',body);self.assertIn('cmp "$inventory" "$output/actual-system-packages.txt"',body);self.assertIn('sha256sum --check',body)
