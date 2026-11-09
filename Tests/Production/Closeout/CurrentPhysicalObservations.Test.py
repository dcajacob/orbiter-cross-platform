"""Small composition fixtures only; no simulation or runtime qualification credit."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from contracts import ROOT

spec=importlib.util.spec_from_file_location('current_physical_observation_controls',
    ROOT/'Tests/Production/CurrentWindows/Hosted/physical_observations.py')
physical=importlib.util.module_from_spec(spec);spec.loader.exec_module(physical)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sha_lf(path):return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


class CurrentPhysicalObservationTests(unittest.TestCase):
    def test_recomputed_fields_cannot_be_removed_from_or_added_to_recorded_observations(self):
        actual=dict(actual_math='sse2',clock_observation={'ticks':960},renderer={'client_width':1280})
        record=dict(actual,**{name:None for name in physical.EXTRAS})
        physical.recorded_observation(actual,record)
        for field in record:
            modified=copy.deepcopy(record);modified.pop(field)
            with self.assertRaises(ValueError):physical.recorded_observation(actual,modified)
        modified=copy.deepcopy(record);modified['clock_observation']['ticks']=959
        with self.assertRaises(ValueError):physical.recorded_observation(actual,modified)
        with self.assertRaises(ValueError):physical.recorded_observation(actual,dict(record,unrecorded_claim=True))

    def test_class_witnesses_must_equal_independently_retained_sdk_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);runtime=root/'sdk';target='Config/Vessels/Test.cfg'
            path=runtime/target;path.parent.mkdir(parents=True);path.write_bytes(b'MODULE = Test\r\n')
            checksum=sha(path);invocation=dict(input_sha256={target:checksum},preserved_inputs_sha256={target:checksum})
            folder=root/'capture';folder.mkdir();manifest=folder/'invocation.json';manifest.write_text(json.dumps(invocation))
            called=[];reader=SimpleNamespace(sha=sha,sha_lf=sha_lf,
                windows=SimpleNamespace(shared=SimpleNamespace(inspect_inputs=lambda *args:called.append(args))))
            config=dict(classes={'Test':dict(target=target,sha256_lf=sha_lf(path))})
            case=dict(declared_vessels={'ship':'Test'})
            inputs=dict(runtime_local=str(runtime),runtime_files_sha256={target:checksum})
            self.assertEqual(physical.class_inputs(folder,case,config,inputs,reader),1)
            self.assertEqual(called[0],(folder,case,config))
            invocation['input_sha256'][target]='a'*64;manifest.write_text(json.dumps(invocation))
            with self.assertRaises(ValueError):physical.class_inputs(folder,case,config,inputs,reader)
            manifest.write_text(json.dumps(dict(input_sha256={target:checksum},preserved_inputs_sha256={target:checksum})))
            path.write_bytes(b'MODULE = Different\r\n')
            with self.assertRaises(ValueError):physical.class_inputs(folder,case,config,inputs,reader)

    def paired_fixture(self,root):
        ids=['case%03d'%i for i in range(38)];case={'id':ids[0]};parent=root/'original';parent.mkdir()
        report=dict(producer_commit=physical.ORIGINAL,configuration='Debug',math_profile='automatic',
            protocol='remaining-stock-matched-clock-v2',status='captured-awaiting-independent-audit',
            diagnostic_only=False,cases_requested=ids,cases={identity:{'runs':[{},{}]} for identity in ids},failures=[])
        manifest=parent/'capture.json';manifest.write_text(json.dumps(report))
        path=parent/(ids[0]+'-1')/physical.CURRENT;path.parent.mkdir(parents=True);path.write_bytes(b'unchanged original fixture save\r\n')
        members={'remaining-stock-repaired/capture.json':sha(manifest),
            'remaining-stock-repaired/'+ids[0]+'-1/'+physical.CURRENT:sha(path)}
        cfg=dict(configuration='Debug',math_profile='automatic',workspace='D:/a/project/project',
            capture_scope={'cases':ids},windows_save_inputs=[])
        for identity in ids:
            for repeat in (1,2):
                key=identity+'-'+str(repeat)
                cfg['windows_save_inputs'].append(dict(configuration='Debug',math_profile='automatic',case=identity,repeat=repeat,
                    path='D:/a/project/project/out/original-stock-audit/transport/Debug-automatic/remaining-stock-repaired/'+key+'/'+physical.CURRENT,
                    sha256=sha(path),parent_capture_sha256=sha(manifest),parent_producer_commit=physical.ORIGINAL,parent_run=key))
        return parent,case,cfg,members,SimpleNamespace(sha=sha)

    def test_exact_saved_input_rejects_replays_aliases_relabelled_parents_and_incomplete_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            parent,case,cfg,members,reader=self.paired_fixture(Path(directory))
            expected,path=physical.paired_input(parent,case,1,cfg,members,reader)
            self.assertEqual(path.read_bytes(),b'unchanged original fixture save\r\n')
            self.assertEqual(expected,cfg['windows_save_inputs'][0])
            for field,value in [('sha256','a'*64),('parent_capture_sha256','b'*64),('parent_producer_commit','f'*40),
                                ('parent_run','another-1'),('configuration','Release'),('math_profile','sse2'),
                                ('path','D:/a/project/project/out/relabelled-save.scn')]:
                changed=copy.deepcopy(cfg);changed['windows_save_inputs'][0][field]=value
                with self.assertRaises(ValueError,msg=field):physical.paired_input(parent,case,1,changed,members,reader)
            changed=copy.deepcopy(cfg);changed['windows_save_inputs'].pop()
            with self.assertRaises(ValueError):physical.paired_input(parent,case,1,changed,members,reader)
            changed=copy.deepcopy(cfg);changed['windows_save_inputs'][-1]=changed['windows_save_inputs'][0]
            with self.assertRaises(ValueError):physical.paired_input(parent,case,1,changed,members,reader)
            path.write_bytes(b'relabelled capture')
            with self.assertRaises(ValueError):physical.paired_input(parent,case,1,cfg,members,reader)

    def comparison_fixture(self,root):
        left=root/'left';right=root/'right';left.mkdir();right.mkdir();calls=[]
        for folder in (left,right):
            for name in ('stock-clock.csv','stock-step-clock.csv','camera.csv','fixture-trace.csv'):
                (folder/name).write_bytes(b'identical complete fixture rows\r\n')
            (folder/'scene.rgba').write_bytes(b'fixture only; no frame qualification')
            path=folder/physical.CURRENT;path.parent.mkdir();path.write_text(json.dumps({'vessels':'fixture','description':'same'}))
        def difference(a,b,excluded=()):
            calls.append(('exclusions',tuple(excluded)))
            return [name for name in set(a)|set(b) if name not in excluded and a.get(name)!=b.get(name)]
        def frame(a,b,width,height):calls.append(('frame',width,height));return 1.0
        def compare(name):
            def result(a,b,cfg):calls.append((name,a,b,cfg));return {'unchanged_comparator_fixture':name}
            return result
        reader=SimpleNamespace(content_differences=difference,parse_saved=lambda p:json.loads(p.read_text()),
            protocol=lambda:{'operator_description_blocks':['description']},
            windows=SimpleNamespace(image_ssim=frame,shared=SimpleNamespace(TRACES=['fixture-trace.csv'])),
            original_audit=SimpleNamespace(compare_state=compare('state'),camera_comparison=compare('camera'),detail_calibration=lambda a,b:{}))
        return left,right,reader,calls,dict(image_ssim_minimum=0.99,budgets={'original_fixture_budget':1e-10})

    def test_direct_windows_comparisons_keep_clock_content_full_frame_and_existing_budgets(self):
        with tempfile.TemporaryDirectory() as directory:
            left,right,reader,calls,config=self.comparison_fixture(Path(directory))
            (right/'stock-clock.csv').write_bytes((left/'stock-clock.csv').read_bytes().replace(b'\r\n',b'\n'))
            physical.compare_windows_pair(left,right,reader,config)
            self.assertIs(calls[0][3],config);self.assertIs(calls[1][3],config)
            self.assertIn(('frame',1280,720),calls);self.assertIn(('exclusions',('description',)),calls)
            reader.windows.image_ssim=lambda *args:math.nextafter(config['image_ssim_minimum'],-math.inf)
            with self.assertRaises(ValueError):physical.compare_windows_pair(left,right,reader,config)
            reader.windows.image_ssim=lambda *args:1.0
            path=right/physical.CURRENT;path.write_text(json.dumps({'vessels':'changed','description':'same'}))
            with self.assertRaises(ValueError):physical.compare_windows_pair(left,right,reader,config)
            path.write_text(json.dumps({'vessels':'fixture','description':'same'}))
            (right/'stock-step-clock.csv').write_bytes(b'different tick clock')
            with self.assertRaises(ValueError):physical.compare_windows_pair(left,right,reader,config)

    def test_repeat_comparison_preserves_byte_equality_and_has_no_saved_content_exclusions(self):
        with tempfile.TemporaryDirectory() as directory:
            left,right,reader,calls,config=self.comparison_fixture(Path(directory));record={'repeat_ssim':1.0}
            physical.inspect_repeat(left,right,record,reader,config)
            self.assertIn(('exclusions',()),calls);self.assertIn(('frame',1280,720),calls)
            with self.assertRaises(ValueError):physical.inspect_repeat(left,right,{'repeat_ssim':0.999},reader,config)
            path=right/physical.CURRENT;path.write_text(json.dumps({'vessels':'fixture','description':'different'}))
            with self.assertRaises(ValueError):physical.inspect_repeat(left,right,record,reader,config)
            path.write_text(json.dumps({'vessels':'fixture','description':'same'}))
            path=right/'fixture-trace.csv';path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
            with self.assertRaises(ValueError):physical.inspect_repeat(left,right,record,reader,config)


if __name__=='__main__':unittest.main()
