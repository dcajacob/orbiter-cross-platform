#!/usr/bin/env python3
"""Reload every exact Windows end save in the repaired original application/SDK."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'RemainingStockRepaired'))
import capture as original
import protocols
from saved_inputs import derived_case,protocol
from saved_state import parse_saved,content_differences,require

spec=importlib.util.spec_from_file_location('persistence_original_auditor',HERE.parent/'RemainingStockRepaired/audit.py')
independent=importlib.util.module_from_spec(spec);spec.loader.exec_module(independent)
sha=original.sha;sha_lf=original.sha_lf
from execution import collect,worker_count
CURRENT='Scenarios/(Current state).scn'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent-capture','build','preserved','data','planets','mesa','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--math-profile',choices=('automatic','sse2'),required=True)
    p.add_argument('--workers',type=worker_count,default=1,help='Independent scene processes (1-4); each scene retains both serial repetitions')
    p.add_argument('--diagnostic-case',action='append')
    a=p.parse_args();contract=protocol();config=original.settings(protocols.V2)
    require(sys.platform=='win32','Original persistence observations require native Windows')
    require(not a.output.exists(),'Fresh persistence capture required; replacement forbidden')
    require((os.environ.get('ORBITER_TEST_OBSERVER_SSE2')=='1')==(a.math_profile=='sse2'),'Actual original CRT selection differs')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    cases=original.selected_cases(config,a.diagnostic_case);diagnostic=a.diagnostic_case is not None
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    build=json.loads((a.build/'build.json').read_text())
    require(build['producer_commit']==producer and build['protocol']==protocols.V2,'Build and reload producers/protocols differ')
    checked_build,runtime=independent.runtime_variant(a.build,producer,a.configuration,a.preserved,protocols.V2)
    require(checked_build==build,'Independently read build manifest differs')
    staged=json.loads((a.build/'module-sources/source-variant.json').read_text())
    require(staged['protocol']=='remaining-stock-repaired-sources-v4','Fresh persistence requires the declared ADI request and complete gauge-storage repairs')
    parent_file=a.parent_capture/'capture.json';parent=json.loads(parent_file.read_text())
    require(parent['producer_commit']==producer and parent['protocol']==protocols.V2 and
            parent['status'] in ('captured-diagnostic-only','captured-awaiting-independent-audit') and not parent['failures'] and
            parent['configuration']==a.configuration and parent['math_profile']==a.math_profile and
            {c['id'] for c in cases}<=set(parent['cases']),'Completed matching original Windows parent captures required')
    if not diagnostic:
        require(not parent['diagnostic_only'] and len(parent['cases'])==contract['complete_scenes'],'Full persistence requires all 38 original parent scenes')
    original_data=original.data_inputs.inspect(a.data,a.planets)
    require(original_data==parent['actual_original_simulation_data'],'Actual original data differs from parent')
    paths=set(original.source_files())|{x for x in HERE.iterdir() if x.is_file()}
    paths.add(Path(independent.__file__))
    sources={path.relative_to(ROOT).as_posix():sha(path) for path in paths}
    for name in sources:
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==sha_lf(ROOT/name),'Persistence reader differs from committed producer: '+name)
    guarded={str(parent_file):sha(parent_file),str(a.build/'build.json'):sha(a.build/'build.json')}
    expected={}
    for name,value in build['runtime_files_sha256'].items():expected.setdefault(Path(name).name.casefold(),set()).add(value)
    a.output.mkdir(parents=True)
    report=dict(status='running',protocol=contract['protocol'],host='repaired-original-windows',producer_commit=producer,
        original_application_and_sdk_source=config['application_source'],configuration=a.configuration,math_profile=a.math_profile,
        execution=dict(workers=a.workers,process_timeout_seconds=900,scene_repetitions='serial',aggregate_writes='main-thread'),
        diagnostic_only=diagnostic,cases_requested=[c['id'] for c in cases],source_raw_sha256=sources,
        parent_capture_sha256=sha(parent_file),independently_checked_runtime=runtime,actual_original_data=original_data,
        cases={},failures={},native_admission_qualified=False,phase6_complete=False)
    manifest=a.output/'capture.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    case_guards={case['id']:{} for case in cases}
    try:
        def observe(case):
            results=[];directories=[];case_guarded=case_guards[case['id']]
            require(len(parent['cases'][case['id']]['runs'])==2,'Both original parent repetitions required')
            for repeat in (1,2):
                parent_dir=a.parent_capture/(case['id']+'-'+str(repeat))
                previous=parent['cases'][case['id']]['runs'][repeat-1]
                require(all(sha(parent_dir/n)==v for n,v in previous['files_sha256'].items()),'Actual parent observation bytes changed')
                case_guarded.update({str(parent_dir/n):v for n,v in previous['files_sha256'].items()})
                parent_result=original.inspect_artifacts(parent_dir,case,config)
                require('configuration_input' in parent_result,'Fresh Windows reload requires the actual parent startup configuration witness')
                saved=parent_dir/CURRENT
                checksum=sha(saved);derived,provenance=derived_case(case,config,saved,checksum);case_guarded[str(saved)]=checksum
                provenance.update(parent_capture_sha256=sha(parent_file),parent_run=case['id']+'-'+str(repeat),
                    parent_finalized_clock=parent_result['matched_clock_observation'],parent_run_files_sha256=previous['files_sha256'])
                out=a.output/(case['id']+'-'+str(repeat));directories.append(out)
                def configure(directory):
                    cfg=directory/'Orbiter.cfg';text=cfg.read_text()
                    for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                        require(text.count(line)==1,'Original propagator fixture differs');text=text.replace(line,'')
                    cfg.write_text(text.replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+
                        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                    target=directory/derived['scenario_entry_point'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(saved.read_bytes())
                    require(sha(target)==provenance['saved_input_sha256'],'Derived save copy differs')
                    (directory/'persistence-input.json').write_text(json.dumps(provenance,indent=2)+'\n')
                    variant=dict(protocol=config['protocol'],protocol_sha256_lf=sha_lf(protocols.path(protocols.V2)),
                        original_application_and_sdk_source=config['application_source'],producer_commit=producer,
                        runtime_variant_manifest_sha256=sha(a.build/'runtime/runtime-variant.json'),frames=config['frames'],
                        fixed_step=config['fixed_step'],capture_tick=config['capture_tick'],diagnostic_only=diagnostic,
                        cases_requested=[c['id'] for c in cases])
                    (directory/'reference-variant.json').write_text(json.dumps(variant,indent=2)+'\n')
                    (directory/protocols.MARKER).write_bytes(protocols.marker_bytes(config))
                    (directory/'ogl-evidence.enabled').touch();original.mesa_files(a.mesa,directory)
                original.stage(a.build/'runtime/Orbiter.exe',a.data,a.planets,out,config,derived,configure,process_timeout=900)
                staged_data=original.data_inputs.inspect(out,out)
                require(staged_data==original_data,'Reload staged original simulation data differs')
                (out/'actual-data-inputs.json').write_text(json.dumps(staged_data,indent=2)+'\n')
                require(all(sha(out/n)==v for n,v in build['runtime_files_sha256'].items() if n.lower().endswith(('.dll','.exe'))),'Executed reload module bytes differ')
                result=original.inspect_artifacts(out,derived,config)
                result['loaded_modules']=original.shared.shared.loaded_modules(out,expected)
                loaded={Path(item['path'].replace('\\','/')).name.casefold() for item in result['loaded_modules']}
                required={'orbiter.exe','oglclient.dll','productioncockpitdriver.dll'}
                required|={Path(config['classes'][kind]['original_module']).name.casefold()
                           for kind in set(derived['declared_vessels'].values()) if config['classes'][kind]['module']}
                require(required<=loaded,'Required saved-vessel factory/application/client/observer not mapped')
                require(a.math_profile!='sse2' or result['actual_math']=='sse2','Executed reload CRT differs')
                end=parse_saved(out/CURRENT)
                result.update(derived_case=derived,persistence_input=provenance,saved_state=end,
                    saved_content_changes=content_differences(parse_saved(saved),end,contract['operator_description_blocks']))
                result['files_sha256'].update({n:sha(out/n) for n in (CURRENT,'persistence-input.json')})
                results.append(result);original.png(out/'scene.png',(out/'scene.rgba').read_bytes(),1280,720)
            for name in (*original.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv'):
                require((directories[0]/name).read_bytes()==(directories[1]/name).read_bytes(),'Original repeated reload trace differs: '+name)
            require(not content_differences(results[0]['saved_state'],results[1]['saved_state']),'Original repeated reload saved content differs')
            similarity=original.image_ssim((directories[0]/'scene.rgba').read_bytes(),(directories[1]/'scene.rgba').read_bytes(),1280,720)
            require(similarity>=config['image_ssim_minimum'],'Original repeated reload exceeds unchanged full-frame budget')
            return dict(runs=results,repeat_ssim=similarity)
        def record(case,result,error):
            guarded.update(case_guards[case['id']])
            if error is None:
                report['cases'][case['id']]=result
                print(case['id'],'exact Windows saves reloaded twice',flush=True)
            else:
                report['failures'][case['id']]=str(error);print(case['id'],'reload failed:',error,flush=True)
            save()
        collect(cases,a.workers,observe,record)
        require(all(sha(a.build/'runtime'/n)==v for n,v in build['runtime_files_sha256'].items()),'Owning runtime bytes changed')
        require(sources=={n:sha(ROOT/n) for n in sources} and all(sha(Path(n))==v for n,v in guarded.items()),'Owning readers/parent observations/saved inputs changed')
        require(original.data_inputs.inspect(a.data,a.planets)==original_data,'Owning actual original data changed')
        complete=len(report['cases'])==len(cases) and not report['failures']
        report.update(status=('captured-diagnostic-only' if diagnostic else 'captured-awaiting-independent-persistence-audit') if complete else 'incomplete',
            owning_sources_runtime_parent_saved_inputs_and_data_unchanged=True,guarded_parent_files_sha256=guarded,
            scope='Every actual vessel and module field retained in exact hashed Windows save inputs. Original Windows writer/reload candidate only; native writer/reload comparison, measured serialization round trips, controls, lifetime and complete Phase 6 acceptance remain required.')
        save();require(complete,'Original persistence reload failures retained; no admission')
    except BaseException as error:
        report.update(status='failed',error=str(error));raise
    finally:save()


if __name__=='__main__':main()
