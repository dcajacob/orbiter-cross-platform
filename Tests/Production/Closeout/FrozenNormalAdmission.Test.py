from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import subprocess
import frozen_admission_api as api
import hosted_normal_admission as admission


class FrozenNormalAdmission(TestCase):
    def test_frozen_lock_cannot_be_rewritten_to_substitute_application_bytes(self):
        lock=api.candidate()
        modified=json.loads(api.LOCK.read_text())
        modified['identities']['application']['Debug-automatic']['exe_sha256']='0'*64
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'modified.json';path.write_text(json.dumps(modified))
            with patch.object(api,'LOCK',path),self.assertRaisesRegex(ValueError,'Exact frozen candidate identity'):
                api.candidate()
        self.assertEqual(len(lock['unit_inventory']),6)

    def test_new_capture_preserves_full_original_provider_setup_and_default_scope(self):
        old=admission.original_setup.prepared_body();new=admission.prepared_body()
        old_setup=old[old.index("        providers=ROOT"):old.index("        build=ROOT")]
        self.assertIn(old_setup,new)
        compile(new,'phase6-frozen-normal-admission-generated','exec')
        self.assertEqual(new.count('Tests/Production/StockScenarios/run.py'),1)
        self.assertEqual(new.count('Tests/Production/StockScenarios/verify.py'),1)
        self.assertNotIn('--case',new)
        self.assertNotIn('--diagnostic-case',new)
        self.assertNotIn('--inventory-only',new)
        self.assertIn('ASAN_OPTIONS=\'detect_leaks=1:fast_unwind_on_malloc=0\'',new)
        self.assertIn('LSAN_OPTIONS=\'\'',new)

    def test_complete_reference_requires_all_paths_and_original_root(self):
        with self.assertRaisesRegex(ValueError,'1125 original'):
            api.expected_paths({'evidence_sha256':{}})
        evidence={str(api.EXPECTED_ROOT/'out/joint-api-qualification'/str(i)):'a'*64 for i in range(1124)}
        evidence['/tmp/substitute.bin']='b'*64
        with self.assertRaisesRegex(ValueError,'outside original runner'):
            api.expected_paths({'evidence_sha256':evidence})

    def test_minimal_container_uses_prepared_plan_before_python(self):
        source=admission.HERE/'prepare_hosted_normal_admission.sh'
        self.assertEqual(subprocess.run(['bash','-n',str(source)],check=False).returncode,0)
        body=source.read_text()
        self.assertLess(body.index('bash "$source_dir/original-plan'),body.index('python3'))
        self.assertEqual(body.count('sha256sum --check'),2)
