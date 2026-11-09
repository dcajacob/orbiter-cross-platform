"""Native reload preparation preserves the real capture and binds every exact original save."""
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contracts import ROOT,case_ids
import capture_hosted_native_reload as reload
import hosted_native_reload_reference as reference


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


receipt_fixture=module('native_reload_receipt_fixture',ROOT/'Tests/Production/Closeout/SourceCompleteCurrent.Test.py')


class HostedNativeReloadTests(unittest.TestCase):
    def fixture(self,root):
        profile='Debug-automatic';base=root/'out/original-stock-audit';source=root/'fixture';source.mkdir()
        cfg=receipt_fixture.SourceCompleteCurrentTests().receipts(source)
        values={name:json.loads(Path(cfg[name]['path']).read_text()) for name in ('reference_transport','reference_audit','reference_persistence_audit','reference_restoration')}
        decoded=base/'transport'/profile;capture=decoded/'remaining-stock-repaired';capture.mkdir(parents=True);(decoded/'remaining-stock-repaired-build').mkdir();(base/'preserved-Debug').mkdir()
        ids=list(case_ids());parent=dict(producer_commit=reference.ORIGINAL,configuration='Debug',math_profile='automatic',
            protocol='remaining-stock-matched-clock-v2',status='captured-awaiting-independent-audit',diagnostic_only=False,
            cases_requested=ids,cases={name:dict(runs=[{},{}]) for name in ids},failures={})
        manifest=capture/'capture.json';manifest.write_text(json.dumps(parent));members={'remaining-stock-repaired/capture.json':reference.sha(manifest)}
        for name in ids:
            for repeat in (1,2):
                relative=name+'-'+str(repeat)+'/Scenarios/(Current state).scn';path=capture/relative;path.parent.mkdir(parents=True);path.write_bytes((name+': original fixture '+str(repeat)).encode());members['remaining-stock-repaired/'+relative]=reference.sha(path)
        archive=base/'archives'/('matched-clock-remaining-stock-v2-'+profile+'.zip');archive.parent.mkdir();archive.write_bytes(b'original opaque API fixture archive bytes')
        artifacts=[]
        for other in sorted(receipt_fixture.transport.legacy.PROFILES):
            name='matched-clock-remaining-stock-v2-'+other;artifacts.append(dict(profile=other,name=name,decoded='out/original-stock-audit/transport/'+other,path='out/original-stock-audit/archives/'+name+'.zip',sha256=reference.sha(archive),bytes=archive.stat().st_size))
        values['reference_transport']['artifacts']=artifacts
        values['reference_audit']['profiles'][profile]['capture_sha256']=reference.sha(manifest)
        values['reference_restoration']['original_api_archive_bindings'][profile]=dict(decoded_members_sha256=members,archive_sha256=reference.sha(archive),archive_bytes=archive.stat().st_size)
        paths=dict(reference_transport=base/'transport/download.json',reference_audit=base/'independent/writer-audit.json',
            reference_persistence_audit=base/'independent/original-persistence-audit.json',reference_restoration=root/'out/reference-audit-restoration/restoration.json')
        def save(name):paths[name].parent.mkdir(parents=True,exist_ok=True);paths[name].write_text(json.dumps(values[name]));return reference.sha(paths[name])
        msha=save('reference_transport');values['reference_audit']['download_manifest_sha256']=msha;wsha=save('reference_audit')
        values['reference_persistence_audit'].update(transport_sha256=msha,writer_audit_sha256=wsha);csha=save('reference_persistence_audit')
        values['reference_restoration'].update(original_transport_sha256=msha,original_writer_audit_sha256=wsha,original_cohort_audit_sha256=csha);save('reference_restoration')
        for name in ('hosted_native_reload_reference.py','capture_hosted_native_reload.py'):
            target=root/'Tests/Production/Closeout'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'Tests/Production/Closeout'/name,target)
        return profile,archive

    def test_actual_parent_manifest_and_all_76_save_bytes_are_bound_and_changes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);profile,archive=self.fixture(root)
            def git(argv,**kwargs):return (root/argv[-1].split(':',1)[1]).read_bytes()
            with patch.object(reference,'ROOT',root),patch.dict(os.environ,GITHUB_SHA='e'*40),patch.object(reference.subprocess,'check_output',side_effect=git):
                result=reference.bind(profile);self.assertEqual(len(result['saved_inputs']),76);self.assertFalse(result['native_admission_qualified']);self.assertEqual(reference.verify(result),result)
                path=Path(result['saved_inputs'][-1]['path']);old=path.read_bytes();path.write_bytes(old+b' changed')
                with self.assertRaises(ValueError):reference.bind(profile)
                with self.assertRaises(ValueError):reference.verify(result)
                path.write_bytes(old);self.assertEqual(reference.verify(result),result)
                changed=copy.deepcopy(result);changed['saved_inputs'].pop()
                with self.assertRaises(ValueError):reference.verify(changed)
                changed=copy.deepcopy(result);changed['saved_inputs'][0]=copy.deepcopy(changed['saved_inputs'][1])
                with self.assertRaises(ValueError):reference.verify(changed)
                archive.write_bytes(archive.read_bytes()+b' changed')
                with self.assertRaises(ValueError):reference.bind(profile)

    def test_full_native_capture_and_independent_checks_are_conserved_for_the_new_phase(self):
        old=reload.writer.prepared_body();new=reload.prepared_body();ast.parse(new)
        changes=[("protocol='phase6-hosted-native-exact-save-reload-v1'","protocol='phase6-hosted-native-stock-writer-runtime-v3'"),
            ("output=ROOT/'out/hosted-native-reload'/a.profile","output=ROOT/'out/hosted-native-writer'/a.profile"),
            ('windows_comparisons_pending=True,writer_phase_pending=True','windows_comparisons_pending=True,reload_phase_pending=True'),
            ("        from hosted_native_reload_reference import bind as bind_reference,verify as verify_reference\n        reference=bind_reference(a.profile);report['original_reference']=reference;save()\n",''),
            ("capture=ROOT/'out/native-stock-reload'/a.profile","capture=ROOT/'out/native-stock-writer'/a.profile"),
            ("'--phase','windows-save-reload'","'--phase','stock-writer'"),
            ("        argv+=['--windows-parent-capture',reference['capture'],'--windows-build',reference['build'],'--preserved',reference['preserved']]\n",''),
            ('all-38-exact-Windows-save-reloads-twice','all-38-stock-writers-twice'),
            ("reader,a.profile,'windows-save-reload'","reader,a.profile,'stock-writer'"),
            ('Complete independent native exact-save reload audit required','Complete independent native writer-only audit required'),
            ('independent-native-reload-audit.json','independent-native-writer-audit.json'),
            ('        verify_reference(reference)\n',''),
            ('captured-and-independently-audited-native-exact-save-reloads-only','captured-and-independently-audited-native-writers-only')]
        for before,after in changes:self.assertGreaterEqual(new.count(before),1);new=new.replace(before,after)
        self.assertEqual(new,old)
        name='Tests/Production/RemainingStockPersistence/capture_native.py';self.assertEqual((ROOT/name).read_bytes(),subprocess.check_output(['git','-C',str(ROOT),'show',reload.SOURCE+':'+name]))
        self.assertEqual((ROOT/'Tests/Production/Closeout/prepare_hosted_native_reload.sh').read_text().replace('capture_hosted_native_reload.py','capture_hosted_native_writer_runtime.py',1),(ROOT/'Tests/Production/Closeout/prepare_hosted_native_writer_runtime.sh').read_text())

    def test_no_native_reload_lane_can_start_before_the_actual_complete_original_audit(self):
        text=(ROOT/'.github/workflows/phase6-native-stock-reloads.yml').read_text()
        for config in ('debug','release'):
            for mode in ('automatic','sse2'):self.assertIn('qualification/native-stock-reload-'+config+'-'+mode+'-v1',text)
        self.assertIn("a13bae582c7de0c9b6e2fd0c064b1a3ea12e85c7",text);self.assertIn("run.conclusion==='success'",text)
        self.assertIn('originalJobs.length!==5',text);self.assertIn('restore_source_complete_reference.py',text)
        self.assertIn('Stage the exact untouched original Windows application and SDK without execution',text)
        self.assertIn('needs: controls',text);self.assertIn('needs.controls.outputs.audit_run_id',text)
        self.assertIn('prepare_hosted_native_reload.sh',text);self.assertNotIn('previous-capture-api.json',text)
        self.assertIn('runs-on: ubuntu-24.04',text);self.assertIn('timeout-minutes: 330',text);self.assertIn('cancel-in-progress: false',text)
        self.assertNotIn('--case',text);self.assertNotIn('detect_leaks=0',text)


if __name__=='__main__':unittest.main()
