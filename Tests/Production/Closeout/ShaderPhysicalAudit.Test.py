"""Small actual ZIP/API/retry fixtures; no simulator or physical acceptance credit."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT

HOSTED=ROOT/'Tests/Production/CurrentWindows/Hosted';sys.path.insert(0,str(HOSTED))
import audit_current_shader_phase_cli as cli
import audit_current_phase_cli as old_cli
import audit_source_complete_shader_phase as phase
import audit_source_complete_phase as old_phase
import verify_shader_capture_readiness as readiness


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


closed=module('shader_physical_closed_fixture',ROOT/'Tests/Production/Closeout/ShaderClosedPhase.Test.py')
retry=module('shader_physical_retry_fixture',ROOT/'Tests/Production/Closeout/CurrentAuditRetry.Test.py')


class ShaderPhysicalAuditTests(unittest.TestCase):
    def api(self):
        record=closed.ShaderClosedPhaseTests().api();artifacts=[]
        for number,cell in enumerate(sorted(readiness.EXPECTED),1):
            artifact=copy.deepcopy(record['artifact']);artifact.update(id=7000+number,
                name='shader-source-complete-current-stock-'+'-'.join(cell));artifacts.append(artifact)
        return dict(repository=record['repository'],run=record['run'],jobs=record['jobs'],artifacts=artifacts)

    def test_all_eight_actual_cells_all_nine_jobs_and_shader_steps_are_required_before_readiness(self):
        record=self.api();result=readiness.verify(record)
        self.assertEqual(len(result['actual_capture_cells']),8);self.assertFalse(result['phase6_complete'])
        for change in (lambda r:r['artifacts'].pop(),lambda r:r['artifacts'].append(copy.deepcopy(r['artifacts'][0])),
                       lambda r:r['artifacts'][0].update(id=r['artifacts'][1]['id']),
                       lambda r:r['artifacts'][-1].update(expired=True),
                       lambda r:r['artifacts'][-1].update(name='source-complete-current-stock-Release-sse2-stock'),
                       lambda r:r['jobs'][-1].update(status='in_progress',conclusion=None),
                       lambda r:next(j for j in r['jobs'] if j['name']!='readiness')['steps'][5].update(conclusion='skipped'),
                       lambda r:r['jobs'][-1]['labels'].append('self-hosted'),
                       lambda r:r['run'].update(run_attempt=2)):
            changed=copy.deepcopy(record);change(changed)
            with self.assertRaises(ValueError):readiness.verify(changed)

    def test_full_scene_coverage_original_reference_sdk_scalar_and_comparison_bodies_are_conserved(self):
        def body(path,name):return ast.dump(next(n for n in ast.parse(Path(path).read_bytes()).body
            if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
        for name in ('complete_cases','bind_original','inspected_inputs'):
            self.assertEqual(body(phase.__file__,name),body(old_phase.__file__,name))
        for name in ('scalar_binding','decode_current'):
            self.assertEqual(body(cli.__file__,name),body(old_cli.__file__,name))
        def loops(path):
            tree=ast.parse(Path(path).read_bytes());inspect=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='inspect')
            return [ast.dump(n,include_attributes=False) for n in inspect.body[-2].body if isinstance(n,ast.For)]
        original=loops(old_phase.__file__);self.assertTrue(original)
        self.assertEqual(loops(phase.__file__),original)

    def test_new_entry_decodes_only_actual_exact_shader_source_archives_with_full_capacity_reserve(self):
        record=self.api();cell=('Debug','automatic','stock')
        artifact=next(a for a in record['artifacts'] if a['name']=='shader-source-complete-current-stock-'+'-'.join(cell))
        api={key:record[key] for key in ('repository','run','jobs')};api['artifact']=artifact
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'fixture-only.zip'
            with zipfile.ZipFile(archive,'w') as source:source.writestr('fixture-only.json','{"runtime_credit":false}')
            artifact.update(size_in_bytes=archive.stat().st_size,digest='sha256:'+cli.sha(archive))
            with patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(free=8*1024**3)):
                with self.assertRaisesRegex(ValueError,'capacity reserve'):cli.decode_current(api,archive,root/'full',cell)
            self.assertFalse((root/'full').exists())
            with patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(free=9*1024**3)):
                self.assertEqual(cli.decode_current(api,archive,root/'fresh',cell),
                    {'fixture-only.json':cli.sha(root/'fresh/fixture-only.json')})
                with self.assertRaises(ValueError):cli.decode_current(api,archive,root/'fresh',cell)
                changed=copy.deepcopy(api);changed['run']['head_sha']='0'*40
                with self.assertRaises(ValueError):cli.decode_current(changed,archive,root/'old-source',cell)
                archive.write_bytes(archive.read_bytes()+b'changed transport')
                with self.assertRaises(ValueError):cli.decode_current(api,archive,root/'changed',cell)
            self.assertFalse((root/'old-source').exists());self.assertFalse((root/'changed').exists())

    def test_independent_retry_proof_rechecks_real_zip_log_partial_members_and_same_owner(self):
        with retry.CurrentAuditRetryTests().evidence() as (out,cfg,restored,manifest):
            with patch.object(cli,'ROOT',out.parent):
                proof,guarded,actual=cli.independent_reference('e'*40)
                self.assertEqual(actual,restored);self.assertEqual(proof['original_windows_processes'],608)
                self.assertIn(str(out/'reference-api/first-job.log'),guarded)
                self.assertIn(str(out/'reference-api/audit.zip'),guarded)
                self.assertTrue(any('first-attempt-source-artifact' in path for path in guarded))
                self.assertFalse(proof['phase6_complete'])
                with self.assertRaises(ValueError):cli.independent_reference('f'*40)
                first=out/'reference-api/first.zip';first.write_bytes(first.read_bytes()+b'changed exact first failure')
                with self.assertRaises(ValueError):cli.independent_reference('e'*40)

    def test_cross_restoration_comparison_preserves_separate_raw_metadata_but_no_changed_stable_fact(self):
        with retry.CurrentAuditRetryTests().evidence() as (out,cfg,restored,manifest):
            captured=copy.deepcopy(restored);captured['restorer_source']='a'*40
            captured['audit_retry_lineage']['first_attempt_api_sha256']='a'*64
            captured['audit_retry_lineage']['first_job_log_transport']={'fixture_only':'different independently verified wire representation'}
            before=copy.deepcopy(captured);result=cli.compare_reference(captured,restored)
            self.assertEqual(captured,before);self.assertTrue(result['raw_API_and_log_transport_identities_preserved'])
            self.assertFalse(result['API_attempts_normalized']);self.assertFalse(result['qualification_granted'])
            for key,value in [('first_job_log_sha256','a'*64),('successful_attempt',1),
                              ('old_failed_attempt_relabelled',True),('same_original_transport_sha256','b'*64)]:
                changed=copy.deepcopy(captured);changed['audit_retry_lineage'][key]=value
                with self.assertRaises(ValueError):cli.compare_reference(changed,restored)
            changed=copy.deepcopy(captured);changed['audit_retry_lineage'].pop('first_attempt_api_sha256')
            with self.assertRaises(ValueError):cli.compare_reference(changed,restored)
            changed=copy.deepcopy(captured);changed['original_audit_artifact_id']+=1
            with self.assertRaises(ValueError):cli.compare_reference(changed,restored)

    def test_audit_retains_its_first_partial_failure_in_a_new_output_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'fresh-reports/nested/cell.json'
            inputs=dict(runtime_local=str(root/'runtime'),observer_local=str(root/'observer/observer.dll'))
            with patch.dict(cli.os.environ,{'GITHUB_ACTIONS':'true'}),patch.object(phase.sys,'platform','linux'),\
                 patch.object(phase,'api_identity',side_effect=ValueError('fixture-only failure before physical inspection')):
                with self.assertRaisesRegex(ValueError,'fixture-only failure'):
                    phase.inspect(root/'payload',{},root/'current.zip',('Debug','automatic','stock'),inputs,
                        None,{},root/'original',root/'original.zip',root/'mesa',output)
            result=json.loads(output.read_text())
            self.assertEqual(result['status'],'failed');self.assertIn('fixture-only failure',result['error'])
            self.assertEqual(result['actual_current_processes'],0);self.assertEqual(result['actual_original_comparisons'],0)
            self.assertFalse(result['phase6_complete']);self.assertFalse(result['native_admission_qualified'])


    def test_all_shader_retry_and_owning_reader_sources_are_guarded_before_and_after(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);hosted=root/'Tests/Production/CurrentWindows/Hosted';hosted.mkdir(parents=True)
            closeout=root/'Tests/Production/Closeout';closeout.mkdir()
            paths=[hosted/'inspect_current_shader_inputs.py',hosted/'audit_source_complete_shader_phase.py',closeout/'audit_retry_lineage.py']
            for path in paths:path.write_text('# fixture source only\n')
            reader=SimpleNamespace(original_audit=SimpleNamespace(verifier_inputs=lambda:{'original/source.py':'a'*64}))
            with patch.object(phase,'ROOT',root):
                before=phase.guarded_sources(reader)
                self.assertTrue(all(path.relative_to(root).as_posix() in before for path in paths))
                paths[0].write_text('# changed actual source bytes\n')
                self.assertNotEqual(phase.guarded_sources(reader),before)
                (hosted/'unexpected_reader.py').write_text('# added source\n')
                self.assertIn('Tests/Production/CurrentWindows/Hosted/unexpected_reader.py',phase.guarded_sources(reader))

    def test_prepared_workflow_keeps_full_matrix_standard_runners_exact_retry_and_all_partial_outputs(self):
        path=ROOT/'.github/workflows/phase6-current-shader-physical-audit.yml';scripts=path.read_text()
        self.assertEqual([line.strip() for line in scripts.splitlines() if 'runs-on:' in line],['runs-on: ubuntu-24.04']*2)
        for expected in ('fail-fast: false','max-parallel: 4','configuration: [Debug, Release]',
                         'math_profile: [automatic, sse2]','phase: [stock, reload]'):
            self.assertIn(expected,scripts)
        for expected in ('phase6-require-retry-reference.cjs','phase6-download-source-complete-retry.cjs',
                         'verify_shader_capture_readiness.py','audit_current_shader_phase_cli.py','restore_source_complete_retry_reference.py',
                         '--first-attempt-api','--first-attempt-archive','--first-attempt-log'):
            self.assertIn(expected,scripts)
        self.assertNotIn('restore_source_complete_reference.py',scripts);self.assertNotIn('46168cd076a07fda53599c1de8bbc6200852322b',scripts)
        retained=scripts[scripts.rindex('      - uses: actions/upload-artifact@v7'):]
        self.assertIn('if: always()',retained)
        for expected in ('first.zip','first-job.log','audit.zip','out/current-physical-audits/*.json','restoration.json'):
            self.assertIn(expected,retained)


if __name__=='__main__':unittest.main()
