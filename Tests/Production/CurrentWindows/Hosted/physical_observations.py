"""Independent current-stock observations after immutable transport/input restoration.

These functions compose the existing readers. They grant no matrix or native
qualification; callers must independently bind the API archives, source-complete
phase receipts, current SDK/observer and complete original reference first.
"""
import importlib.util
import json
from pathlib import Path, PureWindowsPath

ROOT=Path(__file__).resolve().parents[4]
APPLICATION='c08f93151827949ee3ad498f8021f35c11753fde'
ORIGINAL='ba38a7efccb5f770e87add95f5e966aa40270756'
CURRENT='Scenarios/(Current state).scn'
EXTRAS={'loaded_modules','executed_case','persistence_input','saved_state'}


def require(value,message):
    if not value:raise ValueError(message)


def load(path):return json.loads(Path(path).read_text())


def recorded_observation(actual,recorded):
    """Require every recomputed field, including fields absent from a forged receipt."""
    require(set(recorded)==set(actual)|EXTRAS and
            all(recorded[key]==value for key,value in actual.items()),
            'Complete independently recomputed current observation differs')


def class_inputs(folder,case,config,inputs,reader):
    """Bind the preserved/staged class witnesses to actual independently restored SDK bytes."""
    invocation=load(folder/'invocation.json');runtime=Path(inputs['runtime_local'])
    reader.windows.shared.inspect_inputs(folder,case,config)
    classes=set(case['declared_vessels'].values())
    for kind in classes:
        item=config['classes'][kind];name=item['target'];path=runtime/name
        require(path.is_file() and not path.is_symlink() and
                reader.sha(path)==inputs['runtime_files_sha256'][name]==
                invocation['input_sha256'][name]==invocation['preserved_inputs_sha256'][name] and
                reader.sha_lf(path)==item['sha256_lf'],
                'Actual current class input differs from the independently inspected SDK: '+kind)
    return len(classes)


def paired_input(parent,case,repeat,cfg,members,reader):
    """Read the exact BA38 writer save, without translating or rewriting its captured receipt."""
    parent=Path(parent);mode=cfg['math_profile'];profile=cfg['configuration']+'-'+mode
    ids=cfg['capture_scope']['cases'];report=load(parent/'capture.json')
    manifest_sha=reader.sha(parent/'capture.json')
    require(len(ids)==len(set(ids))==38 and report['producer_commit']==ORIGINAL and
            report['configuration']==cfg['configuration'] and report['math_profile']==mode and
            report['protocol']=='remaining-stock-matched-clock-v2' and
            report['status']=='captured-awaiting-independent-audit' and report['diagnostic_only'] is False and
            report['cases_requested']==ids and set(report['cases'])==set(ids) and not report['failures'] and
            all(len(item['runs'])==2 for item in report['cases'].values()) and
            manifest_sha==members['remaining-stock-repaired/capture.json'],
            'Exact complete API-bound original parent capture required')
    supplied={(value['case'],value['repeat']):value for value in cfg['windows_save_inputs']}
    require(len(supplied)==len(cfg['windows_save_inputs'])==76 and
            set(supplied)=={(identity,n) for identity in ids for n in (1,2)},
            'Every unique exact original writer save must be declared')
    key=case['id']+'-'+str(repeat);relative=key+'/'+CURRENT;path=parent/relative
    expected_path=PureWindowsPath(cfg['workspace'])/'out/original-stock-audit/transport'/profile/'remaining-stock-repaired'/relative
    expected=dict(configuration=cfg['configuration'],math_profile=mode,case=case['id'],repeat=repeat,
        path=supplied[(case['id'],repeat)]['path'],sha256=reader.sha(path),parent_capture_sha256=manifest_sha,
        parent_producer_commit=ORIGINAL,parent_run=key)
    require(supplied[(case['id'],repeat)]==expected and
            PureWindowsPath(expected['path'])==expected_path and
            expected['sha256']==members['remaining-stock-repaired/'+relative],
            'Exact API-bound original saved bytes, path or parent identity differs')
    return expected,path


