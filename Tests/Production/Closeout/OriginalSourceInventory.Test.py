"""Fresh reloads retain the complete source guard and every original observation body."""
import ast
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contracts import ROOT
HERE=ROOT/'Tests/Production/RemainingStockPersistence'
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('fresh_original_inventory_collector',HERE/'capture_windows.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)


class OriginalInventoryTests(unittest.TestCase):
    def test_recursive_inventory_includes_actual_tracked_nested_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'Tests/Production/RemainingStockPersistence';(base/'LocalVM').mkdir(parents=True)
            (base/'capture_windows.py').write_text('observed top level\n');(base/'LocalVM/nested.py').write_text('observed nested source\n')
            subprocess.run(['git','init','-q',str(root)],check=True)
            subprocess.run(['git','-C',str(root),'add','.'],check=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=Inventory control','-c','user.email=control@example.invalid','commit','-qm','fixture'],check=True)
            producer=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
            (base/'LocalVM/untracked.py').write_text('not an immutable input\n')
            self.assertEqual(collector.tracked_persistence_sources(root,producer),{base/'capture_windows.py',base/'LocalVM/nested.py'})
            with self.assertRaises(ValueError):collector.tracked_persistence_sources(root,'short')
            (base/'LocalVM/nested.py').unlink()
            with self.assertRaises(ValueError):collector.tracked_persistence_sources(root,producer)

    def test_only_inventory_extends_the_original_capture_and_the_auditor_guard_is_unchanged(self):
        producer='f9bf6c7814965cd897f349f97890d9e005cbb66d'
        path='Tests/Production/RemainingStockPersistence/capture_windows.py'
        original=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+path]).decode()
        current=(ROOT/path).read_text()
        old='    paths=set(original.source_files())|{x for x in HERE.iterdir() if x.is_file()}\n'
        new=old.rstrip('\n')+'|tracked_persistence_sources(ROOT,producer)\n'
        self.assertEqual(current.count(new),1)
        def main(body):return ast.dump(next(n for n in ast.parse(body).body if isinstance(n,ast.FunctionDef) and n.name=='main'),include_attributes=False)
        self.assertEqual(main(current.replace(new,old)),main(original))
        guard='Tests/Production/RemainingStockPersistence/audit.py'
        self.assertEqual((ROOT/guard).read_bytes(),subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+guard]))


if __name__=='__main__':unittest.main()
