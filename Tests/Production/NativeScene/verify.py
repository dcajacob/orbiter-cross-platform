#!/usr/bin/env python3
"""Verify the actual native production external view against frozen Windows."""
import argparse,csv,hashlib,json,math,os,platform,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tests/Production'))
sys.path.insert(0,str(ROOT/'Tests/Production/Client'))
from mesa_runtime import require,digest
from behavior_suite import rows,distance,quaternion,quaternion_angle
from compare_client import image_ssim,reference_pixels,projected_landmarks
from run_client import png
from frozen_client import verify as verify_frozen_client

def states(directory,reference):
    observed=rows(directory/'production-state.csv')
    for row in observed:
        require(all(math.isfinite(float(value)) for key,value in row.items() if key not in ('object',)), 'Nonfinite native trace state')
    by={(int(r['step']),r['object']):r for r in observed}
    maximum=dict(position_m=0.,velocity_m_s=0.,rotation_rad=0.,angular_velocity_rad_s=0.,mjd_days=0.,mass_fraction=0.)
    for old in rows(reference/'behavior-state.csv'):
        tick=int(old['tick']);new=by[tick,old['object']];earth=by[tick,'Earth']
        position=[float(new[k])-float(earth[k]) for k in ('x','y','z')]
        velocity=[float(new[k])-float(earth[k]) for k in ('vx','vy','vz')]
        errors=dict(position_m=distance(position,[float(old[k]) for k in ('rx','ry','rz')]),
            velocity_m_s=distance(velocity,[float(old[k]) for k in ('vx','vy','vz')]),
            rotation_rad=quaternion_angle(quaternion(old),quaternion(new)),
            angular_velocity_rad_s=distance([float(old[k]) for k in ('wx','wy','wz')],[float(new[k]) for k in ('wx','wy','wz')]),
            mjd_days=abs(float(old['mjd'])-float(new['mjd'])))
        require(old['seconds']==new['seconds'] and old['ground']==new['ground'],'Native discrete tick/time/contact differs')
        for key,value in errors.items():maximum[key]=max(maximum[key],value)
        for key in ('mass','fuel'):
            maximum['mass_fraction']=max(maximum['mass_fraction'],abs(float(old[key])-float(new[key]))/max(1e-8,abs(float(old[key]))*1e-8))
    budgets=dict(position_m=.01,velocity_m_s=1e-5,rotation_rad=1e-8,angular_velocity_rad_s=1e-10,mjd_days=1e-10,mass_fraction=1.)
    require(all(maximum[k]<=budgets[k] for k in maximum),'Native application state exceeds frozen Windows budget')
    return dict(maxima=maximum,budgets=budgets,samples=len(observed))

