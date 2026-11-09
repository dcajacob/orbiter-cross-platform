"""The additional Mesa owner cleanup cannot change original detection or build settings."""
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/GraphicsDriverLifetime'))
import build_topology_driver as builder
import topology_cleanup as cleanup


class MesaTopologySourceTests(unittest.TestCase):
    def test_unknown_or_already_patched_cpu_source_cannot_receive_the_cleanup(self):
        for value in (b'',b'substituted CPU detection',cleanup.APPEND):
            with self.assertRaises(ValueError):cleanup.candidate(value)
        self.assertIn(b'free(util_cpu_caps.L3_affinity_mask);',cleanup.APPEND)
        self.assertEqual(cleanup.APPEND.count(b'free('),1)
        self.assertNotIn(b'__lsan',cleanup.APPEND)
        self.assertNotIn(b'atexit',cleanup.APPEND)

    def test_original_mesa_builder_remains_immutable_with_all_commands_and_flags(self):
        original=subprocess.check_output(['git','-C',str(ROOT),'show',builder.BASE+':Tests/Production/GraphicsDriverLifetime/build_driver.py']).decode()
        prepared=builder.prepared_body();ast.parse(prepared)
        extra1='''        from topology_cleanup import apply as apply_topology_cleanup
        report['topology_lifetime_variant']=apply_topology_cleanup(source)
        (output/'topology-source-variant.json').write_text(json.dumps(report['topology_lifetime_variant'],indent=2)+'\\n')
'''
        extra2='''        shutil.copy2(HERE/'topology_cleanup.py',notices)
        shutil.copy2(output/'topology-source-variant.json',notices)
'''
        self.assertEqual(prepared.count(extra1),1);self.assertEqual(prepared.count(extra2),1)
        self.assertEqual(prepared.replace(extra1,'').replace(extra2,''),original)
        saved=builder.BUILDER
        try:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'changed.py';path.write_text(original.replace("'-Dllvm=enabled'","'-Dllvm=disabled'"));builder.BUILDER=path
                with self.assertRaises(ValueError):builder.prepared_body()
        finally:builder.BUILDER=saved


if __name__=='__main__':unittest.main()
