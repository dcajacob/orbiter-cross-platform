#!/usr/bin/env python3
"""Audit preserved Windows station artifacts before native capability changes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from original import select_suite,settings_path
from original import HERE,ROOT,digest,image_ssim,inspect_trace,require,rows,settings,source_digest
from behavior_suite import quaternion,quaternion_angle


def compare_state(left,right,config):
    a={(r['tick'],r['object']):r for r in rows(left/'stock-vessel-state.csv')}
    b={(r['tick'],r['object']):r for r in rows(right/'stock-vessel-state.csv')}
    require(set(a)==set(b),'Original build-pair vessel/tick identities differ')
    maxima=dict.fromkeys(('position_m','velocity_m_s','rotation_rad','angular_velocity_rad_s','mjd_days',
                         'mass_fraction_of_budget','fuel_fraction_of_budget'),0.)
    exact=('class','version','focus','enable_focus','meshes','thrusters','propellants','docks','parents','children','xpdr')
    capabilities=('empty_mass','size','pmix','pmiy','pmiz','csx','csy','csz')
    for key,ref in a.items():
        got=b[key]
        require(all(ref[k]==got[k] for k in exact) and
                all(float(ref[k])==float(got[k]) for k in capabilities),'Paired stock capabilities differ: '+str(key))
        values=lambda row,names:[float(row[k]) for k in names]
        errors=dict(position_m=math.dist(values(ref,('x','y','z')),values(got,('x','y','z'))),
            velocity_m_s=math.dist(values(ref,('vx','vy','vz')),values(got,('vx','vy','vz'))),
            rotation_rad=quaternion_angle(quaternion(ref),quaternion(got)),
            angular_velocity_rad_s=math.dist(values(ref,('wx','wy','wz')),values(got,('wx','wy','wz'))),
            mjd_days=abs(float(ref['mjd'])-float(got['mjd'])))
        require(all(math.isfinite(v) and v<=config['budgets'][k] for k,v in errors.items()),
                'Original Debug/Release state exceeds unchanged budget: '+str(key))
        for field in ('mass','fuel'):
            budget=max(config['budgets']['propellant_absolute_kg'],
                       abs(float(ref[field]))*config['budgets']['propellant_relative'])
            errors[field+'_fraction_of_budget']=abs(float(ref[field])-float(got[field]))/budget
            require(errors[field+'_fraction_of_budget']<=1,'Original mass/propellant build comparison fails')
        for field,error in errors.items():maxima[field]=max(maxima[field],error)
    ports=[rows(path/'stock-vessel-docks.csv') for path in (left,right)]
    require(len(ports[0])==len(ports[1]),'Paired stock docking-port count differs')
    for ref,got in zip(*ports):
        require(all(ref[k]==got[k] for k in ('tick','object','index','docked')) and
                all(float(ref[k])==float(got[k]) for k in ('x','y','z','dx','dy','dz','rx','ry','rz')),
                'Paired stock local docking parameters differ')
    return maxima


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',choices=('stations','shuttle-a'),default='stations')
    for name in ('artifacts','download-manifest','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--producer-commit',required=True)
    a=p.parse_args();select_suite(a.suite);require(not a.output.exists(),'Original station audit output exists')
    require(re.fullmatch('[0-9a-f]{40}',a.producer_commit),'Original station producer must be an immutable commit')
    config=settings();downloads=json.loads(a.download_manifest.read_text())
    require(downloads['status']=='passed' and downloads['source_commit']==a.producer_commit and
            len(downloads['artifacts'])==4,'Original station archive matrix is incomplete')
    result=dict(status='failed',phase6_complete=False,producer_commit=a.producer_commit,
        original_application_source=config['application_source'],source_sha256_lf=source_digest(Path(__file__)),
        download_manifest_sha256=digest(a.download_manifest),profiles={},build_comparisons={},
        method='Every finalized vessel and docking port; exact deterministic repeats; Debug/Release paired within each original CRT profile')
    try:
        names={c['id'] for c in config['cases']};total_samples=0
        for configuration in ('Debug','Release'):
            for math_profile in ('automatic','sse2'):
                profile=configuration+'-'+math_profile
                item=next(i for i in downloads['artifacts'] if i['name']==('original-stations-' if a.suite=='stations' else 'original-shuttle-a-')+profile)
                require(digest(ROOT/item['path'])==item['sha256'],'Downloaded original station archive changed')
                base=a.artifacts/profile;capture=base/('stations-original' if a.suite=='stations' else 'shuttle-a-original')
                report=json.loads((capture/'stock-vessels.json').read_text())
                require(report['status']=='passed' and not report['failures'] and set(report['cases'])==names and
                        report['configuration']==configuration and report['math_profile']==math_profile and
                        report['application_source']==config['application_source'] and
                        report['settings_sha256_lf']==source_digest(settings_path()),
                        'Original station capture is failed, incomplete or mismatched')
                for name,checksum in report['source_sha256_lf'].items():
                    require(Path(name).name==name,'Invalid original observer source path')
                    original=subprocess.check_output(['git','-C',str(ROOT),'show',a.producer_commit+
                                                       ':Tests/Production/StockVessels/'+name])
                    require(hashlib.sha256(original.replace(b'\r\n',b'\n')).hexdigest()==checksum,
                            'Original observer producer source differs: '+name)
                runtime=base/'station-original-runtime'
                preserved=json.loads((runtime/'test-runtime.json').read_text())
                staged=json.loads((runtime/'control-reference-runtime.json').read_text())
                require(preserved['source_commit']==staged['application_source']==config['application_source'] and
                        report['binary_sha256']['application']==preserved['files']['Orbiter.exe'] and
                        staged==report['runtime'] and
                        digest(runtime/'Modules/Plugin/ProductionCockpitDriver.dll')==report['binary_sha256']['observer'],
                        'Preserved original station application/SDK/client/observer identity differs')
                cases={}
                for case in config['cases']:
                    repeated=[]
                    for repeat,recorded in enumerate(report['cases'][case['id']]['runs'],1):
                        out=capture/(case['id']+'-'+str(repeat));repeated.append(out)
                        for file,checksum in recorded['files_sha256'].items():
                            require(digest(out/file)==checksum,'Original station artifact changed: '+str(out/file))
                        state,stations,groups=inspect_trace(out,case,config)
                        total_samples+=len(state)
                        require([r for r in stations if r['tick']=='0']==recorded['station_initial_capabilities'],
                                'Recorded original station capabilities differ from raw SDK observations')
                        require((out/'stock-vessel-complete.txt').read_text().strip()=='60' and
                                json.loads((out/'graphics-lifecycle.json').read_text())==
                                dict(rendered_frames=60,successful_presents=60,context_deleted=True),
                                'Original station presentation/shutdown incomplete')
                        renderer=json.loads((out/'renderer-info.json').read_text())
                        require(renderer==recorded['renderer'] and 'llvmpipe' in renderer['renderer'].lower() and
                                renderer['client_width']==1280 and renderer['client_height']==720,
                                'Actual original station renderer differs')
                        require(source_digest(out/'Scenarios/Behavior.scn')==case['sha256_lf'],
                                'Complete original station scenario source differs')
                        require((out/'math-profile.txt').read_text().strip()==recorded['actual_math'] and
                                (math_profile!='sse2' or recorded['actual_math']=='sse2'),
                                'Actual original station CRT profile differs')
                    for file in ('stock-vessel-state.csv','stock-vessel-docks.csv'):
                        require((repeated[0]/file).read_bytes()==(repeated[1]/file).read_bytes(),
                                'Original station deterministic repeat differs: '+file)
                    similarity=image_ssim((repeated[0]/'scene.rgba').read_bytes(),
                        (repeated[1]/'scene.rgba').read_bytes(),1280,720)
                    require(similarity>=config['image_ssim_minimum'] and similarity==report['cases'][case['id']]['repeat_ssim'],
                            'Original station repeated image score differs or fails')
                    cases[case['id']]=dict(scenario=case['scenario'],repeat_ssim=similarity,
                        station_initial_capabilities=report['cases'][case['id']]['runs'][0]['station_initial_capabilities'])
                control=json.loads((capture/'gate-control.json').read_text())
                require(control['status']=='passed' and control['missing_nonfocus_station_rejected'] and
                        control['missing_port_rejected'] and control['original_capture_unchanged'] and
                        control['source_sha256_lf']==report['source_sha256_lf']['Gate.Test.py'] and
                        all(digest(capture/(config['cases'][0]['id']+'-1')/name)==checksum for name,checksum in control['capture_sha256'].items()),
                        'Original station negative controls differ or fail')
                result['profiles'][profile]=dict(capture_sha256=digest(capture/'stock-vessels.json'),
                    observer_sha256=report['binary_sha256']['observer'],cases=cases,
                    gate_control_sha256=digest(capture/'gate-control.json'),archive_sha256=item['sha256'])
        for math_profile in ('automatic','sse2'):
            pairs={}
            for case in config['cases']:
                paths=[a.artifacts/(c+'-'+math_profile)/('stations-original' if a.suite=='stations' else 'shuttle-a-original')/(case['id']+'-1') for c in ('Debug','Release')]
                errors=compare_state(*paths,config)
                similarity=image_ssim((paths[0]/'scene.rgba').read_bytes(),(paths[1]/'scene.rgba').read_bytes(),1280,720)
                require(similarity>=config['image_ssim_minimum'],'Original station Debug/Release image gate fails')
                pairs[case['id']]=dict(maxima=errors,ssim=similarity)
            result['build_comparisons'][math_profile]=pairs
        processes=len(config['cases'])*2*4
        result.update(status='passed',processes=processes,scene_presents=processes*config['frames'],finalized_all_vessel_samples=total_samples,
                      frozen_references_unchanged=True,native_station_support_qualified=False)
    except BaseException as error:
        result['error']=str(error);raise
    finally:a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','processes','scene_presents','finalized_all_vessel_samples')}))


if __name__=='__main__':main()