def inspect(directory,reference,minimum):
    lifecycle=json.loads((directory/'graphics-lifecycle.json').read_text())
    require(lifecycle==dict(rendered_frames=60,successful_presents=60,context_deleted=True),'Incomplete native graphics lifecycle')
    scene=rows(directory/'scene.csv');vessels=[r for r in scene if r['type']=='vessel']
    require({r['object'] for r in vessels}=={'PB','ISS'},'Actual stock vessel identities missing')
    require({(r['object'],r['class']) for r in vessels}=={('PB','ShuttlePB'),('ISS','ProjectAlpha_ISS')},'Required module/class changed')
    require(all(int(r['groups'])>0 and int(r['materials'])>0 and int(r['textures'])>0 for r in vessels),'Actual mesh/material/texture data missing')
    require({'PB','ISS'}<={r['object'] for r in rows(directory/'object-draws.csv') if int(r['mesh_draw_calls'])>0},'Actual stock geometry was not drawn')
    require(any(r['object']=='Earth' and int(r['textured_draw_calls'])>0 for r in rows(directory/'planet-tiles.csv')),'Actual Earth tiles were not drawn')
    require(any('earth' in r['path'].lower() and r['layer']=='0' and int(r['inflated_bytes'])>0 for r in rows(directory/'archive-reads.csv')),'Real Earth archive was not consumed')
    events=rows(directory/'visual-events.csv')
    for event in ('register','unregister'):
        require({'PB','ISS','Earth'}<={r['object'] for r in events if r['event']==event},'Missing actual visual lifecycle: '+event)
    left,right=projected_landmarks(reference),projected_landmarks(directory)
    landmarks={name:math.dist(left[name],right[name]) for name in left}
    require(all(error<=1 for error in landmarks.values()),'Native projected landmarks exceed one pixel')
    assets={}
    for name in (directory/'loaded-assets.txt').read_text().splitlines():
        path=Path(name);require(path.is_absolute() and path.is_file(),'Unresolved actual asset: '+name);assets[str(path)]=digest(path)
    modules={}
    for name in (directory/'renderer-modules.txt').read_text().splitlines():
        path=Path(name)
        if path.is_file():modules[str(path)]=digest(path)
    names={Path(name).name for name in modules}
    require({'OGLClient.so','ShuttlePB.so','liborbiter_production_vessels.so','liborbiter_production_boundary.so'}<=names,'Actual renderer/engine/vessel libraries missing')
    pixels=(directory/'scene.rgba').read_bytes();png(directory/'scene.png',pixels,1280,720)
    similarity=image_ssim(reference_pixels(ROOT/'Tests/Production/ClientReference/scene.png'),pixels,1280,720)
    require(similarity>=minimum,'Native full-image SSIM below frozen budget')
    return dict(states=states(directory,reference),landmark_errors_px=landmarks,ssim=similarity,ssim_minimum=minimum,masks=[],
        renderer=json.loads((directory/'renderer-info.json').read_text()),loaded_assets=assets,loaded_modules=modules)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    verify_frozen_client(ROOT/'Tests/Production/ClientReference')
    reference=ROOT/'Tests/Production/ClientReference'/args.configuration
    results=[]
    for repeat in (1,2):
        directory=output/('run-'+str(repeat))
        command=[str(args.executable.resolve()),'--assets',str(args.assets.resolve()),'--data',str(args.data.resolve()),'--modules',str(args.modules.resolve()),
            '--planets',str(args.planets.resolve()),'--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),
            '--scenario',str(ROOT/'Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn'),'--evidence',str(directory),'--frames','60','--fixed-step','0.25','--capture-time','12.5','--run']
        process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        (output/('run-'+str(repeat)+'.log')).write_bytes(process.stdout)
        require(process.returncode==0,'Native production scene failed: '+str(output))
        results.append(inspect(directory,reference,.98))
    for name in ('production-state.csv','camera.csv','scene.csv','scene.rgba','object-draws.csv','planet-tiles.csv','archive-reads.csv','visual-events.csv'):
        require((output/'run-1'/name).read_bytes()==(output/'run-2'/name).read_bytes(),'Native repeated scene differs: '+name)
    # A missing required native vessel must never become a generic substitute.
    negative=output/'negative-generic-assets'
    if negative.exists():shutil.rmtree(negative)
    shutil.copytree(args.assets.resolve(),negative,copy_function=os.link)
    config=negative/'Config/Vessels/ShuttlePB.cfg';text=config.read_text();config.unlink()
    config.write_text('\n'.join(line for line in text.splitlines() if not line.lstrip().lower().startswith('module'))+'\n')
    command=[str(args.executable.resolve()),'--assets',str(negative),'--data',str(args.data.resolve()),'--modules',str(args.modules.resolve()),
        '--planets',str(args.planets.resolve()),'--config',str(ROOT/'Tests/Production/NativeScene/Orbiter.cfg'),
        '--scenario',str(ROOT/'Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn'),'--frames','1']
    try:
        rejected=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        (output/'negative-generic.log').write_bytes(rejected.stdout)
        require(rejected.returncode!=0 and b'generic replacement is forbidden' in rejected.stdout,'Required native module silently became a generic vessel')
    finally:
        shutil.rmtree(negative)
    report=dict(status='passed actual native production external view',configuration=args.configuration,host=platform.platform(),
        source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only'])),
        executable_sha256=digest(args.executable),runs=results,
        scope='Real Sol/SPICE, production world/camera/session, actual ISS and source-built ShuttlePB, shared stock OpenGL scene. Cockpit, flight input, Lua and stock-playable release gates remain open.')
    (output/'native-scene-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Native production scene passed; SSIM:',*[r['ssim'] for r in results])
if __name__=='__main__':main()
