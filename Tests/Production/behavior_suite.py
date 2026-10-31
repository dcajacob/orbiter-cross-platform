#!/usr/bin/env python3
"""Capture/verify real production behavioral scenarios without refreshing goldens."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from capture_reference import link_or_copy, ROOT, git
from mesa_runtime import digest, require
from observation_source import verify as verify_observation_source
from compare_references import quaternion
from trace_tools import distance, quaternion_angle

FILES = ('behavior-state.csv','behavior-events.csv','behavior-propellant.csv','behavior-animations.csv')


def scenario(fixture):
    pb = 'PB:ShuttlePB\n  STATUS Orbiting Earth\n  RPOS 6771100 0 0\n  RVEL 0 0 7672.5\n  AROT 0 0 0\n  VROT 0 0 0\n  PRPLEVEL 0:1\n'
    iss = 'ISS:ProjectAlpha_ISS\n  STATUS Orbiting Earth\n  RPOS 6771000 0 0\n  RVEL 0 0 7672.5\n  AROT 0 0 0\n  VROT 0 0 0\nEND\n'
    focus = 'PB'
    if fixture == 'approach':
        # Orbiter's +90 degree X convention maps PB's +Y approach to -Z,
        # opposite ISS port 0. Port origins start 5 m apart, closing at .2 m/s.
        pb = pb.replace('6771100 0 0','6771000.08 -4.8 22').replace('0 0 7672.5','0 0 7672.3').replace('AROT 0 0 0','AROT 90 0 0')
    if fixture == 'docked':
        pb += '  DOCKINFO 0:0,ISS\n'
    if fixture in ('ground','dg_orbit'):
        focus='DG'
        if fixture == 'ground':
            # Real terrain at Edwards, not a synthetic plane or visual LOD.
            pb='DG:DG-S\n  STATUS Landed Earth\n  POS -117.883 34.916\n  HEADING 90\n  GEAR 1 1.0000\n'
        else:
            pb=pb.replace('PB:ShuttlePB','DG:DG-S')+'  GEAR 0 0.0000\n  NOSECONE 0 0.0000\n'
        pb+='  TANKCONFIG 1\n  PRPLEVEL 0:0.8 1:1 2:1\n  RCSMODE 1\n  PSNGR 2 3 4\n'
    return ('BEGIN_DESC\nReduced production behavior fixture; not stock-corpus acceptance.\nEND_DESC\n'
            'BEGIN_ENVIRONMENT\n  System Sol\n  Date MJD 51982.5\nEND_ENVIRONMENT\n'
            f'BEGIN_FOCUS\n  Ship {focus}\nEND_FOCUS\nBEGIN_CAMERA\n'
            f'  TARGET {focus}\n  MODE Extern\n  POS 4 0 0\n  TRACKMODE TargetRelative\n  FOV 50\nEND_CAMERA\n'
            'BEGIN_SHIPS\n'+iss+pb+'END\nEND_SHIPS\n')


def rows(path):
    with path.open(newline='',encoding='ascii') as stream:
        reader=csv.DictReader(stream)
        result=list(reader)
        require(reader.fieldnames is not None,'missing behavior CSV header')
        require(all(None not in row and None not in row.values() for row in result),'malformed behavior CSV')
    return result


def validate(directory,case):
    states=rows(directory/'behavior-state.csv');events=rows(directory/'behavior-events.csv')
    require(states and events,'empty production observations')
    ticks=sorted(set(int(row['tick']) for row in states))
    expected=case['frames']-(3 if case['id']=='clock' else 0)
    require(ticks==list(range(expected+1)),'missing or nonfinalized physics ticks')
    for row in states:
        for key,value in row.items():
            if key not in ('object','class','dock','focus','attached'):
                require(math.isfinite(float(value)),'nonfinite production behavior state: '+key)
        m=[[float(row[f'm{i}{j}']) for j in range(1,4)] for i in range(1,4)]
        require(all(abs(sum(m[i][k]*m[j][k] for k in range(3))-(i==j))<=1e-12
                    for i in range(3) for j in range(3)),'invalid behavior rotation')
    require(events[-1]['phase']=='module.end','normal stock lifecycle termination missing')
    require(int(events[-1]['frame'])==case['frames'],'wrong application frame count')
    phases=[row['phase'] for row in events]
    for phase in ('vessel.setcaps.before','vessel.load.before','vessel.postcreation.before',
                  'vessel.pre.before','vessel.post.before','world.finalise.before','time.end.after'):
        require(phase in phases,'real production callback not observed: '+phase)
    for row in states:
        require(float(row['mass'])>0 and float(row['fuel'])>=0,'invalid stock mass/propellant')
    target='DG' if case['fixture'] in ('ground','dg_orbit','reload') else 'PB'
    own=[row for row in states if row['object']==target]
    require(len(own)==expected+1,'target stock vessel disappeared')
    identifier=case['id']
    if identifier=='rcs':
        used={row['detail'].split(':')[0] for row in events if row['phase']=='input.rcs'}
        require(set(map(str,range(12)))<=used,'not all production RCS groups exercised')
        require(float(own[-1]['fuel'])<float(own[0]['fuel']),'RCS groups consumed no fuel')
        for group in range(12):
            require(float(own[group*40+8]['fuel'])<float(own[group*40]['fuel']),
                    'RCS group consumed no propellant: '+str(group))
        require(max(distance([float(r[k]) for k in ('wx','wy','wz')],[0,0,0]) for r in own)>1e-8,'RCS caused no rotation')
    elif identifier=='autopilot':
        require(phases.count('input.navmode')==5 and any(int(r['navmask']) for r in own),'original autopilot modes not active')
    elif identifier=='atmosphere':
        require(max(float(r['density']) for r in own)>0 and max(float(r['drag']) for r in own)>0,
                'production atmosphere/aerodynamics not active')
    elif identifier in ('contact','landed'):
        require(any(r['ground']=='1' for r in own),'production ground contact not reached')
        require(any(abs(float(r['altitude_mean'])-float(r['altitude_agl']))>100 for r in own),
                'real nonzero Edwards terrain elevation was not queried')
    elif identifier=='docked':
        require(own[0]['dock']=='ISS' and own[-1]['dock']=='','stock dock/undock state missing')
        require('vessel.undock.before' in phases,'stock undocking callback missing')
    elif identifier=='dock_approach':
        require(own[0]['dock']=='' and any(r['dock']=='ISS' for r in own),'automatic production docking did not occur')
        require('vessel.dock.before' in phases,'stock docking callback missing')
    elif identifier=='attachments':
        require('input.attach' in phases and 'input.detach' in phases,'production attachment transition missing')
        require(any(r['attached']=='Child;' for r in own) and own[-1]['attached']=='',
                'real production attachment state did not attach/detach')
    elif identifier=='lifetime':
        require({'module.create','module.delete','module.focus'}<=set(phases),'stock lifetime/focus callbacks missing')
        require(any(r['object']=='Child' for r in states) and not any(r['object']=='Child' and int(r['tick'])>=31 for r in states),
                'deferred deletion did not remove the real vessel')
    elif identifier=='clock':
        require([r['detail'] for r in events if r['phase']=='module.pause']==['1','0'],'pause/resume notifications differ')
        require(phases.count('input.warp')==2,'time acceleration schedule missing')
    elif identifier.startswith('dg_'):
        require(all(r['class']=='DG-S' for r in own),'real DG-S module missing')
        animation=rows(directory/'behavior-animations.csv')
        require(animation,'stock DG animations missing')
        if identifier != 'dg_reload':
            values={}
            for row in animation:
                if row['object']=='DG':values.setdefault(row['index'],set()).add(row['state'])
            require(any(len(v)>1 for v in values.values()),'real DG keyboard controls caused no animation')
        if identifier=='dg_persistence':require((directory/'Scenarios/BehaviorSnapshot.scn').is_file(),'vessel-specific stock save missing')
    # Pair observations around each original vessel callback, including creation/deletion.
    stack=[]
    for row in events:
        phase=row['phase']
        if phase.startswith('vessel.') and phase.endswith('.before'):stack.append((phase[:-7],row['object']))
        elif phase.startswith('vessel.') and phase.endswith('.after'):
            require(stack and stack.pop()==(phase[:-6],row['object']),'vessel callback nesting/order differs')
    require(not stack,'unfinalized stock callback')
    return dict(states=len(states),events=len(events),physics_ticks=expected,frames=case['frames'],target=target,
                initial_fuel=float(own[0]['fuel']),final_fuel=float(own[-1]['fuel']))


def compare(reference,candidate,case):
    a,b=rows(reference/'behavior-state.csv'),rows(candidate/'behavior-state.csv')
    require(len(a)==len(b),'behavior sample counts differ')
    maxima=dict(position_m=0.,velocity_m_s=0.,rotation_rad=0.,angular_velocity_rad_s=0.,mjd_days=0.,mass_fraction=0.)
    contact=case['budgets']=='contact'
    limits=dict(position_m=1 if contact else .01,velocity_m_s=.1 if contact else 1e-5,
                rotation_rad=1e-3 if contact else 1e-8,angular_velocity_rad_s=1e-10,mjd_days=1e-10)
    for ref,got in zip(a,b):
        for key in ('tick','frame','seconds','object','class','dock','focus','navmask','ground','attached'):
            require(ref[key]==got[key],'discrete production behavior differs: '+key)
        def values(row,fields):return [float(row[k]) for k in fields]
        errors=dict(position_m=distance(values(ref,('rx','ry','rz')),values(got,('rx','ry','rz'))),
                    velocity_m_s=distance(values(ref,('vx','vy','vz')),values(got,('vx','vy','vz'))),
                    rotation_rad=quaternion_angle(quaternion(ref),quaternion(got)),
                    angular_velocity_rad_s=distance(values(ref,('wx','wy','wz')),values(got,('wx','wy','wz'))),
                    mjd_days=abs(float(ref['mjd'])-float(got['mjd'])))
        for key,value in errors.items():
            require(value<=limits[key],f'{case["id"]}: {key} exceeds predeclared budget')
            maxima[key]=max(maxima[key],value)
        for field in ('mass','fuel'):
            fraction=abs(float(ref[field])-float(got[field]))/max(1e-8,abs(float(ref[field]))*1e-8)
            require(fraction<=1,'production mass/propellant budget exceeded')
            maxima['mass_fraction']=max(maxima['mass_fraction'],fraction)
    require((reference/'behavior-events.csv').read_bytes()==(candidate/'behavior-events.csv').read_bytes(),
            'production inputs/callback sequence differs')
    for filename in ('behavior-propellant.csv','behavior-animations.csv'):
        left,right=rows(reference/filename),rows(candidate/filename)
        require(len(left)==len(right),'stock propellant/animation observation count differs')
        for ref,got in zip(left,right):
            for key in ref:
                if key in ('mass','capacity','state'):
                    budget=max(1e-8,abs(float(ref[key]))*1e-8) if key!='state' else 1e-12
                    require(abs(float(ref[key])-float(got[key]))<=budget,'stock resource/animation state differs')
                else:require(ref[key]==got[key],'stock resource identity differs')
    return maxima


def persistence_round_trip(saved,reloaded):
    """Measure the stock Windows format's documented decimal quantization."""
    before={r['object']:r for r in rows(saved/'behavior-state.csv') if r['tick']=='40'}
    after={r['object']:r for r in rows(reloaded/'behavior-state.csv') if r['tick']=='0'}
    require(before.keys()==after.keys(),'stock reload changed vessel identities')
    result={}
    for name,a in before.items():
        b=after[name]
        vector=lambda row,keys:[float(row[k]) for k in keys]
        p=distance(vector(a,('rx','ry','rz')),vector(b,('rx','ry','rz')))
        v=distance(vector(a,('vx','vy','vz')),vector(b,('vx','vy','vz')))
        q=quaternion_angle(quaternion(a),quaternion(b))
        # Vessel::Write: RPOS .3 m, RVEL .4 m/s, AROT .3 degrees.
        # Position allowance includes global-coordinate double subtraction.
        require(p<=math.sqrt(3)*.0005+.0001,'reload exceeds stock position serialization precision')
        require(v<=math.sqrt(3)*.00005+1e-8,'reload exceeds stock velocity serialization precision')
        require(q<=math.sqrt(3)*math.radians(.0005)+1e-8,'reload exceeds stock attitude serialization precision')
        require(abs(float(a['mjd'])-float(b['mjd']))<=1e-10,'finalized checkpoint epoch changed on reload')
        require(a['class']==b['class'] and a['dock']==b['dock'],'stock module/docking identity lost on reload')
        result[name]=dict(position_m=p,velocity_m_s=v,rotation_rad=q)
    a={(r['object'],r['index']):float(r['state']) for r in rows(saved/'behavior-animations.csv') if r['tick']=='40'}
    b={(r['object'],r['index']):float(r['state']) for r in rows(reloaded/'behavior-animations.csv') if r['tick']=='0'}
    require(a.keys()==b.keys(),'stock animation identities lost on reload')
    require(all(abs(value-b[key])<=.00005+1e-12 for key,value in a.items()),'stock .4-decimal animation state lost on reload')
    text=(saved/'Scenarios/BehaviorSnapshot.scn').read_text()
    require(all(token in text for token in ('GEAR ','NOSECONE ','PSNGR 2 3 4','TANKCONFIG 1')),
            'DG-specific persistence fields missing from stock serializer')
    return result