def inspect_run_record(folder,case,repeat,recorded,cfg,inputs,config,reader,mesa,mesa_imports,
                       original_parent,original_members):
    """Re-read one actual current process with unchanged physical, clock and module readers."""
    spec=importlib.util.spec_from_file_location('independent_current_stock_observer',ROOT/'Tests/Production/CurrentWindows/stock.py')
    stock=importlib.util.module_from_spec(spec);spec.loader.exec_module(stock)
    folder=Path(folder);mode=cfg['math_profile'];phase=cfg['phase']
    require(cfg['source_commit']==APPLICATION and inputs['status']=='inspected-immutable-Windows-build-and-observer-bytes-only' and
            inputs['compiled_application_source']==inputs['compiled_observer_source']==APPLICATION and
            inputs['configuration']==cfg['configuration'] and phase in ('stock','reload') and mode in ('automatic','sse2') and
            type(repeat) is int and repeat in (1,2) and config['frames']==960,'Actual complete current application/SDK/profile required')
    paired,parent_save=paired_input(original_parent,case,repeat,cfg,original_members,reader)
    if phase=='reload':
        executed,provenance=reader.derived_case(case,config,parent_save,paired['sha256'])
        require(reader.sha(folder/executed['scenario_entry_point'])==paired['sha256'],
                'Current reload did not consume the exact independently restored original save')
    else:executed,provenance=case,None
    require(recorded['executed_case']==executed and recorded['persistence_input']==provenance,
            'Actual current scene or exact saved-input derivation differs')
    actual=stock.inspect_run(folder,executed,config,reader.windows,APPLICATION,ROOT)
    recorded_observation(actual,recorded)
    require(actual['actual_math']==('sse2' if mode=='sse2' else 'fma3'),
            'Actual independently observed current CRT mode differs')
    require(load(folder/'current-runtime-variant.json')==dict(cohort='current-windows',roles=cfg['roles'],
        configuration=cfg['configuration'],math_profile=mode,phase=phase,case=case['id'],repeat=repeat,
        paired_windows_input=paired if phase=='reload' else None),
        'Actual current runtime roles and dispatch metadata differ')
    require(inputs['executed_runtime_files_sha256']==dict(inputs['runtime_files_sha256'])|
            {'Modules/Plugin/ProductionCockpitDriver.dll':inputs['observer']['sha256']},
            'Only the independently inspected passive observer may replace a pristine SDK member')
    system=reader.original_audit.loaded_modules(folder,recorded['loaded_modules'],inputs['executed_runtime_files_sha256'],
        executed,config,mesa,mesa_imports,Path(inputs['runtime_local']))
    classes=class_inputs(folder,executed,config,inputs,reader)
    actual_data=load(folder/'actual-data-inputs.json');reader.data_inputs.validate(actual_data)
    saved=reader.parse_saved(folder/CURRENT)
    require(saved==recorded['saved_state'],'Complete actual current saved state differs from its receipt')
    return dict(observation=actual,complete_saved_state=saved,actual_class_inputs=classes,
                actual_simulation_data=actual_data,system_modules=system)


def compare_windows_pair(left,right,reader,config):
    """Direct original/current or current Debug/Release comparison at every existing budget."""
    left=Path(left);right=Path(right)
    state=reader.original_audit.compare_state(left,right,config)
    camera=reader.original_audit.camera_comparison(left,right,config)
    require(all((left/name).read_bytes().replace(b'\r\n',b'\n')==
                (right/name).read_bytes().replace(b'\r\n',b'\n')
                for name in ('stock-clock.csv','stock-step-clock.csv')),
            'Actual Windows begin/end matched clocks differ')
    differences=reader.content_differences(reader.parse_saved(left/CURRENT),reader.parse_saved(right/CURRENT),
                                          reader.protocol()['operator_description_blocks'])
    require(not differences,'Complete Windows saved content differs: '+json.dumps(differences[:10]))
    similarity=reader.windows.image_ssim((left/'scene.rgba').read_bytes(),(right/'scene.rgba').read_bytes(),1280,720)
    require(similarity>=config['image_ssim_minimum'],'Complete Windows framebuffer exceeds unchanged budget')
    return dict(state=state,camera=camera,ssim=similarity,complete_saved_content_identical=True,
                actual_clocks_identical_lf=True,detail_calibration_only=reader.original_audit.detail_calibration(left,right))


def inspect_repeat(left,right,recorded,reader,config):
    """Keep the collector's byte-exact repeats and saved-content rule without exclusions."""
    left=Path(left);right=Path(right)
    for name in (*reader.windows.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv'):
        require((left/name).read_bytes()==(right/name).read_bytes(),'Current repeated raw trace differs: '+name)
    require(not reader.content_differences(reader.parse_saved(left/CURRENT),reader.parse_saved(right/CURRENT)),
            'Current repeated complete saved content differs')
    score=reader.windows.image_ssim((left/'scene.rgba').read_bytes(),(right/'scene.rgba').read_bytes(),1280,720)
    require(score>=config['image_ssim_minimum'] and score==recorded['repeat_ssim'],
            'Current repeated full frame or independently recomputed similarity differs')
    return dict(raw_trace_bytes_identical=True,complete_saved_content_identical=True,ssim=score)
