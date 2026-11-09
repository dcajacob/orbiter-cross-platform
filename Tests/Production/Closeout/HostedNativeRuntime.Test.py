"""Declared runtime repairs keep every old capture and package-provenance guard intact."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contracts import ROOT
import hosted_native_runtime_dependencies as runtime
import capture_hosted_native_writer_runtime as writer


class HostedNativeRuntimeTests(unittest.TestCase):
    def test_runtime_repair_requires_actual_binary_declarations_and_the_exact_existing_plugin_source(self):
        args=('Shared library: [libGLU.so.1]',b'original GLFW libdecor-0.so.0\x00',
            dict(status='built',baseline=False,sanitizers=True,source_lock_sha256='a'*64,plugin_sha256='b'*64),
            dict(package_version='0.2.5-1',automatic_refresh=False),'a'*64,'b'*64)
        self.assertEqual(runtime.contract(*args),['libglu1-mesa','libdecor-0-0=0.2.5-1'])
        for change in (lambda a:a.__setitem__(0,'unrelated SONAME'),lambda a:a.__setitem__(1,b'unrelated library'),
                       lambda a:a[2].update(baseline=True),lambda a:a[2].update(sanitizers=False),
                       lambda a:a[2].update(source_lock_sha256='c'*64),lambda a:a[2].update(plugin_sha256='d'*64),
                       lambda a:a[3].update(package_version='0.2.6-1'),lambda a:a[3].update(automatic_refresh=True)):
            changed=copy.deepcopy(list(args));change(changed)
            with self.assertRaises(ValueError):runtime.contract(*changed)

    def test_real_library_and_inventory_changes_cannot_reuse_an_earlier_dependency_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);libraries={};resolutions={};source='e'*40;inventory='original:amd64=1\nlibdecor-0-0:amd64=0.2.5-1\n'
            for n,soname in enumerate(runtime.SONAMES.values()):
                path=root/soname;path.write_bytes(('fixture-'+str(n)).encode())
                libraries[soname]=dict(path=str(path),resolved_path=str(path.resolve()),sha256=runtime.sha(path))
            for name in ('dragonfly','graphics','private-gtk'):
                path=root/(name+'.so');path.write_bytes((name+' original fixture').encode());resolutions[name]=dict(path=str(path),sha256=runtime.sha(path))
            report=dict(protocol='phase6-hosted-declared-native-runtime-dependencies-v1',status='installed-declared-native-runtime-dependencies-only',
                collector_source=source,compiled_runtime_source=runtime.RUNTIME,helper_sha256=runtime.sha(runtime.__file__),
                previous_packages_and_versions_unchanged=True,full_inventory_sha256=hashlib.sha256(inventory.encode()).hexdigest(),
                libraries=libraries,resolutions=resolutions,simulation_executed=False,phase6_complete=False,native_admission_qualified=False)
            receipt=root/'receipt.json';receipt.write_text(json.dumps(report))
            with patch.dict(os.environ,GITHUB_SHA=source),patch.object(runtime,'inventory',return_value=inventory):
                self.assertEqual(runtime.verify(receipt),report)
                for mutate in (lambda r:r['libraries'].pop(next(iter(libraries))),lambda r:r.update(collector_source='f'*40),
                               lambda r:r.update(full_inventory_sha256='f'*64),lambda r:r.update(native_admission_qualified=True)):
                    changed=copy.deepcopy(report);mutate(changed);receipt.write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):runtime.verify(receipt)
                receipt.write_text(json.dumps(report));path=Path(next(iter(libraries.values()))['path']);path.write_bytes(b'changed actual library')
                with self.assertRaises(ValueError):runtime.verify(receipt)
            original={'protected:amd64':'1','compositor-added:amd64':'2'}
            self.assertEqual(runtime.original_packages_unchanged(original,dict(original,**{'new:amd64':'3'})),{'new:amd64':'3'})
            with self.assertRaises(ValueError):runtime.original_packages_unchanged(original,{'protected:amd64':'1','compositor-added:amd64':'3'})

    def test_the_original_complete_capture_and_every_simulation_statement_are_unchanged(self):
        old=writer.mesa_writer.prepared_body();new=writer.prepared_body();ast.parse(new)
        changes=[("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-stock-writer-Mesa-v2'"),
            ("        from hosted_native_runtime_dependencies import install as install_native_runtime,verify as verify_native_runtime\n        report['native_host_dependencies']=install_native_runtime(providers,output,a.profile,run,package_inventory,mesa);save()\n",''),
            ("        require(verify_native_runtime(output/'native-runtime-dependencies.json')==report['native_host_dependencies'],'Actual native runtime dependency proof changed')\n",'')]
        for before,after in changes:self.assertEqual(new.count(before),1);new=new.replace(before,after,1)
        self.assertEqual(new,old)
        for name in ('Tests/Production/RemainingStockPersistence/capture_native.py','Tests/Production/RemainingVessels/native.py'):
            self.assertEqual((ROOT/name).read_bytes(),subprocess.check_output(['git','-C',str(ROOT),'show',writer.SOURCE+':'+name]))
        actual=(ROOT/'Tests/Production/Closeout/prepare_hosted_native_writer_runtime.sh').read_text()
        self.assertEqual(actual.replace('capture_hosted_native_writer_runtime.py','capture_hosted_native_writer_mesa.py',1),
            (ROOT/'Tests/Production/Closeout/prepare_hosted_native_writer_mesa.sh').read_text())

    def test_each_replacement_lane_is_one_exact_closed_failed_profile(self):
        text=(ROOT/'.github/workflows/phase6-native-runtime-stock-writers.yml').read_text()
        for config in ('debug','release'):
            for mode in ('automatic','sse2'):self.assertIn('qualification/native-runtime-writer-'+config+'-'+mode+'-v1',text)
        self.assertIn("profile!==allowed[branch]",text);self.assertIn("found[0].status!=='completed'",text)
        self.assertIn("found[0].conclusion!=='failure'",text);self.assertNotIn('math_profile: [automatic, sse2]',text)
        self.assertIn("endsWith(github.ref_name, '-automatic-v1')",text);self.assertIn("contains(github.ref_name, '-debug-')",text)
        self.assertIn('const run_id=profile.startsWith(\'Debug-\')?42545909682:42549074137;',text)
        self.assertIn('runs-on: ubuntu-24.04',text);self.assertIn('cancel-in-progress: false',text)
        self.assertIn('timeout-minutes: 330',text);self.assertIn('prepare_hosted_native_writer_runtime.sh',text)
        self.assertNotIn("--case",text);self.assertNotIn('detect_leaks=0',text)


if __name__=='__main__':unittest.main()
