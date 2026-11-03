#!/usr/bin/env python3
"""Compare complete native X11 and Wayland VC camera matrices with the existing budgets."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent/'CockpitCamera'))
import run as camera

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('x11','wayland','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();camera.require(not args.output.exists(),'Backend comparison output exists')
    config=camera.settings();names={c['id'] for c in config['cases']};reports=[]
    for base,backend in ((args.x11,'x11'),(args.wayland,'wayland')):
        report=json.loads((base/'camera-report.json').read_text());reports.append(report)
        camera.require(report['status']=='passed' and report['host']=='native-linux' and
                       set(report['cases'])==names,'Incomplete native backend matrix')
        camera.require(report['settings_sha256']==camera.source_digest(camera.HERE/'cases.json'),
                       'Backend camera fixture definition differs')
        for source in ('Observation.h','NativeProbe.cpp'):
            camera.require(report['input_sources_sha256'][source]==camera.source_digest(camera.HERE/source),
                           'Backend SDK fixture source differs')
        for case in config['cases']:
            for repeat in (1,2):
                path=base/(case['id']+'-'+str(repeat))/'native-window.json'
                camera.require(json.loads(path.read_text())['backend']==backend,'Actual native window backend differs')
    camera.require(reports[0]['runtime']['engine_library_sha256']==reports[1]['runtime']['engine_library_sha256'],
                   'Backend comparison requires identical engine libraries')
    result=dict(status='pending',scope='Native X11 versus native Wayland; not original Windows parity',
                x11=str(args.x11),wayland=str(args.wayland),
                report_sha256=[camera.digest(base/'camera-report.json') for base in (args.x11,args.wayland)],
                matched_engine_sha256=reports[0]['runtime']['engine_library_sha256'],cases={},mfd_images={},screen_mfds={},camera={})
    try:
        with tempfile.TemporaryDirectory(prefix='orbiter-backend-compare-') as temporary:
            views=[]
            for index,base in enumerate((args.x11,args.wayland)):
                view=Path(temporary)/str(index);view.mkdir();views.append(view)
                for case in config['cases']:
                    source=base/(case['id']+'-1');target=view/source.name;target.mkdir()
                    for file in source.iterdir():
                        if file.is_file() and file.name!='instrument-text.csv':(target/file.name).symlink_to(file.resolve())
                    (target/'instrument-text.csv').symlink_to((source/'instrument-text-values.csv').resolve())
            result['cases']=camera.compare_cockpit(*views,config)
        result['mfd_images']=camera.mfd_images(args.x11,args.wayland,config)
        for case in config['cases']:
            name=case['id'];left=args.x11/(name+'-1');right=args.wayland/(name+'-1')
            result['screen_mfds'][name]=camera.compare_screen_mfds(left,right,config)
            a=camera.rows(left/'camera-sdk.csv');b=camera.rows(right/'camera-sdk.csv')
            camera.require(len(a)==len(b)==60,'Incomplete backend camera trace')
            maxima=dict(position_m=0.,rotation_rad=0.,aperture_rad=0.)
            for x,y in zip(a,b):
                camera.require(all(x[k]==y[k] for k in ('tick','seconds','internal','cockpit')),'Discrete backend camera state differs')
                errors=dict(position_m=camera.distance([float(x[k]) for k in ('x','y','z')],[float(y[k]) for k in ('x','y','z')]),
                    rotation_rad=camera.quaternion_angle(camera.quaternion(x),camera.quaternion(y)),
                    aperture_rad=abs(float(x['aperture'])-float(y['aperture'])))
                for key,value in errors.items():
                    camera.require(value<=config['budgets']['rotation_rad' if key=='aperture_rad' else key],
                                   'Backend camera transform exceeds existing budget: '+key)
                    maxima[key]=max(maxima[key],value)
            result['camera'][name]=maxima
        result['status']='passed'
        print('All twelve native X11/Wayland camera comparisons passed')
    except Exception as error:
        result.update(status='failed',error=str(error));raise
    finally:args.output.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
