#!/usr/bin/env python3
"""Compare stock VC headlook images with the exact preserved Windows application."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
from reference import fixture,stage,mesa_files,image_ssim,require,rows,inspect as inspect_original
from compare import compare as compare_cockpit
from regression import mfd_images
from behavior_suite import distance,quaternion,quaternion_angle
from run_client import png

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()

def settings():
    value=json.loads((HERE/'cases.json').read_text())
    original=json.loads((HERE.parent/'Cockpit/cases.json').read_text())
    for key in ('application_source','frames','fixed_step','epoch','image_ssim_minimum','budgets'):
        require(value[key]==original[key],'Camera fixture changed an existing source/clock/budget: '+key)
    require(len(value['cases'])==12 and len({c['id'] for c in value['cases']})==12,'Incomplete camera fixture matrix')
    require({(c['class'],c['phi'],c['theta'],c['reopen']) for c in value['cases']}==
            {(cls,phi,theta,reopen) for cls in ('DeltaGlider','DG-S') for phi,theta in ((0,0),(.8,-.8),(0,-.6)) for reopen in (False,True)},
            'Camera poses, gliders or MFD startup paths differ')
    mesh='Src/Vessel/DeltaGlider/Meshes/deltaglider_vc.msh'
    preserved=subprocess.check_output(['git','-C',str(ROOT),'show',value['application_source']+':'+mesh])
    require(hashlib.sha256(preserved.replace(b'\r\n',b'\n')).hexdigest()==source_digest(ROOT/mesh),
            'Original VC mesh geometry changed')
    return value

def camera_input(out,case):
    (out/'headlook.txt').write_text(f"{case['phi']:.17g} {case['theta']:.17g} {int(case['reopen'])}\n")

def scenario(case):
    return fixture(case).replace('BEGIN_SHIPS',
        'BEGIN_MFD Left\n  TYPE Orbit\n  REF Earth\nEND_MFD\n'
        'BEGIN_MFD Right\n  TYPE Surface\nEND_MFD\nBEGIN_SHIPS')

CONFIG='\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'

def text_values(out):
    # The preserved observer numbers pointer-valued surface handles without
    # seeing their deletion. Reopening MFDs can reuse those addresses, so its
    # opaque labels are not repeatable. Retain the raw trace and compare every
    # draw call, dimension, coordinate, font, color and text byte in order.
    # Left/right render-target identity remains gated by direct MFD captures
    # and complete VC framebuffers, including off-axis texture placement.
    source=rows(out/'instrument-text.csv')
    fields=[name for name in source[0] if name!='surface']
    target=out/'instrument-text-values.csv'
    with target.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore',lineterminator='\n')
        writer.writeheader();writer.writerows(source)
    return target

def repeated_mfds(left,right,config):
    result={}
    for frame in (20,50):
        for index in (0,1):
            name=f'mfd-{index}-{frame}'
            sizes=[json.loads((p/(name+'.json')).read_text()) for p in (left,right)]
            require((sizes[0]['width'],sizes[0]['height'])==(sizes[1]['width'],sizes[1]['height']),
                    'Repeated MFD dimensions differ')
            similarity=image_ssim((left/(name+'.rgba')).read_bytes(),(right/(name+'.rgba')).read_bytes(),
                                  sizes[0]['width'],sizes[0]['height'])
            require(similarity>=config['image_ssim_minimum'],'Repeated direct MFD image exceeds unchanged budget')
            result[name]=similarity
    return result

def mfd_quads():
    lines=(ROOT/'Src/Vessel/DeltaGlider/Meshes/deltaglider_vc.msh').read_text().splitlines()
    result={}
    for label in ('LMFD_DISPLAY','RMFD_DISPLAY'):
        start=lines.index('LABEL '+label)+1
        require(lines[start].split()==['GEOM','4','2'],'Original VC MFD quad layout differs')
        result[label]=[list(map(float,line.split()[:3])) for line in lines[start+1:start+5]]
    return result

def project_quad(points,pose):
    result=[]
    for point in points:
        delta=[point[i]-float(pose[key]) for i,key in enumerate(('x','y','z'))]
        view=[sum(float(pose[f'm{j+1}{i+1}'])*delta[j] for j in range(3)) for i in range(3)]
        require(view[2]>0,'Fixture MFD quad crosses the camera plane')
        scale=360/math.tan(float(pose['aperture']))
        result.append([639.5+view[0]*scale/view[2],359.5-view[1]*scale/view[2]])
    return result

def visible_bounds(points):
    x0=max(0,math.floor(min(p[0] for p in points))-2);x1=min(1280,math.ceil(max(p[0] for p in points))+2)
    y0=max(0,math.floor(min(p[1] for p in points))-2);y1=min(720,math.ceil(max(p[1] for p in points))+2)
    return (x0,y0,x1,y1) if x1>x0 and y1>y0 else None

def crop(pixels,bounds):
    x0,y0,x1,y1=bounds
    return b''.join(pixels[4*(1280*y+x0):4*(1280*y+x1)] for y in range(y0,y1))

def compare_screen_mfds(original,native,config):
    result={};quads=mfd_quads()
    a={int(r['tick']):r for r in rows(original/'camera-sdk.csv')}
    b={int(r['tick']):r for r in rows(native/'camera-sdk.csv')}
    for frame in (20,50):
        for label,points in quads.items():
            left=project_quad(points,a[frame]);right=project_quad(points,b[frame])
            error=max(distance(p,q) for p,q in zip(left,right))
            require(error<=1.,'Projected original/native MFD quad exceeds the existing one-pixel overlay bound')
            bounds=visible_bounds(left)
            record=dict(projected_original=left,projected_native=right,max_pixel_error=error,bounds=bounds)
            if bounds:
                x0,y0,x1,y1=bounds
                similarity=image_ssim(crop((original/f'instrument-{frame}.rgba').read_bytes(),bounds),
                                      crop((native/f'instrument-{frame}.rgba').read_bytes(),bounds),x1-x0,y1-y0)
                require(similarity>=config['image_ssim_minimum'],'On-screen MFD image exceeds unchanged SSIM budget: '+label)
                record['ssim']=similarity
            result[f'{label}-{frame}']=record
    return result

def build_probe(build,out):
    compiler=next(line.split('=',1)[1] for line in (build/'CMakeCache.txt').read_text().splitlines()
                  if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
    probe=out/'camera-probe.so'
    subprocess.run([compiler,'-std=c++17','-fPIC','-shared','-Wl,--no-undefined',
        '-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),str(HERE/'NativeProbe.cpp'),
        '-L'+str(build),'-lorbiter_production_vessels','-lorbiter_production_boundary','-ldl','-o',str(probe)],check=True)
    return probe

def launch(args,out,case,probe):
    source=scenario(case)
    if args.original:
        def configure(directory):
            cfg=directory/'Orbiter.cfg'
            cfg.write_text(cfg.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')+CONFIG)
            (directory/'Scenarios/Behavior.scn').write_text(source)
            camera_input(directory,case)
            for name in ('ogl-evidence.enabled','instrument-evidence.enabled'):(directory/name).touch()
            mesa_files(args.mesa,directory)
        stage(args.executable,args.data,args.planets,out,dict(frames=60,fixed_step=.25,epoch=51982.5),configure)
        require(not (out/'cockpit-failure.txt').exists(),'Original camera observer failed')
        require((out/'cockpit-complete.txt').read_text().strip()=='60','Original camera capture did not complete')
    else:
        out.mkdir()
        camera_input(out,case)
        (out/'flight.scn').write_text(source)
        (out/'Orbiter.cfg').write_text((HERE.parent/'NativeScene/Orbiter.cfg').read_text()+CONFIG)
        (out/'instrument-evidence.enabled').touch()
        command=[str(args.executable),'--assets',str(args.assets),'--data',str(args.data),
            '--modules',str(args.modules),'--planets',str(args.planets),'--config',str(out/'Orbiter.cfg'),
            '--scenario',str(out/'flight.scn'),'--evidence',str(out),'--frames','60','--fixed-step','.25','--run']
        (out/'invocation.json').write_text(json.dumps(command,indent=2)+'\n')
        with (out/'console.txt').open('w') as log:
            subprocess.run(command,cwd=out,env=dict(os.environ,LD_PRELOAD=str(probe)),
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)

def validate(out,case,config,original):
    state=rows(out/'cockpit-state.csv');camera=rows(out/'camera-sdk.csv')
    # Camera SDK reads occur only at app.frame.end, after the real camera update.
    # Initial physical state remains the existing pre-step tick-0 observation.
    for samples,ticks in ((state,range(61)),(camera,range(1,61))):
        require([int(r['tick']) for r in samples]==list(ticks),'Incomplete camera/state observation')
        require(all(float(r['seconds'])==int(r['tick'])*.25 for r in samples),'Camera fixed-step clock differs')
        require(all(math.isfinite(float(v)) for r in samples for k,v in r.items() if k not in ('object','class')),
                'Nonfinite camera/state observation')
    require(all(r['object']=='DG' and r['class']==case['class'] and r['cockpit']=='3' and
                r['hud']=='1' and r['left_mfd']=='1' and r['right_mfd']=='2' for r in state),
            'Requested real vessel/VC/instruments differ')
    require(all(r['internal']=='1' and r['cockpit']=='3' and
                abs(float(r['aperture'])-math.radians(25))<1e-12 for r in camera),'Camera mode or aperture differs')
    if case['phi'] or case['theta']:
        require(sum(abs(float(camera[-1][k])) for k in ('m13','m23','m31','m32'))>.1,
                'SDK headlook did not rotate the actual VC camera')
    if case['theta']==-.6:
        for points in mfd_quads().values():
            require(all(0<=x<1280 and 0<=y<720 for x,y in project_quad(points,camera[-1])),
                    'Centered-downward fixture must expose both complete MFD displays')
    inputs=rows(out/'camera-inputs.csv')
    require(len(inputs)==1 and inputs[0]['tick']=='0' and float(inputs[0]['phi'])==case['phi'] and
            float(inputs[0]['theta'])==case['theta'] and int(inputs[0]['reopen'])==case['reopen'],
            'Actual public SDK headlook/MFD inputs differ')
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=60,successful_presents=60,context_deleted=True),'Incomplete camera graphics lifecycle')
    renderer=json.loads((out/'renderer-info.json').read_text())
    require('llvmpipe' in renderer['renderer'].lower(),'Camera image gate requires actual software OpenGL')
    errors=out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(),'Camera OpenGL errors')
    text=rows(out/'instrument-text.csv')
    require(len(text)>100 and any(float(r['seconds'])>=12.5 for r in text),'Original MFD drawing did not reach the captures')
    text_values(out)
    images={}
    for frame in (20,50):
        stem=out/f'instrument-{frame}';pixels=stem.with_suffix('.rgba').read_bytes()
        require(len(pixels)==1280*720*4,'Incomplete full VC framebuffer')
        png(stem.with_suffix('.png'),pixels,1280,720);images[str(frame)]=digest(stem.with_suffix('.rgba'))
        for index in (0,1):
            stem=out/f'mfd-{index}-{frame}';mfd=json.loads(stem.with_suffix('.json').read_text())
            require(mfd['colored_pixels']>20 and mfd['nonwhite_pixels']>mfd['width']*mfd['height']//4,
                    'Camera capture has a blank actual MFD surface')
            png(stem.with_suffix('.png'),stem.with_suffix('.rgba').read_bytes(),mfd['width'],mfd['height'])
    console=(out/'console.txt').read_text(errors='replace')
    for marker in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','Lua error:'):
        require(marker not in console,'Camera runtime error: '+marker)
    result=dict(status='passed',images=images,renderer=renderer,lifecycle=life,camera_samples=len(camera),
                camera_sha256=digest(out/'camera-sdk.csv'),inputs_sha256=digest(out/'camera-inputs.csv'),
                text_values_sha256=digest(out/'instrument-text-values.csv'),raw_text_sha256=digest(out/'instrument-text.csv'))
    if original:result['original_runtime']=inspect_original(out,case,config)
    return result

def capture(args):
    config=settings()
    require(not args.case or set(args.case)<={c['id'] for c in config['cases']},'Unknown camera case')
    for name in ('executable','data','planets','output','mesa','assets','modules'):
        if (value:=getattr(args,name,None)) is not None:setattr(args,name,value.resolve())
    require(not args.output.exists(),'Camera output exists; replacement is forbidden')
    if args.original:
        require(sys.platform=='win32' and args.mesa,'Preserved camera capture requires native Windows and the locked Mesa runtime')
        runtime=json.loads((args.executable.parent/'control-reference-runtime.json').read_text())
        require(runtime['application_source']==config['application_source'],'Wrong preserved Windows application')
        preserved=json.loads((args.executable.parent/'test-runtime.json').read_text())
        for name,checksum in preserved['files'].items():
            if name!='Modules/Plugin/ProductionCockpitDriver.dll':
                require(digest(args.executable.parent/name)==checksum,'Preserved application/SDK bytes differ: '+name)
        for name,checksum in runtime['client_files_sha256'].items():
            require(digest(args.executable.parent/name)==checksum,'Preserved client/shader bytes differ: '+name)
        runtime['executed_application_sha256']=digest(args.executable)
        producer=args.executable.parent/'Modules/Plugin/ProductionCockpitDriver.dll'
    else:
        require(args.assets and args.modules,'Native camera capture requires assets and modules')
        runtime=dict(executable_sha256=digest(args.executable),
                     engine_library_sha256=digest(args.executable.parent/'liborbiter_production_vessels.so'),
                     renderer_module_sha256=digest(args.modules/'Graphics/OGLClient.so'))
    args.output.mkdir(parents=True)
    probe=None if args.original else build_probe(args.executable.parent,args.output)
    producer=producer if args.original else probe
    report=dict(status='pending',host='original-windows' if args.original else 'native-linux',
        configuration=args.configuration,math_profile=args.math_profile,application_source=config['application_source'],
        runtime=runtime,producer_sha256=digest(producer),settings_sha256=source_digest(HERE/'cases.json'),
        input_sources_sha256={p.name:source_digest(p) for p in HERE.iterdir() if p.is_file()},cases={},failures={})
    for case in config['cases']:
        if args.case and case['id'] not in args.case:continue
        try:
            runs=[];observed=[]
            for repeat in (1,2):
                out=args.output/(case['id']+'-'+str(repeat));runs.append(out)
                launch(args,out,case,probe);observation=validate(out,case,config,args.original)
                actual_math=(out/'math-profile.txt').read_text().strip() if args.original else json.loads((out/'numerics.json').read_text())['math']
                require(actual_math in ('fma3','sse2','amd-6121d02-fma3','amd-6121d02-sse2'),'Unknown camera math implementation')
                if args.math_profile=='sse2':require(actual_math.endswith('sse2'),'Camera did not use the required SSE2 profile')
                observation['actual_math']=actual_math;observed.append(observation)
            for name in ('cockpit-state.csv','camera-sdk.csv','camera-inputs.csv','instrument-text-values.csv',
                         'instrument-geometry.csv','instrument-self-blits.csv'):
                require((runs[0]/name).read_bytes()==(runs[1]/name).read_bytes(),'Camera repeat differs: '+name)
            repeated={str(frame):image_ssim((runs[0]/f'instrument-{frame}.rgba').read_bytes(),
                       (runs[1]/f'instrument-{frame}.rgba').read_bytes(),1280,720) for frame in (20,50)}
            require(min(repeated.values())>=config['image_ssim_minimum'],'Camera image repeat exceeds unchanged budget')
            report['cases'][case['id']]=dict(runs=observed,repeat_ssim=repeated,
                repeat_mfd_ssim=repeated_mfds(*runs,config),
                identical_state_camera_text_values_geometry=True,raw_text_surface_labels_retained=True)
            print(case['id'],'passed',flush=True)
        except Exception as error:
            failure=out/'cockpit-failure.txt'
            report['failures'][case['id']]=str(error)+(': '+failure.read_text().strip() if failure.exists() else '')
            print(case['id'],report['failures'][case['id']],flush=True)
    report['status']='failed' if report['failures'] else 'passed'
    (args.output/'camera-report.json').write_text(json.dumps(report,indent=2)+'\n')
    require(report['status']=='passed','Camera capture failed; do not claim image parity')

def compare(args):
    config=settings();names={c['id'] for c in config['cases']}
    require(not args.output.exists(),'Camera comparison output exists; replacement is forbidden')
    profiles=[]
    for path,host in ((args.original,'original-windows'),(args.native,'native-linux')):
        report=json.loads((path/'camera-report.json').read_text())
        require(report['status']=='passed' and report['host']==host and set(report['cases'])==names,
                'Incomplete original/native camera matrix')
        require(report['settings_sha256']==source_digest(HERE/'cases.json'),'Camera input definition differs')
        for name in ('Observation.h','Driver.cpp','NativeProbe.cpp'):
            require(report['input_sources_sha256'][name]==source_digest(HERE/name),
                    'Camera SDK fixture/observer source differs: '+name)
        profiles.append((report['configuration'],report['math_profile']))
        for case in config['cases']:
            for repeat,run in enumerate(report['cases'][case['id']]['runs'],1):
                out=path/(case['id']+'-'+str(repeat))
                for name,key in (('camera-sdk.csv','camera_sha256'),('camera-inputs.csv','inputs_sha256'),
                                 ('instrument-text-values.csv','text_values_sha256'),('instrument-text.csv','raw_text_sha256')):
                    require(digest(out/name)==run[key],'Captured camera evidence bytes differ: '+str(out/name))
    require(profiles[0]==profiles[1],'Original/native camera configuration/profile differs')
    result=dict(status='pending',cases={},camera={},mfd_images={},screen_mfds={})
    try:
        # Apply the existing cockpit comparator to read-only input views. Only
        # opaque pointer-label columns are projected out; all raw files remain.
        with tempfile.TemporaryDirectory(prefix='orbiter-camera-compare-') as temporary:
            views=[]
            for index,base in enumerate((args.original,args.native)):
                view=Path(temporary)/str(index);view.mkdir();views.append(view)
                for case in config['cases']:
                    source=base/(case['id']+'-1');target=view/source.name;target.mkdir()
                    for file in source.iterdir():
                        if file.is_file() and file.name!='instrument-text.csv':
                            (target/file.name).symlink_to(file.resolve())
                    (target/'instrument-text.csv').symlink_to((source/'instrument-text-values.csv').resolve())
            result['cases']=compare_cockpit(*views,config)
        result['mfd_images']=mfd_images(args.original,args.native,config)
        for case in config['cases']:
            result['screen_mfds'][case['id']]=compare_screen_mfds(
                args.original/(case['id']+'-1'),args.native/(case['id']+'-1'),config)
            name=case['id'];left=rows(args.original/(name+'-1')/'camera-sdk.csv');right=rows(args.native/(name+'-1')/'camera-sdk.csv')
            maximum=dict(position_m=0.,rotation_rad=0.,aperture_rad=0.)
            for a,b in zip(left,right):
                for key in ('tick','seconds','internal','cockpit'):require(a[key]==b[key],'Discrete camera state differs: '+key)
                errors=dict(position_m=distance([float(a[k]) for k in ('x','y','z')],[float(b[k]) for k in ('x','y','z')]),
                            rotation_rad=quaternion_angle(quaternion(a),quaternion(b)),
                            aperture_rad=abs(float(a['aperture'])-float(b['aperture'])))
                for key,value in errors.items():
                    budget=config['budgets']['rotation_rad' if key=='aperture_rad' else key]
                    require(value<=budget,'Actual camera transform exceeds existing budget: '+name+' '+key)
                    maximum[key]=max(maximum[key],value)
            result['camera'][name]=maximum
        result['status']='passed'
    except Exception as error:
        result.update(status='failed',error=str(error));raise
    finally:args.output.write_text(json.dumps(result,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('capture');p.add_argument('--original',action='store_true')
    for name in ('executable','data','planets','output'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('mesa','assets','modules'):p.add_argument('--'+name,type=Path)
    p.add_argument('--case',action='append')
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--math-profile',choices=('automatic','sse2'),required=True)
    p=sub.add_parser('compare')
    for name in ('original','native','output'):p.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.command=='compare':compare(args)
    else:capture(args)
if __name__=='__main__':main()
