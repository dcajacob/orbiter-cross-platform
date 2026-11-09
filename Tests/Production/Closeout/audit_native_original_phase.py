"""Independently compare one complete retained native phase with its actual original cohort.

The standard hosted bootstrap must restore the exact captured runtime, providers,
assets and userspace first. This audits all 38 scenes twice without launching a
simulator. Complete four-profile/two-phase and direct build gates remain required.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from contracts import ROOT,require,sha,load,atomic_json,PROFILES,PHASES

PERSISTENCE=ROOT/'Tests/Production/RemainingStockPersistence'
sys.path[:0]=[str(PERSISTENCE),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
import inspect_native_writer_receipts as writers
import inspect_native_reload_receipts as reloads
import source_complete_original_transport as original
from audit_current_shader_phase_cli import independent_reference,scalar_binding
from audit_source_complete_shader_phase import guarded_sources

spec=importlib.util.spec_from_file_location('conserved_native_original_full_persistence_audit',PERSISTENCE/'audit.py')
persistence=importlib.util.module_from_spec(spec);spec.loader.exec_module(persistence)
persistence.transport=original.legacy
require(Path(persistence.transport.__file__).resolve()==PERSISTENCE/'transport.py','Exact original persistence archive reader required')


def complete_scope(capture,observed,profile,phase,config):
    """Neither a selected diagnostic nor a shortened physical result can supply this phase."""
    ids=[c['id'] for c in config['cases']];configuration,mode=profile.split('-',1)
    require(profile in PROFILES and phase in PHASES and len(ids)==len(set(ids))==38 and config['frames']==960,
        'Complete unchanged native/original phase and all38 cases required')
    expected=writers.SOURCE if phase=='stock-writer' else reloads.SOURCE
    require(capture['producer_commit']==expected and capture['phase']==phase and capture['host']=='native-linux' and
        capture['runtime_source_commit']==writers.RUNTIME and capture['runtime_role']=='normal' and
        capture['observer_delay_ms']==120 and capture['process_receipts']=='owned-pid-start-argv-exit-v1' and
        capture['runtime_identity']['configuration']==configuration and capture['runtime_identity']['math_profile']==mode and
        capture['cases_requested']==ids and set(capture['cases'])==set(ids) and capture['repeats']==2 and capture['frames']==960 and
        all(len(v['runs'])==2 for v in capture['cases'].values()) and not capture['failures'] and capture['diagnostic_only'] is False and
        capture['status']=='captured-awaiting-independent-persistence-audit' and capture['phase6_complete'] is False and
        capture['native_admission_qualified'] is False,'Every actual native capture source/normal-role/process/scope receipt required')
    require(observed['status']=='audited-native-phase-only' and observed['phase']==phase and observed['profile']==profile and
        observed['source_producer']==expected and observed['runtime_source']==writers.RUNTIME and observed['runtime_role']=='normal' and
        observed['observer_delay_ms']==120 and observed['actual_processes']==76 and observed['actual_presentations']==76*960 and
        set(observed['cases'])==set(ids) and all(len(v['runs'])==2 for v in observed['cases'].values()) and
        observed['owning_bytes_unchanged'] is True and observed['diagnostic_only'] is False and
        observed['phase6_complete'] is False and observed['native_admission_qualified'] is False,
        'All76 independently recomputed native physical observations required')
    return config['cases']


def bound_native_tree(payload,native,profile,phase):
    """Require an exact retained copy at the original recorded native paths; never rewrite a capture."""
    require(profile in PROFILES and phase in PHASES,'Exact native phase/profile required')
    prefix='native-stock-writer' if phase=='stock-writer' else 'native-stock-reload'
    source=Path(payload)/prefix/profile;target=ROOT/'out'/prefix/profile
    require(Path(native).resolve()==target and source.resolve()!=target and source.is_dir() and target.is_dir(),
        'Original native capture paths and a separate API-decoded source required')
    def inventory(root):
        files={}
        for path in root.rglob('*'):
            require(not path.is_symlink(),'Retained native input tree cannot redirect through a symlink')
            if path.is_file():files[path.relative_to(root).as_posix()]=sha(path)
        return files
    expected=inventory(source);require(expected and 'capture.json' in expected and inventory(target)==expected,
        'Every actual native input file must equal its exact raw API-decoded source; no extras or omissions')
    return expected


def original_bindings():
    manifest=load(ROOT/'out/original-stock-audit/transport/download.json')
    decoded={profile:ROOT/'out/original-stock-audit/transport'/profile for profile in PROFILES}
    return original.inspect_matrix(manifest,ROOT,decoded,original.SOURCE)


def inspect(payload,api,archive,native,profile,phase,ssim_api,ssim_archive,mesa,output,api_file):
    """Re-read all native physics and directly compare all76 pairs at every original budget."""
    require(sys.platform=='linux' and os.environ.get('GITHUB_ACTIONS')=='true' and
        os.environ.get('RUNNER_OS')=='Linux' and os.environ.get('GITHUB_REPOSITORY')=='dcajacob/orbiter-cross-platform' and
        os.environ.get('ImageOS')=='ubuntu24' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,
        'Actual standard hosted Ubuntu24 runner with restored matching native userspace required')
    require(profile in PROFILES and phase in PHASES,'Exact complete native/original phase required')
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    require(head==os.environ['GITHUB_SHA'],'Actual independent native auditor source differs')
    require(not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=all','--','Tests/Production'],text=True).strip(),
        'Actual independent owning-source worktree must match the immutable auditor commit')
    output=Path(output).resolve();payload=Path(payload).resolve();native=Path(native).resolve();archive=Path(archive).resolve()
    protected=(payload,native,ROOT/'out/original-stock-audit',ROOT/'out/phase6-hosted-native',ROOT/'out/hosted-native-providers',ROOT/'out/hosted-mesa-topology',ROOT/'out/native-stock-assets',ROOT/'out/native-stock-data',ROOT/'out/native-stock-planets',Path(mesa).resolve())
    require(output==ROOT/'out/native-original-physical-audits'/(profile+'-'+phase+'.json') and not output.exists() and all(not output.is_relative_to(path) for path in protected),
        'Fresh partial physical report must be separate from all protected native/original inputs')
    output.parent.mkdir(parents=True,exist_ok=True)
    report=dict(protocol='phase6-independent-native-original-complete-physical-phase-v1',status='running',profile=profile,phase=phase,
        auditor_source=head,required_profiles=4,required_phases=2,required_cases=38,required_repeats=2,required_frames=960,
        actual_native_processes=0,actual_direct_original_native_pairs=0,cases={},
        complete_four_profile_two_phase_matrix_pending=True,direct_native_and_original_build_pairs_pending=True,
        current_native_comparisons_pending=True,other_class_lifetime_full157_and_hardware_gates_pending=True,
        qualification_granted=False,phase6_complete=False,native_admission_qualified=False)
    def save():atomic_json(output,report)
    save()
    try:
        require(load(api_file)==api,'Actual native API receipt differs from the retained immutable record')
        api_guards={str(Path(path).resolve()):sha(path) for path in (api_file,ssim_api)}
        collector=writers if phase=='stock-writer' else reloads
        raw=collector.inspect(api,archive,profile);tree=bound_native_tree(payload,native,profile,phase)
        reader=persistence.bind_owner(ROOT,collector.SOURCE);config=reader.native.settings(reader.protocols.V2)
        original_ssim=reader.windows.image_ssim
        scalar=scalar_binding(Path(ssim_api),Path(ssim_archive),reader,head,original_ssim)
        reader.native.shared.image_ssim=reader.windows.image_ssim
        reference,reference_files,restored=independent_reference(head);bindings=original_bindings()
        sources=guarded_sources(reader)|{str(PERSISTENCE/name):sha(PERSISTENCE/name) for name in ('audit.py','observations.py','capture_native.py','saved_state.py','saved_inputs.py')}
        originals=ROOT/'out/original-stock-audit/transport'/profile
        preserved=ROOT/'out/original-stock-audit'/('preserved-'+profile.split('-',1)[0])
        mesa_files,mesa_imports=reader.original_audit.independent_mesa(Path(mesa),original.SOURCE)
        observed_original=persistence.inspect_windows(originals,profile,reader,preserved,mesa_files,mesa_imports)
        observed_native=persistence.inspect_native(native,ROOT,reader,profile,phase)
        capture=load(native/'capture.json');cases=complete_scope(capture,observed_native,profile,phase,config)
        runtime_guards=dict(capture['guarded_files_sha256'])|{str(path):sha(path) for path in preserved.rglob('*') if path.is_file()}
        require(runtime_guards and all(sha(name)==value for name,value in runtime_guards.items()),'Every restored native runtime and preserved original input byte required')
        require(capture['actual_original_data']==load(originals/'remaining-stock-repaired/capture.json')['actual_original_simulation_data'],
            'Actual native/original full data locks and witnesses must agree')
        report.update(native_source=collector.SOURCE,compiled_runtime_source=writers.RUNTIME,raw_native_proof=raw,
            native_API_archive_sha256=api['artifact']['digest'],native_decoded_tree_sha256=tree,original_reference=reference,
            original_api_bindings=bindings,independent_original_observations=observed_original,
            independent_native_observations=observed_native,actual_native_processes=observed_native['actual_processes'],
            guarded_runtime_and_preserved_original_inputs_sha256=runtime_guards,actual_scalar_binding=scalar,guarded_sources_sha256=sources,
            unchanged_budgets=config['budgets'],unchanged_image_ssim_minimum=config['image_ssim_minimum'])
        save()
        for case in cases:
            runs=[];report['cases'][case['id']]=dict(runs=runs)
            for repeat in (1,2):
                report.update(active_case=case['id'],active_repeat=repeat);save()
                ws=originals/'remaining-stock-repaired'/(case['id']+'-'+str(repeat))
                wr=originals/'remaining-stock-persistence'/(case['id']+'-'+str(repeat))
                folder=native/(case['id']+'-'+str(repeat))
                if phase=='windows-save-reload':
                    prior=observed_native['cases'][case['id']]['runs'][repeat-1]
                    require(prior['persistence_input']['saved_input_sha256']==sha(ws/persistence.CURRENT)==sha(folder/prior['executed_case']['scenario_entry_point']),
                        'Actual native and original reloads must consume the same exact original saved input')
                runs.append(dict(direct_original_native=persistence.compare_pair(ws if phase=='stock-writer' else wr,folder,reader,config),
                    original_windows_roundtrip=persistence.serialization_calibration(ws,wr,reader)))
                report['actual_direct_original_native_pairs']+=1;save()
        require(len(report['cases'])==38 and report['actual_native_processes']==report['actual_direct_original_native_pairs']==76,
            'Every complete native/original direct pair required; subset reports never qualify')
        require(collector.inspect(api,archive,profile)==raw and bound_native_tree(payload,native,profile,phase)==tree and
            original_bindings()==bindings and independent_reference(head)==(reference,reference_files,restored) and
            scalar_binding(Path(ssim_api),Path(ssim_archive),reader,head,original_ssim)==scalar and
            guarded_sources(reader)|{str(PERSISTENCE/name):sha(PERSISTENCE/name) for name in ('audit.py','observations.py','capture_native.py','saved_state.py','saved_inputs.py')}==sources and
            all(sha(name)==value for name,value in (reference_files|api_guards|runtime_guards).items()) and load(api_file)==api and
            reader.original_audit.independent_mesa(Path(mesa),original.SOURCE)==(mesa_files,mesa_imports),
            'Native/original API archives, decoded inputs, original retry receipts, proven scalar or owning readers changed during physical comparison')
        report.update(status='passed-one-complete-native-original-physical-phase-only',successful_native_presentations=76*960)
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    return report
