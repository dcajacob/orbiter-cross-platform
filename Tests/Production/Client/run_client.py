#!/usr/bin/env python3
"""Execute the real Windows client with production Sol/ISS/ShuttlePB data."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import zipfile
import zlib

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from behavior_suite import stage,rows,git
from mesa_runtime import digest,require
from frozen_behavior import load_reference
from compare_references import quaternion
from trace_tools import distance,quaternion_angle
from pe_symbols import PE


def mesa_files(source,destination):
    manifest=json.loads((source/'mesa-runtime.json').read_text());bindings={}
    for name,entry in manifest['files'].items():
        incoming=source/name;target=destination/name
        require(digest(incoming)==entry['sha256'],'Mesa staging file differs from locked package: '+name)
        if target.exists() and digest(target)!=entry['sha256']:
            require(name.casefold()=='zlib1.dll','unreviewed application/Mesa DLL conflict: '+name)
            required={}
            for candidate in source.glob('*.dll'):
                imports=PE(candidate).imports().get('zlib1.dll',set())
                if imports:required[candidate.name]=sorted(imports)
            exports=PE(target).exports()
            require(all(set(symbols)<=exports for symbols in required.values()),
                    'production zlib cannot satisfy pinned Mesa imports; do not overwrite either runtime')
            bindings[name]=dict(policy='retain original source-built application zlib; exact C exports audited',
                                effective_sha256=digest(target),mesa_package_sha256=entry['sha256'],imports=required)
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():shutil.copy2(incoming,target)
    (destination/'mesa-bindings.json').write_text(json.dumps(dict(runtime=manifest,bindings=bindings),indent=2)+'\n')


def png(path,pixels,width,height):
    require(len(pixels)==width*height*4,'incomplete real-client readback')
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data))
    scan=b''.join(b'\0'+pixels[y*width*4:(y+1)*width*4] for y in reversed(range(height)))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+
                     chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))


def numerical_reference(directory,configuration):
    metadata=load_reference(HERE.parent/'BehaviorReference');record=metadata['artifacts'][configuration]
    with zipfile.ZipFile((HERE.parent/'BehaviorReference'/record['path']).resolve()) as archive:
        import io
        reference=list(csv.DictReader(io.StringIO(archive.read('production-behavior/callbacks/behavior-state.csv').decode())))
    current=rows(directory/'behavior-state.csv');require(len(reference)==len(current),'rendered numerical sample count differs')
    maxima=dict(position_m=0.,velocity_m_s=0.,rotation_rad=0.,angular_velocity_rad_s=0.,mjd_days=0.)
    limits=dict(position_m=.01,velocity_m_s=1e-5,rotation_rad=1e-8,angular_velocity_rad_s=1e-10,mjd_days=1e-10)
    for a,b in zip(reference,current):
        for key in ('tick','frame','seconds','object','class','ground','dock','focus','navmask','attached'):
            require(a[key]==b[key],'graphics changed discrete simulation state: '+key)
        vector=lambda r,keys:[float(r[k]) for k in keys]
        errors=dict(position_m=distance(vector(a,('rx','ry','rz')),vector(b,('rx','ry','rz'))),
                    velocity_m_s=distance(vector(a,('vx','vy','vz')),vector(b,('vx','vy','vz'))),
                    rotation_rad=quaternion_angle(quaternion(a),quaternion(b)),
                    angular_velocity_rad_s=distance(vector(a,('wx','wy','wz')),vector(b,('wx','wy','wz'))),
                    mjd_days=abs(float(a['mjd'])-float(b['mjd'])))
        for key,error in errors.items():require(error<=limits[key],'graphics changed production numerics: '+key);maxima[key]=max(maxima[key],error)
        for key in ('mass','fuel'):
            require(abs(float(a[key])-float(b[key]))<=max(1e-8,abs(float(a[key]))*1e-8),'graphics changed propulsion state')
    return maxima


def validate(directory,configuration,provenance):
    info=json.loads((directory/'renderer-info.json').read_text());require('llvmpipe' in info['renderer'],'real application did not load software Mesa')
    require(info['client_width']==1280 and info['client_height']==720,'real window client area differs from the test viewport')
    errors=directory/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(),'OpenGL reported errors during actual client execution')
    summary=json.loads((directory/'scene-summary.json').read_text())
    require(summary['simulation_seconds']==12.5 and summary['frames']>0 and summary['mesh_draw_calls']>0 and summary['indices']>0,'real scene geometry was not drawn')
    lifecycle=json.loads((directory/'graphics-lifecycle.json').read_text())
    require(lifecycle['rendered_frames']>=50 and lifecycle['successful_presents']>=50 and lifecycle['context_deleted'],
            'real window presentation or OpenGL cleanup did not complete')
    scene=rows(directory/'scene.csv');vessels=[r for r in scene if r['type']=='vessel']
    require({'PB','ISS'}<={r['object'] for r in vessels},'real stock vessel visuals/meshes missing')
    require(all(int(r['groups'])>0 and int(r['materials'])>0 and int(r['textures'])>0 for r in vessels),'stock mesh/material/texture content missing')
    require({'Sun','Earth','Moon'}<={r['object'] for r in scene},'production Sol object graph missing')
    object_draws=rows(directory/'object-draws.csv')
    require({'PB','ISS'}<={r['object'] for r in object_draws if int(r['mesh_draw_calls'])>0},
            'actual stock vessel geometry was not submitted to OpenGL')
    planet_tiles=rows(directory/'planet-tiles.csv');archive_reads=rows(directory/'archive-reads.csv')
    require(any(r['object']=='Earth' and int(r['textured_draw_calls'])>0 for r in planet_tiles),
            'actual Earth surface tiles were not drawn')
    require(any('earth' in r['path'].casefold() and r['layer']=='0' and int(r['inflated_bytes'])>0 for r in archive_reads),
            'real Earth surface archive data was not consumed')
    events=rows(directory/'visual-events.csv')
    require({'PB','ISS','Earth'}<={r['object'] for r in events if r['event']=='register'},'normal engine visual registration missing')
    require({'PB','ISS','Earth'}<={r['object'] for r in events if r['event']=='unregister'},'normal visual teardown missing')
    bindings=json.loads((directory/'mesa-bindings.json').read_text());modules=[]
    expected_files={name.casefold():entry for name,entry in bindings['runtime']['files'].items()}
    effective_bindings={name.casefold():entry for name,entry in bindings['bindings'].items()}
    system=Path(os.environ['SystemRoot']).resolve();names=set()
    for line in (directory/'renderer-modules.txt').read_text().splitlines():
        path=Path(line).resolve();names.add(path.name.casefold())
        if path.suffix.lower()!='.dll':continue
        require(directory.resolve() in path.parents or system in path.parents,'unrecorded external runtime DLL: '+str(path))
        entry=dict(path=str(path),sha256=digest(path));modules.append(entry)
        expected=expected_files.get(path.name.casefold())
        if expected:
            checksum=effective_bindings.get(path.name.casefold(),{}).get('effective_sha256',expected['sha256'])
            require(path.parent==directory.resolve() and entry['sha256']==checksum,'actual loaded Mesa binding differs: '+path.name)
    require({'opengl32.dll','libgallium_wgl.dll','oglclient.dll','shuttlepb.dll'}<=names,'required actual client/vessel/driver DLL was not loaded')
    assets={}
    for line in (directory/'loaded-assets.txt').read_text().splitlines():
        if not line:continue
        p=Path(line);p=p if p.is_absolute() else directory/p
        require(p.is_file(),'recorded texture asset is missing: '+line);assets[line]=digest(p)
    require(assets,'no actual texture asset was decoded')
    for r in vessels:
        p=directory/'Meshes'/(r['name'].replace('\\','/')+'.msh')
        require(p.is_file(),'actual vessel mesh file missing');assets[p.relative_to(directory).as_posix()]=digest(p)
    raw=(directory/'scene.rgba').read_bytes();png(directory/'scene.png',raw,1280,720)
    require(len(set(raw[::4]))>16,'scene readback is a blank or trivial image')
    report=dict(status='passed real Windows production scene',provenance=provenance,
                executable_sha256=digest(directory/'Orbiter.exe'),client_sha256=digest(directory/'Modules/Plugin/OGLClient.dll'),renderer=info,geometry=summary,lifecycle=lifecycle,
                objects=scene,object_draws=object_draws,planet_tiles=planet_tiles,archive_reads=archive_reads,asset_sha256=assets,loaded_modules=modules,
                simulation_comparison=numerical_reference(directory,configuration),image_sha256=digest(directory/'scene.png'))
    (directory/'client-report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','mesa','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args();require(sys.platform=='win32','real Windows application execution is required')
    require(json.loads((HERE.parent/'phase1-gates.json').read_text())['phase_status']=='accepted','Phase 1 must be accepted first')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
    args.output.mkdir(parents=True,exist_ok=False)
    case=next(c for c in json.loads((HERE.parent/'behavior-cases.json').read_text())['cases'] if c['id']=='callbacks')
    def configure(directory):
        config=directory/'Orbiter.cfg';s=config.read_text().replace('  ProductionBehaviorDriver','  ProductionBehaviorDriver\n  OGLClient')
        config.write_text(s+'\nFPS = 0\n',encoding='ascii')
        scenario=directory/'Scenarios/Behavior.scn';scenario.write_text(scenario.read_text().replace('  POS 4 0 0','  POS 4 90 0'))
        (directory/'ogl-evidence.enabled').write_text('Stock Sol/ISS/ShuttlePB integration evidence\n')
        require((directory/'Modules/Plugin/OGLClient.dll').is_file(),'separately built OpenGL client missing')
        mesa_files(args.mesa.resolve(),directory)
    provenance=dict(renderer_source=git('rev-parse','HEAD').decode().strip(),
                    application_source=json.loads((args.orbiter.parent/'test-runtime.json').read_text())['source_commit'],
                    data_profiles_sha256={name:digest(HERE.parent/name) for name in ('stock-data.lock.json','standard-planets.lock.json','mesa-ucrt64.lock.json')})
    reports=[];summary=dict(status='pending',config=args.configuration,provenance=provenance)
    try:
        for name in ('scene','scene-repeat'):
            directory=args.output.resolve()/name
            stage(args.orbiter.resolve(),args.data.resolve(),args.planets.resolve(),directory,case,None,before_launch=configure)
            reports.append(validate(directory,args.configuration,provenance))
        for name in ('behavior-state.csv','behavior-events.csv','behavior-propellant.csv','behavior-animations.csv'):
            require((args.output/'scene'/name).read_bytes()==(args.output/'scene-repeat'/name).read_bytes(),'rendered production repeat differs: '+name)
        require(reports[0]['image_sha256']==reports[1]['image_sha256'],'fixed-camera real scene did not repeat identically')
        summary.update(status='passed',repeated_image_sha256=reports[0]['image_sha256'])
    except Exception as error:
        summary.update(status='failed',error=str(error),completed_runs=len(reports))
        raise
    finally:
        (args.output/'client-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Real Windows Orbiter/OpenGL Sol + ISS + ShuttlePB scene, DLL audit, repeat and frozen numerical comparison passed')


if __name__=='__main__':main()
