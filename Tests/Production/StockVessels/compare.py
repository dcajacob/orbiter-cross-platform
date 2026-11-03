#!/usr/bin/env python3
"""Compare every native vessel, station capability, camera and complete framebuffer."""
import argparse
import json
import math
from pathlib import Path
import sys

from original import HERE,ROOT,digest,image_ssim,require,rows,settings,source_digest
# The original capture helper also imports cockpit tooling. Select this
# fixture's native observer rather than the separate Cockpit/native.py.
sys.path.insert(0,str(HERE))
from native import inspect
from verify_original import compare_state
from behavior_suite import quaternion,quaternion_angle


def geometry(path):
    camera=rows(path/'camera.csv');require(len(camera)==1,'Incomplete finalized stock camera')
    camera=camera[0]
    require(all(math.isfinite(float(v)) for v in camera.values()),'Nonfinite stock camera')
    p=[float(camera[k]) for k in ('px','py','pz')]
    r=[[float(camera[f'm{i}{j}']) for j in range(1,4)] for i in range(1,4)]
    tangent=math.tan(float(camera['aperture']));require(tangent>0,'Invalid stock field of view')
    landmarks={}
    for row in rows(path/'scene.csv'):
        delta=[float(row[k])-v for k,v in zip(('px','py','pz'),p)]
        view=[sum(r[i][j]*delta[i] for i in range(3)) for j in range(3)]
        if view[2]<=0:continue
        point=[640+360*view[0]/(view[2]*tangent),360-360*view[1]/(view[2]*tangent)]
        landmarks[row['object']]=point
    require(landmarks,'No front-facing engine-object projections in complete stock scene')
    return camera,landmarks


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('original','native','reference-audit','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'Stock comparison output exists')
    config=settings();original=json.loads((a.original/'stock-vessels.json').read_text())
    native=json.loads((a.native/'stock-vessels.json').read_text())
    audit=json.loads(a.reference_audit.read_text());names={c['id'] for c in config['cases']}
    require(audit['status']=='passed' and original['status']==native['status']=='passed' and
            not original['failures'] and not native['failures'] and set(original['cases'])==set(native['cases'])==names,
            'Failed or incomplete original/native station matrix')
    require((original['configuration'],original['math_profile'])==(native['configuration'],native['math_profile']),
            'Original/native station build or numerical profiles differ')
    profile=original['configuration']+'-'+original['math_profile']
    require(audit['profiles'][profile]['capture_sha256']==digest(a.original/'stock-vessels.json') and
            original['settings_sha256_lf']==native['settings_sha256_lf']==source_digest(HERE/'cases.json') and
            original['source_sha256_lf']['Observation.h']==source_digest(HERE/'Observation.h'),
            'Audited original station source/protocol differs')
    for name,checksum in native['source_sha256'].items():
        require(digest(ROOT/name)==checksum,'Native station observer/source changed: '+name)
    for name,checksum in native['runtime_files_sha256'].items():
        require(digest(ROOT/name)==checksum,'Native station runtime library/module changed: '+name)
    result=dict(status='failed',phase6_complete=False,profile=profile,cases={},
        original_report_sha256=digest(a.original/'stock-vessels.json'),native_report_sha256=digest(a.native/'stock-vessels.json'),
        reference_audit_sha256=digest(a.reference_audit),source_sha256_lf=source_digest(Path(__file__)))
    try:
        for case in config['cases']:
            compared=[]
            for repeat in (1,2):
                paths=[base/(case['id']+'-'+str(repeat)) for base in (a.original,a.native)]
                for path,record in zip(paths,(original,native)):
                    recorded=record['cases'][case['id']]['runs'][repeat-1]
                    for name,checksum in recorded['files_sha256'].items():
                        require(digest(path/name)==checksum,'Stock comparison input artifact changed: '+str(path/name))
                    if path==paths[1]:
                        recomputed=inspect(path,case,config)
                        require(recorded==recomputed,'Recomputed native stock outcome differs')
                errors=compare_state(*paths,config)
                poses,points=zip(*(geometry(path) for path in paths))
                require(set(points[0])==set(points[1]),'Original/native front-facing stock landmarks differ')
                pixel_error=max(math.dist(points[0][name],points[1][name]) for name in points[0])
                require(pixel_error<=1,'Complete stock scene landmark exceeds unchanged one-pixel budget')
                camera_position=math.dist([float(poses[0][k]) for k in ('px','py','pz')],
                                          [float(poses[1][k]) for k in ('px','py','pz')])
                camera_rotation=quaternion_angle(quaternion(poses[0]),quaternion(poses[1]))
                require(camera_position<=config['budgets']['position_m'] and
                        camera_rotation<=config['budgets']['rotation_rad'] and
                        float(poses[0]['aperture'])==float(poses[1]['aperture']),
                        'Actual original/native stock camera exceeds unchanged budgets')
                similarity=image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
                require(similarity>=config['image_ssim_minimum'],'Complete stock framebuffer exceeds unchanged SSIM budget')
                compared.append(dict(maxima=errors,ssim=similarity,landmark_maximum_px=pixel_error,
                    camera_position_m=camera_position,camera_rotation_rad=camera_rotation,
                    projected_landmarks=list(points[0]),
                    visible_landmarks=[name for name,point in points[0].items() if 0<=point[0]<1280 and 0<=point[1]<720]))
            result['cases'][case['id']]=dict(scenario=case['scenario'],repetitions=compared)
        result.update(status='passed',compared_processes=14,compared_scene_presents=840,
                      every_declared_vessel_and_docking_port=True,full_frame_without_masks=True,
                      frozen_references_and_budgets_unchanged=True)
    except BaseException as error:
        result['error']=str(error);raise
    finally:a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','profile','compared_processes','compared_scene_presents')}))


if __name__=='__main__':main()
