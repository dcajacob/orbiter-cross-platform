"""Complete phase composition fixtures; no real simulator or frame acceptance is run."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT

sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import audit_source_complete_phase as phase

spec=importlib.util.spec_from_file_location('phase_original_api_fixture',ROOT/'Tests/Production/Closeout/SourceCompleteOriginal.Test.py')
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


class CurrentPhysicalPhaseTests(unittest.TestCase):
    def complete(self):
        cases=[dict(id='case%03d'%n) for n in range(38)];ids=[c['id'] for c in cases]
        cfg=dict(math_profile='automatic',phase='stock',capture_scope=dict(kind='complete',gate='remaining-stock',cases=ids))
        worker=dict(cases_requested=ids,repeats=2,frames=960,actual_processes=76,successful_presents=76*960,
            cases={'automatic-stock-'+identity:{'runs':[{},{}]} for identity in ids})
        bound=dict(status='bound-source-complete-current-API-source-process-and-raw-export-receipts-only',request=cfg,worker=worker)
        return bound,dict(cases=cases,frames=960)

    def test_complete_physical_phase_cannot_skip_scenes_processes_or_repeats(self):
        bound,config=self.complete();self.assertEqual(phase.complete_cases(bound,config),config['cases'])
        changes=[lambda x:x['worker']['cases'].pop('automatic-stock-case000'),
            lambda x:x['worker']['cases']['automatic-stock-case000']['runs'].pop(),
            lambda x:x['worker'].update(actual_processes=75),lambda x:x['worker'].update(frames=959),
            lambda x:x['worker'].update(successful_presents=75*960),lambda x:x['worker'].update(repeats=1),
            lambda x:x['request']['capture_scope'].update(kind='diagnostic'),
            lambda x:x['worker']['cases_requested'].reverse(),lambda x:x.update(status='running')]
        for change in changes:
            modified=copy.deepcopy(bound);change(modified)
            with self.assertRaises(ValueError):phase.complete_cases(modified,config)

    def test_original_reference_is_bound_to_raw_zip_all_decoded_members_and_captured_api_identity(self):
        transport=reference.transport;saved_root=transport.ROOT
        try:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);transport.ROOT=root;archives=root/'out/archives';archives.mkdir(parents=True)
                run,jobs=reference.SourceCompleteOriginalTests().record();artifacts=[]
                for n,profile in enumerate(sorted(transport.legacy.PROFILES)):
                    name='matched-clock-remaining-stock-v2-'+profile;path=archives/(name+'.zip')
                    with zipfile.ZipFile(path,'w') as source:source.writestr('fixture.json',json.dumps(dict(fixture_only=True,profile=profile)))
                    artifacts.append(dict(id=7000+n,name=name,size_in_bytes=path.stat().st_size,digest='sha256:'+transport.sha(path),
                        expired=False,workflow_run=dict(id=transport.RUN,head_sha=transport.SOURCE,head_branch=transport.BRANCH)))
                manifest=transport.retain(dict(workflow_run=run,jobs=jobs,artifacts=artifacts),archives,root/'out/decoded')
                decoded={p:root/'out/decoded'/p for p in transport.legacy.PROFILES}
                bindings=transport.inspect_matrix(manifest,root,decoded,transport.SOURCE)
                payload=root/'current-api-payload';receipt=payload/'original-stock-audit/transport/download.json'
                receipt.parent.mkdir(parents=True);receipt.write_text(json.dumps(manifest))
                restored=payload/'reference-audit-restoration/restoration.json';restored.parent.mkdir()
                captured=copy.deepcopy(bindings)
                for value in captured.values():value['archive']='D:/original-collector/archives/unchanged.zip'
                restored.write_text(json.dumps(dict(original_api_archive_bindings=captured)))
                before=restored.read_bytes();profile='Debug-automatic';archive=Path(bindings[profile]['archive'])
                result=phase.bind_original(payload,decoded[profile],archive,profile)
                self.assertEqual(result,bindings[profile]);self.assertEqual(before,restored.read_bytes())
                altered=copy.deepcopy(captured);altered[profile]['original_stock_job_id']+=1
                restored.write_text(json.dumps(dict(original_api_archive_bindings=altered)))
                with self.assertRaises(ValueError):phase.bind_original(payload,decoded[profile],archive,profile)
                restored.write_bytes(before);(decoded[profile]/'extra-unmanifested.json').write_text('{}')
                with self.assertRaises(ValueError):phase.bind_original(payload,decoded[profile],archive,profile)
                (decoded[profile]/'extra-unmanifested.json').unlink();(decoded[profile]/'fixture.json').write_text('damaged bytes')
                with self.assertRaises(ValueError):phase.bind_original(payload,decoded[profile],archive,profile)
        finally:transport.ROOT=saved_root

    def test_full_physical_artifact_audit_cannot_be_started_as_local_fixture_work(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}):
            with self.assertRaisesRegex(ValueError,'hosted Linux'):
                phase.inspect(None,None,None,None,None,None,None,None,None,None,None)


if __name__=='__main__':unittest.main()
