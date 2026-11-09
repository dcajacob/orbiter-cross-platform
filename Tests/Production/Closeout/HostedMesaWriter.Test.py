"""Separate Mesa restoration cannot substitute failed controls or change the native capture."""
import ast
import copy
from pathlib import Path
import subprocess
import unittest
from contracts import ROOT
import restore_hosted_mesa_topology as mesa
import capture_hosted_native_writer_mesa as writer


class HostedMesaWriterTests(unittest.TestCase):
    def test_exact_successful_mesa_controls_are_required(self):
        record=dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=mesa.RUN,head_sha=mesa.SOURCE,head_branch='qualification/mesa-topology-repair',path='.github/workflows/phase6-mesa-topology.yml',run_attempt=1,status='completed',conclusion='success'),
            artifact=dict(id=mesa.ARTIFACT,name='mesa-topology-owner-repair',expired=False,size_in_bytes=mesa.SIZE,digest='sha256:'+mesa.DIGEST,workflow_run=dict(id=mesa.RUN,head_sha=mesa.SOURCE)),
            jobs=[dict(id=128923839407,run_id=mesa.RUN,head_sha=mesa.SOURCE,status='completed',conclusion='success',labels=['ubuntu-24.04'],steps=[dict(name=n,status='completed',conclusion='success') for n in mesa.STEPS])])
        mesa.validate_api(record)
        for change in (lambda r:r['run'].update(head_sha='f'*40),lambda r:r['artifact'].update(digest='sha256:'+'0'*64),
                       lambda r:r['jobs'][0].update(conclusion='failure'),lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped')):
            changed=copy.deepcopy(record);change(changed)
            with self.assertRaises(ValueError):mesa.validate_api(changed)

    def test_safe_complete_archive_reader_is_byte_conserved_in_its_separate_namespace(self):
        old=(ROOT/'Tests/Production/Closeout/restore_hosted_native_providers.py').read_text();new=Path(mesa.__file__).read_text()
        def body(value):return ast.dump(next(n for n in ast.parse(value).body if isinstance(n,ast.FunctionDef) and n.name=='restore_tree'),include_attributes=False)
        self.assertEqual(body(old),body(new));self.assertEqual(mesa.PREFIX,'out/hosted-mesa-topology')

    def test_original_full_capture_argv_and_observation_sources_remain_unchanged(self):
        original=writer.ORIGINAL.read_bytes();prepared=writer.prepared_body();ast.parse(prepared)
        def argv(value):
            main=next(n for n in ast.parse(value).body if isinstance(n,ast.FunctionDef) and n.name=='main')
            return ast.dump(next(n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='argv' for t in n.targets)),include_attributes=False)
        self.assertEqual(argv(original),argv(prepared))
        self.assertIn("compiled_mesa_source='"+mesa.SOURCE+"'",prepared)
        self.assertIn("base_compiled_provider_source='"+mesa.BASE_SOURCE+"'",prepared)
        name='Tests/Production/RemainingStockPersistence/capture_native.py'
        self.assertEqual((ROOT/name).read_bytes(),subprocess.check_output(['git','-C',str(ROOT),'show',writer.BASE+':'+name]))


if __name__=='__main__':unittest.main()
