#!/usr/bin/env python3
"""Independently audit all four complete 38-scene Windows observation profiles."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path,PurePosixPath,PureWindowsPath
import re
import stat
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('remaining_audit_original',HERE/'original.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
from verify_original import compare_state
from behavior_suite import quaternion,quaternion_angle
ROOT=original.ROOT;require=original.require;digest=original.digest;sha_lf=original.sha_lf
OBSERVER='Modules/Plugin/ProductionCockpitDriver.dll'


def safe(name):
    path=PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name,'Unsafe artifact path')
    return name


def verify_archive(path,root):
    seen=set()
    with zipfile.ZipFile(path) as source:
        for member in source.infolist():
            name=safe(member.filename)
            require(name not in seen and not stat.S_ISLNK(member.external_attr>>16),'Duplicate/symlink original archive member')
            seen.add(name)
            if member.is_dir():continue
            require((root/name).is_file() and digest(root/name)==hashlib.sha256(source.read(member)).hexdigest(),
                    'Extracted original member differs from the exact ZIP: '+name)
    require(seen,'Original archive is empty');return len(seen)


def producer_sources(report,producer):
    folder=HERE.relative_to(ROOT).as_posix()
    tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',producer,'--',folder],text=True).splitlines()
    own={name for name in tracked if str(PurePosixPath(name).parent)==folder}
    shared={p.relative_to(ROOT).as_posix() for p in original.source_files() if p.parent!=HERE}
    source=report['source_sha256_lf']
    require(set(source)==own|shared,'Original observer source closure incomplete')
    for name,value in source.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+safe(name)])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==value,'Producer source differs: '+name)
    for name in ('original.py','inputs.py','cases.json','Details.h','Driver.cpp','stage_original.py'):
        require(source[folder+'/'+name]==sha_lf(HERE/name),'Current observation reader/protocol differs from producer')
    return source


def audit_profile(root,profile,config,producer,preserved):
    capture=root/'remaining-stock-original';runtime=root/'remaining-stock-original-runtime'
    report=json.loads((capture/'capture.json').read_text());configuration,math_profile=profile.split('-',1)
    require(report['status']=='captured-awaiting-independent-audit' and report['host']=='original-windows' and
        report['protocol']==config['protocol'] and report['producer_commit']==producer and
        report['application_source']==config['application_source'] and report['configuration']==configuration and
        report['math_profile']==math_profile and report['settings_sha256_lf']==sha_lf(HERE/'cases.json') and
        report['preserved_runtime_unchanged'] and report['observer_sources_unchanged'] and not report['failures'] and
        set(report['cases'])=={c['id'] for c in config['cases']},'Original remaining-stock profile incomplete/misidentified')
    source=producer_sources(report,producer)
    for name in ('test-runtime.json','control-reference-runtime.json'):
        require(sha_lf(runtime/name)==sha_lf(preserved/name),'Independent retained original metadata differs')
    metadata=json.loads((runtime/'test-runtime.json').read_text());client=json.loads((runtime/'control-reference-runtime.json').read_text())
    require(metadata['source_commit']==client['application_source']==config['application_source'],'Original package source differs')
    protected={name:value for name,value in {**metadata['files'],**client['client_files_sha256']}.items() if name!=OBSERVER}
    require(protected==report['preserved_files_sha256'] and all(digest(preserved/safe(name))==value for name,value in protected.items()),
            'Retained application, SDK, configuration, meshes or client changed')
    observer=runtime/OBSERVER;require(digest(observer)==report['observer_sha256'],'Actual original observer DLL differs')
    build=root/'remaining-stock-driver'
    cache=dict(line.split('=',1) for line in (build/'CMakeCache.txt').read_text().splitlines() if '=' in line and not line.startswith(('#','//')))
    commands=json.loads((build/'compile_commands.json').read_text())
    require(cache['CMAKE_BUILD_TYPE:STRING']==configuration and len(commands)==1 and
        PureWindowsPath(commands[0]['file']).name=='Driver.cpp' and PureWindowsPath(commands[0]['file']).parent.name=='RemainingStock' and
        re.findall(r'(?:^|\s)[/-](MDd?)(?=\s|$)',commands[0]['command'])==['MDd' if configuration=='Debug' else 'MD'],
        'Actual observer build source/configuration/CRT differs')
    modules={}
    for name,value in {**protected,OBSERVER:report['observer_sha256']}.items():modules.setdefault(PurePosixPath(name).name.casefold(),set()).add(value)
    results={};maths=set()
    for case in config['cases']:
        recorded_case=report['cases'][case['id']];require(recorded_case['scenario']==case['scenario'] and len(recorded_case['runs'])==2,'Original scene repeat incomplete')
        paths=[];runs=[]
        for repeat,recorded in enumerate(recorded_case['runs'],1):
            out=capture/(case['id']+'-'+str(repeat));paths.append(out)
            for name,value in recorded['files_sha256'].items():require(digest(out/safe(name))==value,'Captured original bytes changed')
            actual=original.inspect_artifacts(out,case,config)
            require(all(recorded[key]==value for key,value in actual.items()),'Recomputed original result differs')
            invocation=json.loads((out/'invocation.json').read_text())
            expected_inputs={name:value for name,value in protected.items() if name.startswith(('Config/','Meshes/'))}
            require(invocation['preserved_inputs_sha256']==expected_inputs and
                all(invocation['input_sha256'][name]==value for name,value in expected_inputs.items()) and
                invocation['driver_sha256']==report['observer_sha256'],'Actual staged original inputs/observer differ')
            loaded={}
            trace={(line.strip().replace('\\','/').casefold()) for line in (out/'renderer-modules.txt').read_text().splitlines() if line.strip()}
            for item in recorded['loaded_modules']:
                path=item['path'].replace('\\','/');name=PurePosixPath(path).name.casefold()
                require(path.casefold() in trace and name in modules and item['sha256'] in modules[name],
                        'Actual original DLL identity differs')
                require(name not in loaded,'Duplicate original DLL identity');loaded[name]=item['sha256']
            required={'orbiter.exe','oglclient.dll','productioncockpitdriver.dll'}
            required|={PurePosixPath(config['classes'][kind]['original_module']).name.casefold()
                       for kind in set(case['declared_vessels'].values()) if config['classes'][kind]['module']}
            require(required<=set(loaded),'Original declared factory/application/client/observer not actually loaded')
            require(math_profile!='sse2' or actual['actual_math']=='sse2','Actual original math profile differs')
            maths.add(actual['actual_math']);runs.append({key:value for key,value in actual.items() if key not in ('files_sha256','renderer')})
        for name in (*original.TRACES,'camera.csv'):
            require((paths[0]/name).read_bytes()==(paths[1]/name).read_bytes(),'Original repeated trace or camera differs')
        score=original.image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
        require(score>=config['image_ssim_minimum'] and score==recorded_case['repeat_ssim'],'Original repeated full-frame gate failed')
        results[case['id']]=dict(scenario=case['scenario'],runs=runs,repeat_ssim=score)
    require(len(maths)==1,'Original actual math implementation changed across scenes')
    controls=json.loads((capture/'gate-control.json').read_text())
    names={'missing_background_vessel','missing_thruster','missing_tank','unknown_tank_owner','missing_attachment',
        'missing_mesh_slot','false_initial_playback','missing_position_recording','wrong_windows_entry_point',
        'changed_class_input','shifted_clock','missing_population_tick','missing_mesh_delivery_repair',
        'changed_mesh_delivery_provenance','live_resource_marked_retired','retired_resource_marked_live',
        'forged_retired_resource_seen_tick','missing_retired_resource_witness'}
    require(controls['status']=='passed' and controls['original_capture_unchanged'] and
        len(controls['controls'])==18 and {row['control'] for row in controls['controls']}==names,'Original detail controls incomplete')
    gate=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+HERE.relative_to(ROOT).as_posix()+'/Gate.Test.py']).replace(b'\r\n',b'\n')
    require(controls['source_sha256'] in {hashlib.sha256(gate).hexdigest(),hashlib.sha256(gate.replace(b'\n',b'\r\n')).hexdigest()},'Original control producer differs')
    require(controls['positive']==original.inspect_artifacts(capture/'remaining_stock_003-1',config['cases'][2],config),
            'Original control positive capture differs')
    require(controls['retired_positive']==original.inspect_artifacts(capture/'remaining_stock_001-1',config['cases'][0],config) and
            controls['retired_positive']['retired_resource_bindings']>0,'Original retired-resource control positive differs')
    return dict(capture_sha256=digest(capture/'capture.json'),observer_sha256=digest(observer),actual_math=next(iter(maths)),
        runtime_metadata_sha256_lf=sha_lf(runtime/'test-runtime.json'),client_metadata_sha256_lf=sha_lf(runtime/'control-reference-runtime.json'),
        source_manifest_sha256=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),
        gate_sha256=digest(capture/'gate-control.json'),cases=results)


def detail_calibration(left,right):
    identities={'tick','object','index','to_parent','id','attached','resource_object','resource_index','resource_state',
                'resource_id','resource_seen_tick','present','template','name','visibility','playback','count'}
    maxima={}
    for name in original.TRACES[2:]:
        a=original.rows(left/name);b=original.rows(right/name)
        require(len(a)==len(b),'Original detail calibration row count differs')
        for x,y in zip(a,b):
            require(x.keys()==y.keys() and all(x[key]==y[key] for key in x if key in identities),
                    'Original detail calibration object/resource/mesh identity differs')
            for key in x:
                if key not in identities:maxima[name+':'+key]=max(maxima.get(name+':'+key,0),abs(float(x[key])-float(y[key])))
    return maxima


def camera_comparison(left,right,config):
    records=[original.rows(path/'camera.csv') for path in (left,right)]
    require(all(len(rows)==1 for rows in records),'Original camera observation incomplete')
    a,b=[rows[0] for rows in records]
    require(all(math.isfinite(float(v)) for row in (a,b) for v in row.values()),'Nonfinite original camera')
    position=math.dist([float(a[k]) for k in ('px','py','pz')],[float(b[k]) for k in ('px','py','pz')])
    rotation=quaternion_angle(quaternion(a),quaternion(b))
    require(position<=config['budgets']['position_m'] and rotation<=config['budgets']['rotation_rad'] and
            float(a['aperture'])==float(b['aperture']),'Original paired camera exceeds unchanged budgets')
    return dict(position_m=position,rotation_rad=rotation,byte_identical=(left/'camera.csv').read_bytes()==(right/'camera.csv').read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('artifacts','download-manifest','preserved-debug','preserved-release','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--producer-commit',required=True);a=p.parse_args();config=original.settings()
    require(not a.output.exists() and re.fullmatch('[0-9a-f]{40}',a.producer_commit),'Fresh output and immutable producer required')
    downloads=json.loads(a.download_manifest.read_text());profiles={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')}
    require(downloads['status']=='passed' and downloads['source_commit']==a.producer_commit and len(downloads['artifacts'])==4 and
        {item['profile'] for item in downloads['artifacts']}==profiles,'Full original profile transport matrix incomplete')
    result=dict(status='failed',phase6_complete=False,native_admission_qualified=False,producer_commit=a.producer_commit,
        application_source=config['application_source'],verifier_sha256=digest(Path(__file__)),profiles={},build_pairs={})
    try:
        for profile in sorted(profiles):
            item=next(v for v in downloads['artifacts'] if v['profile']==profile);archive=ROOT/safe(item['path'])
            require(item['name']=='original-remaining-stock-'+profile and archive.stat().st_size==item['bytes'] and digest(archive)==item['sha256'],
                    'Exact original archive transport differs')
            count=verify_archive(archive,a.artifacts/profile)
            result['profiles'][profile]=audit_profile(a.artifacts/profile,profile,config,a.producer_commit,
                a.preserved_debug if profile.startswith('Debug-') else a.preserved_release)
            result['profiles'][profile].update(archive_sha256=item['sha256'],archive_members_verified=count)
        for math_profile in ('automatic','sse2'):
            pairs={}
            require(result['profiles']['Debug-'+math_profile]['actual_math']==result['profiles']['Release-'+math_profile]['actual_math'],
                    'Original paired configurations select different actual math')
            for case in config['cases']:
                paths=[a.artifacts/(kind+'-'+math_profile)/'remaining-stock-original'/(case['id']+'-1') for kind in ('Debug','Release')]
                errors=compare_state(*paths,config);detail=detail_calibration(*paths);camera=camera_comparison(*paths,config)
                score=original.image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
                require(score>=config['image_ssim_minimum'],'Original paired full-frame gate failed')
                pairs[case['id']]=dict(maxima=errors,ssim=score,camera=camera,detail_numeric_calibration_only=detail)
            result['build_pairs'][math_profile]=pairs
        runs=[run for profile in result['profiles'].values() for case in profile['cases'].values() for run in case['runs']]
        require(len(runs)==304,'Original complete process matrix incomplete')
        result.update(status='passed',processes=len(runs),presentations=60*len(runs),
            all_vessel_rows=sum(r['all_vessel_rows'] for r in runs),docking_rows=sum(r['docking_rows'] for r in runs),
            attachment_rows=sum(r['attachment_rows'] for r in runs),thruster_rows=sum(r['thruster_rows'] for r in runs),
            propellant_rows=sum(r['propellant_rows'] for r in runs),mesh_rows=sum(r['mesh_rows'] for r in runs))
        result.update(retired_resource_bindings=sum(r['retired_resource_bindings'] for r in runs),
            retired_resource_nonzero_levels=sum(r['retired_resource_nonzero_levels'] for r in runs),
            retired_resource_scope='Inherited original sampled handle-lifetime evidence; no native lifetime waiver or admission')
    except BaseException as error:result['error']=str(error);raise
    finally:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('status','processes','presentations','all_vessel_rows','attachment_rows','thruster_rows')}))


if __name__=='__main__':main()