def stage(executable,data,planets,directory,case,reload):
    directory.mkdir()
    for p in executable.parent.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.exe'):shutil.copy2(p,directory/p.name)
    for name in ('Config','Modules','Meshes','Images','Script','Textures','Textures2'):
        source=executable.parent/name
        if source.is_dir():shutil.copytree(source,directory/name,copy_function=link_or_copy)
    # The production build tree puts all atmosphere DLLs in one folder when
    # CELBODY is unset. Reproduce their existing CMake install destinations.
    # These are the verified source-built binaries, never downloaded DLLs.
    for body,modules in {'Earth':('EarthAtm2006','EarthAtmJ71G','EarthAtmNRLMSISE00'),
                         'Mars':('MarsAtm2006',),'Venus':('VenusAtm2006',)}.items():
        for module in modules:
            target=directory/'Modules/Celbody'/body/'Atmosphere'/(module+'.dll')
            source=directory/'Modules/Celbody/Atmosphere'/(module+'.dll')
            require(source.is_file(),'required source-built atmosphere module missing: '+module)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name in ('Kernels','Textures','Textures2','GravityModels','Fonts'):
        require((data/name).is_dir(),'required production data directory missing: '+name)
        shutil.copytree(data/name,directory/name,dirs_exist_ok=True,copy_function=link_or_copy)
    planet_lock=json.loads(Path(__file__).with_name('standard-planets.lock.json').read_text())
    for name in planet_lock['data_files']:
        target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);link_or_copy(planets/name,target)
    scn=directory/'Scenarios';scn.mkdir()
    if case['fixture']=='reload':
        require(reload is not None,'production persistence checkpoint is required')
        shutil.copy2(reload,scn/'Behavior.scn')
    else:(scn/'Behavior.scn').write_text(scenario(case['fixture']),encoding='ascii')
    config=Path(__file__).with_name('Fixtures')/'Orbiter.cfg'
    text=config.read_text().replace('ProductionReferenceDriver','ProductionBehaviorDriver')
    text+='\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n'
    (directory/'Orbiter.cfg').write_text(text,encoding='ascii')
    (directory/'behavior-case.txt').write_text(f'{case["id"]} {case["frames"]} {case["fixed_step"]:.17g} {case["epoch"]:.17g}\n',encoding='ascii')
    argv=[str(directory/executable.name),'--scenariox=Behavior',f'--fixedstep={case["fixed_step"]:.17g}',f'--maxframes={case["frames"]}']
    (directory/'invocation.json').write_text(json.dumps(dict(argv=argv,case=case,
        input_sha256={p.relative_to(directory).as_posix():digest(p) for name in ('Config','Meshes','Scenarios')
                      for p in (directory/name).rglob('*') if p.is_file()},
        data_profiles={name:digest(Path(__file__).with_name(name)) for name in ('stock-data.lock.json','standard-planets.lock.json')}),indent=2)+'\n')
    with (directory/'console.txt').open('w') as console:
        subprocess.run(argv,cwd=directory,stdout=console,stderr=subprocess.STDOUT,check=True,timeout=240)
    require('Could not find a module' not in (directory/'Orbiter.log').read_text(errors='replace'),
            'required production module failed to load; fallback is prohibited')
    return validate(directory,case)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orbiter',type=Path);parser.add_argument('--data',type=Path)
    parser.add_argument('--planets',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--configuration',choices=('Debug','Release'))
    parser.add_argument('--case',action='append');parser.add_argument('--compare',type=Path)
    args=parser.parse_args()
    require(sys.platform=='win32' or args.compare is not None,'production behavioral capture requires native Windows')
    manifest=json.loads(Path(__file__).with_name('behavior-cases.json').read_text())
    require(not args.case or set(args.case)<={case['id'] for case in manifest['cases']},'unknown production behavior case')
    cases=[case for case in manifest['cases'] if not args.case or case['id'] in args.case]
    if args.compare:
        report={case['id']:compare(args.compare/case['id'],args.output/case['id'],case) for case in cases}
        (args.output/'cross-configuration.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2));return
    require(all((args.orbiter,args.data,args.planets,args.configuration)),
            'capture requires --orbiter, --data, --planets, and --configuration')
    verify_observation_source()
    require(not git('status','--porcelain','--untracked-files=no').strip(),'behavior capture requires committed sources')
    for name in ('stock-data.lock.json','standard-planets.lock.json'):
        profile=json.loads(Path(__file__).with_name(name).read_text());base=args.data if name.startswith('stock') else args.planets
        for path,entry in profile['data_files'].items():require(digest(base/path)==entry['sha256'],'incompatible behavior data: '+path)
    executable=args.orbiter.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    require((executable.parent/'Modules/Plugin/ProductionBehaviorDriver.dll').is_file(),'source-built production behavior driver missing')
    report=dict(status='candidate',source_commit=git('rev-parse','HEAD').decode().strip(),configuration=args.configuration,
                binary_sha256=digest(executable),case_manifest_sha256=digest(Path(__file__).with_name('behavior-cases.json')),cases={})
    runtime=executable.parent/'test-runtime.json'
    report['application_source_commit']=json.loads(runtime.read_text())['source_commit'] if runtime.exists() else report['source_commit']
    failures=[]
    try:
        for case in cases:
            name=case['id'];reload=output/'dg_persistence/Scenarios/BehaviorSnapshot.scn' if name=='dg_reload' else None
            try:
                first=stage(executable,args.data.resolve(),args.planets.resolve(),output/name,case,reload)
                repeated=stage(executable,args.data.resolve(),args.planets.resolve(),output/(name+'-repeat'),case,reload)
                report['cases'][name]=dict(first=first,repeat=repeated,comparison=compare(output/name,output/(name+'-repeat'),case))
                for filename in FILES:require((output/name/filename).read_bytes()==(output/(name+'-repeat')/filename).read_bytes(),'behavior repeat is not byte-identical: '+name+'/'+filename)
                if name=='dg_reload':report['stock_serialization_round_trip']=persistence_round_trip(output/'dg_persistence',output/name)
            except Exception as error:
                report['cases'][name]=dict(status='failed',error=str(error));failures.append(name)
                print(name+': '+str(error),flush=True)
        require(not failures,'production behavior cases failed: '+', '.join(failures))
        report['status']='repeatable-candidate; cross-configuration acceptance pending'
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:(output/'behavior-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
