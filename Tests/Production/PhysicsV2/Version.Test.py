import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PhysicsV2 import source
from PhysicsV2.transforms import TARGET,BASELINE,corrected_physics,versioned_builder,versioned_client,BUILDER,CLIENT


class PhysicsVersion(unittest.TestCase):
    def test_exact_patch_transport_requires_lf_on_windows(self):
        attributes=Path(__file__).with_name('.gitattributes').read_text()
        self.assertIn('correction.patch text eol=lf',attributes.splitlines())
        patch_bytes=Path(__file__).with_name('correction.patch').read_bytes()
        self.assertNotIn(b'\r',patch_bytes)
        self.assertEqual(source.digest(patch_bytes),json.loads(Path(__file__).with_name('version.json').read_text())['patch_sha256'])

    def test_applied_shared_source_is_exact_independently_validated_patch(self):
        old=source.normalized(source.git('show',BASELINE+':'+TARGET)).decode()
        self.assertEqual(corrected_physics(old),source.normalized((source.ROOT/TARGET).read_bytes()).decode())
        self.assertEqual(versioned_builder(source.normalized(source.git('show',BASELINE+':'+BUILDER)).decode()),source.normalized((source.ROOT/BUILDER).read_bytes()).decode())
        self.assertEqual(versioned_client(source.normalized(source.git('show',BASELINE+':'+CLIENT)).decode()),source.normalized((source.ROOT/CLIENT).read_bytes()).decode())

    def fixture(self,root):
        names=[*source.expected_sources(),*source.INPUTS]
        manifest=json.loads((source.ROOT/'Tests/Production/PhysicsV2/version.json').read_text());names+=list(manifest['original_guard_files_sha256_lf'])
        for n in set(names):
            p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((source.ROOT/n).read_bytes())

    def test_fourth_physics_change_cannot_be_hidden_by_rehashing_version_manifest(self):
        real=source.git
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            def git(*args,**kw):
                if kw.get('root')==root and args[0] in ('diff','ls-files'):return b''
                return real(*args,**kw)
            with patch.object(source,'git',side_effect=git):
                source.validate_current(root)
                p=root/TARGET;p.write_bytes(p.read_bytes()+b'\nint undeclared_physics_change = 1;\n')
                m=root/'Tests/Production/PhysicsV2/version.json';v=json.loads(m.read_text());v['corrected_source_sha256_lf']=source.digest(source.normalized(p.read_bytes()));m.write_text(json.dumps(v))
                with self.assertRaises(ValueError):source.validate_current(root)

    def test_unchanged_original_guard_cannot_be_modified_by_versioned_route(self):
        real=source.git
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            def git(*args,**kw):
                if kw.get('root')==root and args[0] in ('diff','ls-files'):return b''
                return real(*args,**kw)
            p=root/'Tests/Production/vessel_source.py';p.write_bytes(p.read_bytes()+b'\n# changed guard\n')
            with patch.object(source,'git',side_effect=git),self.assertRaises(ValueError):source.validate_current(root)

    def test_real_isolated_sparse_baseline_keeps_original_git_head_and_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();subprocess.run(['git','init','--quiet',str(root)],check=True)
            for n in ('Src/engine.cpp','Tests/Production/guard.py','.github/workflows/original.yml','.gitignore','Sound/excluded.bin'):
                p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('original '+n+'\n')
            subprocess.run(['git','-C',str(root),'add','.'],check=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=Control','-c','user.email=control@example.invalid','commit','--quiet','-m','Original source fixture'],check=True)
            commit=source.git('rev-parse','HEAD',root=root).decode().strip();view=Path(d)/'view'
            with patch.object(source,'BASELINE',commit),patch.object(source,'SCOPES',('Src','Tests','.github','.gitignore')):source.baseline_clone(view,root=root)
            for n in ('Src/engine.cpp','Tests/Production/guard.py','.github/workflows/original.yml','.gitignore'):self.assertEqual((view/n).read_bytes(),(root/n).read_bytes())
            self.assertFalse((view/'Sound/excluded.bin').exists());self.assertFalse(source.git('status','--porcelain',root=view).strip())

    def test_original_vessel_guard_still_rejects_the_intentional_new_physics(self):
        import vessel_source
        guard=source.ROOT/'Tests/Production/vessel_source.py';manifest=json.loads((source.ROOT/'Tests/Production/PhysicsV2/version.json').read_text())
        self.assertEqual(source.digest(source.normalized(guard.read_bytes())),manifest['original_guard_files_sha256_lf']['Tests/Production/vessel_source.py'])
        with self.assertRaisesRegex(ValueError,r'Src/Orbiter/SuperVessel\.cpp changed beyond declared services'):vessel_source.verify()
