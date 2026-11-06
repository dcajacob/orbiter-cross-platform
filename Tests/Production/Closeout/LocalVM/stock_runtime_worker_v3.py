"""Capture declared current-Windows stock writers and the exact paired Windows saves."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

from win_local_process_v1 import context
from runtime_descriptor_v3 import preflight,require,sha
from static_binary_link_staging_v1 import BinaryLinks
from current_stock import selection,inspect_run


def load(path):return json.loads(Path(path).read_text())
def lfsha(path):return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def main():
    request=Path(sys.argv[1]);cfg=load(request);share=request.parent;source=Path(cfg['source']);output=Path(cfg['output'])
    report=dict(status='running',source=cfg['source_commit'],configuration=cfg['configuration'],math_profile=cfg['math_profile'],
        roles=cfg['roles'],transport_protocol=cfg['transport_protocol'],context=context(),request_sha256=sha(request),
        script_sha256=sha(__file__),cloud_builds_used=False,native_admission_qualified=False,phase6_complete=False,
        cases={},actual_process_receipts=[])
    links=None
    def save():
        temporary=share/'worker-result.tmp';temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(share/'worker-result.json')
    def export_run(folder,target):
        target.mkdir()
        paths=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower() not in ('.exe','.dll')]
        paths.extend(p for sub in ('Scenarios','Flights') for p in (folder/sub).rglob('*') if p.is_file())
        for path in paths:
            destination=target/path.relative_to(folder);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
    try:
        require(report['context']==dict(session=cfg['active_session'],window_station='WinSta0',desktop=cfg['desktop']), 'Actual private desktop differs')
        report['root_preflight']=preflight(cfg)
        os.environ.update(PATH=str(Path(cfg['git']).parent)+';'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1',
                          LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
        require(cfg['cohort']=='current-windows' and cfg['source_role']=='application', 'Actual current application source role required')
        require(sha(cfg['application_build_manifest'])==cfg['application_build_manifest_sha256'], 'Current application build record differs')
        built=load(cfg['application_build_manifest']);item=built['configurations'][cfg['configuration']];runtime=Path(cfg['preserved'])
        require(built['source_commit']==cfg['source_commit'] and built['owning_sources_unchanged'] is True and item['status']=='built' and
                Path(item['runtime'])==runtime, 'Actual current application/SDK package differs')
        require(all(cfg['roles'][r]['manifest_sha256']==item['sdk_manifest_sha256'] and
                    Path(cfg['roles'][r]['manifest_path'])==runtime/'test-runtime.json' for r in ('application','sdk')),
                'Current application/SDK roles name another package')
        require(subprocess.check_output([cfg['git'],'-C',source,'rev-parse','HEAD'],text=True).strip()==cfg['source_commit'], 'Actual application source differs')
        source_guards=built['source_guard_sha256_lf']
        require(all(lfsha(source/name)==value for name,value in source_guards.items()), 'Owning current application source changed')
        guards={str(runtime/name):value for name,value in item['runtime_files_sha256'].items()}
        observer_build=load(cfg['roles']['observer']['manifest_path']);observer=observer_build['observer']
        require(observer_build['status']=='prepared-passive-observer-only' and observer['kind']=='remaining-stock' and
                observer['sdk_source_commit']==cfg['source_commit'] and observer['source_commit']==cfg['roles']['observer']['commit'] and
                observer['configuration']==cfg['configuration'] and observer_build['sdk']['manifest_sha256']==item['sdk_manifest_sha256'] and
                sha(observer['binary'])==observer['sha256'], 'Stock observer was not built against this exact current SDK')
        guards[observer['binary']]=observer['sha256']
        provider=load(Path(cfg['mesa'])/'mesa-runtime.json')
        guards.update({str(Path(cfg['mesa'])/name):value['sha256'] for name,value in provider['files'].items()})
        require(all(sha(path)==value for path,value in guards.items()), 'Actual current runtime/observer/provider bytes differ')
        sys.path[:0]=[str(source/'Tests/Production/RemainingStockRepaired'),str(source/'Tests/Production/RemainingStockPersistence'),
                      str(source/'Tests/Production/RemainingStock'),str(source/'Tests/Production/Client'),str(source/'Tests/Production')]
        import capture as reader
        from saved_inputs import derived_case
        from saved_state import parse_saved,content_differences
        config=reader.settings(reader.protocols.V2);cases,diagnostic=selection(cfg,config)
        actual_data=reader.data_inputs.inspect(Path(cfg['data']),Path(cfg['planets']))
        report.update(diagnostic_only=diagnostic,cases_requested=[case['id'] for case in cases],repeats=2,frames=960,
                      observer_build_sha256=sha(cfg['roles']['observer']['manifest_path']),actual_simulation_data=actual_data)
        expected_inputs={(mode,case['id'],repeat) for mode in ('automatic','sse2') for case in cases for repeat in (1,2)}
        supplied={(item['math_profile'],item['case'],item['repeat']) for item in cfg['windows_save_inputs']}
        require(len(cfg['windows_save_inputs'])==len(supplied) and supplied==expected_inputs, 'Every exact paired Windows save required')
        inputs={}
        for value in cfg['windows_save_inputs']:
            path=Path(value['path']);require(sha(path)==value['sha256'], 'Exact Windows save input changed')
            inputs[(value['math_profile'],value['case'],value['repeat'])]=value;guards[str(path)]=value['sha256']
        output.mkdir();export=Path(cfg['export']);export.mkdir();links=BinaryLinks(guards,output);links.install();save()
        expected_modules={}
        for path,value in guards.items():expected_modules.setdefault(Path(path).name.casefold(),set()).add(value)
        for mode in ('automatic','sse2'):
            if mode=='sse2':os.environ['ORBITER_TEST_OBSERVER_SSE2']='1'
            else:os.environ.pop('ORBITER_TEST_OBSERVER_SSE2',None)
            for phase in ('stock','reload'):
                parent=output/(mode+'-'+phase);parent.mkdir();destination=export/parent.name;destination.mkdir()
                for case in cases:
                    runs=[];folders=[]
                    for repeat in (1,2):
                        folder=parent/(case['id']+'-'+str(repeat));folders.append(folder)
                        value=inputs[(mode,case['id'],repeat)];saved=Path(value['path'])
                        executed,provenance=derived_case(case,config,saved,value['sha256']) if phase=='reload' else (case,None)
                        def configure(directory):
                            target=directory/'Orbiter.cfg';text=target.read_text()
                            for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                                require(text.count(line)==1,'Original propagation fixture changed');text=text.replace(line,'')
                            target.write_text(text.replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+
                                '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                            target=directory/executed['scenario_entry_point'];target.parent.mkdir(parents=True,exist_ok=True)
                            target.write_bytes(saved.read_bytes() if phase=='reload' else (source/case['scenario_entry_point']).read_bytes())
                            require(lfsha(target)==executed['sha256_lf'], 'Unchanged scene/exact saved input differs')
                            target=directory/'Modules/Plugin/ProductionCockpitDriver.dll'
                            target.unlink(missing_ok=True)  # The staged original may share its immutable file record.
                            shutil.copy2(observer['binary'],target)
                            (directory/'current-runtime-variant.json').write_text(json.dumps(dict(cohort='current-windows',roles=cfg['roles'],
                                configuration=cfg['configuration'],math_profile=mode,phase=phase,case=case['id'],repeat=repeat,
                                paired_windows_input=value if phase=='reload' else None),indent=2)+'\n')
                            (directory/reader.protocols.MARKER).write_bytes(reader.protocols.marker_bytes(config))
                            (directory/'ogl-evidence.enabled').touch();reader.mesa_files(Path(cfg['mesa']),directory)
                        try:
                            reader.stage(runtime/'Orbiter.exe',Path(cfg['data']),Path(cfg['planets']),folder,config,executed,configure,process_timeout=900)
                            staged_data=reader.data_inputs.inspect(folder,folder)
                            require(staged_data==actual_data, 'Actual staged simulation data differs from the locked Windows inputs')
                            (folder/'actual-data-inputs.json').write_text(json.dumps(staged_data,indent=2)+'\n')
                            result=inspect_run(folder,executed,config,reader,cfg['source_commit'],source)
                            require(result['actual_math']==('sse2' if mode=='sse2' else 'fma3'), 'Actual current CRT mode differs')
                            result['loaded_modules']=reader.shared.shared.loaded_modules(folder,expected_modules)
                            require([module['sha256'] for module in result['loaded_modules']
                                     if Path(module['path']).name.casefold()=='productioncockpitdriver.dll']==[observer['sha256']],
                                    'Actual loaded current-SDK stock observer differs')
                            loaded={Path(item['path']).name.casefold() for item in result['loaded_modules']}
                            required={'orbiter.exe','oglclient.dll','productioncockpitdriver.dll'}|{
                                Path(config['classes'][kind]['original_module']).name.casefold()
                                for kind in set(executed['declared_vessels'].values()) if config['classes'][kind]['module']}
                            require(required<=loaded, 'Required current vessel factory/client/application/observer not mapped')
                            result.update(executed_case=executed,persistence_input=provenance,saved_state=parse_saved(folder/'Scenarios/(Current state).scn'))
                            timing=load(folder/'process-timing.json')
                            report['actual_process_receipts'].append(dict(math_profile=mode,phase=phase,case=case['id'],repeat=repeat,
                                                                        folder=str(folder),timing=timing))
                            runs.append(result)
                        finally:
                            if folder.is_dir():export_run(folder,destination/folder.name)
                            report['export_files_sha256']={p.relative_to(export).as_posix():sha(p) for p in export.rglob('*') if p.is_file()};save()
                    for name in (*reader.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv'):
                        require((folders[0]/name).read_bytes()==(folders[1]/name).read_bytes(), 'Current repeated trace differs: '+name)
                    require(not content_differences(runs[0]['saved_state'],runs[1]['saved_state']), 'Current repeated complete saved content differs')
                    score=reader.image_ssim((folders[0]/'scene.rgba').read_bytes(),(folders[1]/'scene.rgba').read_bytes(),1280,720)
                    require(score>=config['image_ssim_minimum'], 'Current repeated full frame exceeds existing image budget')
                    report['cases'][mode+'-'+phase+'-'+case['id']]=dict(runs=runs,repeat_ssim=score);save()
        require(all(sha(path)==value for path,value in guards.items()) and all(lfsha(source/name)==value for name,value in source_guards.items()),
                'Owning current sources/runtime/SDK/provider/paired saves changed')
        require(reader.data_inputs.inspect(Path(cfg['data']),Path(cfg['planets']))==actual_data, 'Owning simulation data changed')
        links.close()
        report.update(status='captured-current-Windows-stock-and-paired-exact-save-reloads',actual_processes=len(report['actual_process_receipts']),
                      successful_presents=960*len(report['actual_process_receipts']),owning_sources_runtime_sdk_provider_and_saved_inputs_unchanged=True,
                      simulation_comparison_and_independent_audit_pending=True)
    except BaseException as error:
        report.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
    finally:
        if links:links.close()
        save()


if __name__=='__main__':main()
