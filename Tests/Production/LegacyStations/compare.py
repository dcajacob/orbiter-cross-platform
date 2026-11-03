#!/usr/bin/env python3
"""Compare a complete native legacy-station profile with its pinned original."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path,PurePosixPath
import re
import subprocess

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('legacy_station_native',HERE/'native.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
legacy=native.legacy;ROOT=native.ROOT;require=native.require;digest=native.digest
from verify_original import compare_state
from behavior_suite import quaternion,quaternion_angle


def safe(name):
    path=PurePosixPath(name.replace('\\','/'))
    require(not path.is_absolute() and '..' not in path.parts and ':' not in str(path),'Unsafe native legacy artifact path')
    return path.as_posix()


def geometry(path):
    poses=legacy.rows(path/'camera.csv');require(len(poses)==1,'Incomplete native/original legacy camera')
    pose=poses[0]
    require(all(math.isfinite(float(v)) for v in pose.values()),'Nonfinite legacy camera')
    position=[float(pose[k]) for k in ('px','py','pz')]
    rotation=[[float(pose[f'm{i}{j}']) for j in range(1,4)] for i in range(1,4)]
    tangent=math.tan(float(pose['aperture']));require(tangent>0,'Invalid legacy field of view')
    landmarks={}
    for row in legacy.rows(path/'scene.csv'):
        delta=[float(row[k])-v for k,v in zip(('px','py','pz'),position)]
        view=[sum(rotation[i][j]*delta[i] for i in range(3)) for j in range(3)]
        if view[2]<=0:continue
        point=[640+360*view[0]/(view[2]*tangent),360-360*view[1]/(view[2]*tangent)]
        require(all(math.isfinite(v) for v in point),'Nonfinite projected legacy landmark')
        landmarks[row['object']]=point
    require(landmarks,'No front-facing original/native legacy landmarks')
    return pose,landmarks


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('original','original-audit','native','build-record','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--runtime-root',type=lambda v:Path(v).resolve(),default=ROOT)
    p.add_argument('--runtime-source-commit',required=True)
    a=p.parse_args();require(not a.output.exists(),'Native legacy comparison replacement forbidden')
    require(re.fullmatch('[0-9a-f]{40}',a.runtime_source_commit),'Native legacy runtime source must be immutable')
    config=legacy.settings();pins=json.loads((HERE/'observations.lock.json').read_text())
    require(pins['status']=='audited-original-observations','Full original legacy playback reference is not qualified')
    audit=json.loads(a.original_audit.read_text());report=json.loads((a.native/'capture.json').read_text())
    require(audit['status']=='passed' and audit['processes']==32 and len(audit['profiles'])==4 and
            audit['producer_commit']==pins['producer_commit'] and audit['application_source']==config['application_source'] and
            audit['verifier_sha256']==pins['audit_verifier_sha256']==digest(HERE/'audit_original.py'),
            'Complete independently audited original legacy reference required')
    require(report['status']=='captured-awaiting-original-comparison' and not report['failures'] and
            report['host']=='native-linux' and report['sources_and_binaries_unchanged'] and
            report['runtime_source_commit']==a.runtime_source_commit and
            set(report['cases'])=={case['id'] for case in config['cases']},'Native legacy profile failed or incomplete')
    identity=report['runtime_identity'];profile=identity['profile']
    require(profile==identity['configuration']+'-'+identity['math_profile'] and profile in pins['profiles'],
            'Native legacy profile misidentified')
    original=a.original/profile/'legacy-stations-original';old=json.loads((original/'capture.json').read_text())
    require(digest(original/'capture.json')==audit['profiles'][profile]['capture_sha256']==pins['profiles'][profile]['capture_sha256'],
            'Original legacy profile differs from audited pins')
    require(re.fullmatch('[0-9a-f]{40}',report['producer_commit']),'Native legacy producer must be immutable')
    folder=HERE.relative_to(ROOT).as_posix()
    tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',report['producer_commit'],'--',folder],text=True).splitlines()
    expected={name for name in tracked if str(PurePosixPath(name).parent)==folder}|set(native.PROTOCOL_SHARED)
    require(set(report['source_sha256_lf'])==expected,'Native legacy observer source manifest incomplete')
    for name,expected_sha in report['source_sha256_lf'].items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',report['producer_commit']+':'+safe(name)])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==expected_sha,'Native legacy producer source differs')
    for name in ('Tests/Production/LegacyStations/cases.json','Tests/Production/LegacyStations/original.py',
                 'Tests/Production/StockVessels/Observation.h'):
        require(report['source_sha256_lf'][name]==old['source_sha256_lf'][name],
                'Native/original legacy measurement schema or case differs')
    build=json.loads(a.build_record.read_text())
    require(build['status']=='built' and digest(a.build_record)==identity['build_record_sha256'],'Native legacy build record differs')
    owning=build.get('source_sha256_lf',build.get('source_sha256'))
    ledger=json.loads((ROOT/'Tests/Production/phase3-extraction.lock.json').read_text())['files']
    require(owning and set(owning)==set(ledger),'Native legacy owning-source build ledger incomplete')
    for name,expected_sha in owning.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',a.runtime_source_commit+':'+safe(name)])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==expected_sha,'Native legacy build input differs from runtime source')
    for name,expected_sha in build['runtime_files_sha256'].items():
        require(digest(a.runtime_root/safe(name))==expected_sha,'Retained native legacy runtime changed')
    marker='/Src/Orbiter/Production/NativeApplication.cpp'
    anchor=next(name for name in report['protected_files_sha256'] if name.endswith(marker))
    recorded_root=Path(anchor[:-len(marker)])
    for name,expected_sha in report['protected_files_sha256'].items():
        require(digest(a.runtime_root/Path(name).relative_to(recorded_root))==expected_sha,'Captured native legacy input changed: '+name)
    cache_name=next(name for name in build['runtime_files_sha256'] if name.endswith('/CMakeCache.txt'))
    cache=dict(line.split('=',1) for line in (a.runtime_root/cache_name).read_text().splitlines()
               if '=' in line and not line.startswith(('#','//')))
    require(cache['CMAKE_BUILD_TYPE:STRING']==identity['configuration'] and
            cache['ORBITER_MATH_FORCE_SSE2:BOOL']==('ON' if identity['math_profile']=='sse2' else 'OFF'),
            'Actual native legacy CMake configuration or math selection differs')
    flags=[cache['CMAKE_'+language+'_FLAGS:STRING'] for language in ('C','CXX')]
    sanitized=all('-fsanitize=address,undefined' in flag for flag in flags)
    require(sanitized==identity['sanitizer_linked'] and (sanitized or not any('-fsanitize=' in flag for flag in flags)),
            'Actual native legacy C/C++ instrumentation differs')
    executable=next(name for name in build['runtime_files_sha256'] if Path(name).name=='orbiter-production')
    linked=subprocess.check_output(['readelf','-d',str(a.runtime_root/executable)],text=True)
    require(('libasan.so' in linked)==sanitized and ('libubsan.so' in linked)==sanitized,'Native legacy sanitizer linkage differs')
    recorded_build=recorded_root/Path(executable).parent
    libraries=list(map(Path,report['private_library_directories']))
    result=dict(status='failed',phase6_complete=False,profile=profile,runtime_source_commit=a.runtime_source_commit,
        original_audit_sha256=digest(a.original_audit),original_capture_sha256=digest(original/'capture.json'),
        native_capture_sha256=digest(a.native/'capture.json'),source_sha256=digest(Path(__file__)),cases={})
    try:
        for case in config['cases']:
            rows=[]
            require(len(report['cases'][case['id']]['runs'])==2,'Native legacy repeats incomplete')
            for repeat in (1,2):
                left=original/(case['id']+'-'+str(repeat));right=a.native/(case['id']+'-'+str(repeat))
                for path,record in ((left,old),(right,report)):
                    captured=record['cases'][case['id']]['runs'][repeat-1]
                    for name,expected_sha in captured['files_sha256'].items():
                        require(digest(path/safe(name))==expected_sha,'Original/native legacy artifact changed')
                actual=native.inspect(right,case,config,identity,recorded_build,libraries)
                require(actual==report['cases'][case['id']]['runs'][repeat-1],'Recomputed native legacy outcome differs')
                errors=compare_state(left,right,config)
                poses,points=zip(*(geometry(path) for path in (left,right)))
                require(set(points[0])==set(points[1]),'Original/native legacy landmark identities differ')
                pixel_error=max(math.dist(points[0][name],points[1][name]) for name in points[0])
                camera_position=math.dist([float(poses[0][k]) for k in ('px','py','pz')],[float(poses[1][k]) for k in ('px','py','pz')])
                camera_rotation=quaternion_angle(quaternion(poses[0]),quaternion(poses[1]))
                require(pixel_error<=1 and camera_position<=config['budgets']['position_m'] and
                        camera_rotation<=config['budgets']['rotation_rad'] and
                        float(poses[0]['aperture'])==float(poses[1]['aperture']),
                        'Original/native legacy camera or projected landmarks exceed unchanged budgets')
                similarity=legacy.image_ssim((left/'scene.rgba').read_bytes(),(right/'scene.rgba').read_bytes(),1280,720)
                require(similarity>=config['image_ssim_minimum'],'Complete legacy framebuffer exceeds unchanged SSIM budget')
                rows.append(dict(maxima=errors,ssim=similarity,camera_position_m=camera_position,camera_rotation_rad=camera_rotation,
                    landmark_maximum_px=pixel_error,visible_landmarks=[name for name,point in points[0].items() if 0<=point[0]<1280 and 0<=point[1]<720]))
            result['cases'][case['id']]=dict(scenario=case['scenario'],runs=rows)
        result.update(status='passed',compared_processes=8,presentations=480,every_vessel_and_port=True,
                      full_frame_without_masks=True,frozen_budgets_unchanged=True)
    except BaseException as error:result['error']=str(error);raise
    finally:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(profile,'eight complete native legacy scenes match the original Windows profile')


if __name__=='__main__':main()
