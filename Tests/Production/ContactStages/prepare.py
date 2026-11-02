#!/usr/bin/env python3
"""Instrument an isolated source copy, retaining every original calculation byte.

Never point this at the working checkout. Windows uses the frozen source clone;
Linux uses --native-overlay. This is not an accepted executable or a reference.
"""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ORIGINAL='0a5b9bd68dee7a0c702c021eb9fcac5243bc9df1e1319de4c0ace9e4d23f205b'

def sha(data):return hashlib.sha256(data).hexdigest()

def row(stage,fields,point='-1',call='contact_trace'):
    entries=', '.join('{"'+name+'", '+value+'}' for name,value in fields)
    return '\n\tcontact_stages::Row('+call+', "'+stage+'", '+point+', {'+entries+'});\n'

def vector(prefix,value):return [(prefix+'_'+axis,value+'.'+axis) for axis in ('x','y','z')]
def matrix(prefix,value):return [(prefix+str(i)+str(j),value+'.m'+str(i)+str(j)) for i in range(1,4) for j in range(1,4)]

def instrument(original):
    source=original
    changes=[]
    def insert(anchor,addition,before=False):
        nonlocal source
        if source.count(anchor)!=1:raise ValueError('Diagnostic anchor is not unique: '+anchor[:100])
        replacement=addition+anchor if before else anchor+addition
        source=source.replace(anchor,replacement);changes.append((replacement,anchor))
    include='#include "ContactStageObservation.h"\n'
    source=include+source
    start='bool Vessel::AddSurfaceForces (Vector *F, Vector *M, const StateVectors *s, double tfrac, double dt, bool allow_groundcontact) const\n{'
    insert(start,'\n\tconst auto contact_trace = contact_stages::Begin(GetRigidBodyServices().Time().SimT1, tfrac, dt, Name());\n')
    insert('\tsurfp.Set (*s, ps, proxybody, &etile, &windp); // intermediate surface parameters',row('surface',
        [('mass','mass'),('allow_contact','allow_groundcontact'),('proxy_update','proxyT'),('comms_update','commsT'),
         ('alt','surfp.alt'),('longitude','surfp.lng'),('latitude','surfp.lat'),
         ('radius','surfp.rad'),('sin_lng','surfp.slng'),('cos_lng','surfp.clng'),('sin_lat','surfp.slat'),('cos_lat','surfp.clat'),
         ('elevation','surfp.elev')]+vector('position','s->pos')+vector('velocity','s->vel')+vector('omega','s->omega')+
        matrix('vessel','s->R')+vector('planet_position','ps.pos')+vector('planet_velocity','ps.vel')+matrix('planet','ps.R')+
        vector('ground_velocity','surfp.groundvel_ship')+vector('normal','surfp.surfnml')+matrix('horizon','surfp.L2H')+
        vector('extra_force','(*F)')+vector('extra_moment','(*M)')+
        [('q_x','s->Q.qvx'),('q_y','s->Q.qvy'),('q_z','s->Q.qvz'),('q_s','s->Q.qs'),
         ('density','surfp.atmrho'),('pressure','surfp.atmp'),('temperature','surfp.atmT'),('dynamic_pressure','surfp.dynp')]))
    insert('\t\ttdy[i] = rad - elev - proxybody->Size();',row('vertex',
        vector('planet_local','p')+[('longitude','lng'),('latitude','lat'),('radius','rad'),('elevation','elev'),('depth','tdy[i]')],'i'))
    insert('\tVector d2h (crossp (hn, d1h));',row('axes',
        [('mass_dt','massdt')]+vector('normal','hn')+vector('longitudinal','d1h')+vector('lateral','d2h')+matrix('transform','T')))
    insert('\t\t\t\tfn_tot += fn[i];\n\n\t\t\t\t// debug',row('reaction',
        vector('ground_velocity','gv')+[('normal_speed','gv_n'),('longitudinal_speed','gv_lon'),('lateral_speed','gv_lat'),
         ('normal_force','fn[i]'),('longitudinal_force','flng[i]'),('lateral_force','flat[i]'),('depth','tdy[i]')],'i'),before=False)
    insert('\t\tVector M_surf, F_surf = hn*fn_tot + d1h*flng_tot + d2h*flat_tot;',row('limited',
        [('normal_speed','gv_n'),('longitudinal_speed','gv_lon'),('lateral_speed','gv_lat'),('normal_force','fn_tot'),
         ('longitudinal_force','flng_tot'),('lateral_force','flat_tot')]+vector('force','F_surf')))
    insert('\t\t*F += F_surf;\n\t\t*M += M_surf;',row('result',
        vector('force','F_surf')+vector('moment','M_surf')+vector('angle_change','dA')+[('angle_magnitude','da')]))
    gravity='\tRigidBody::GetIntermediateMoments (acc, tau, state, tfrac, dt);  // get gravitational component'
    completed=gravity+'\n\tacc += mul (state.Q, F/mass);\n\ttau += M/mass;'
    insert(completed,row('acceleration',vector('acceleration','acc')+vector('torque_per_mass','tau'),call='contact_stages::Current()'))
    insert(gravity,row('gravity',vector('acceleration','acc')+vector('torque_per_mass','tau')+
        vector('force','F')+vector('moment','M')+[('mass','mass'),('gravity_update','gfielddata.updt'),
        ('gravity_source_count','gfielddata.ngrav'),('gravity_next_candidate','gfielddata.testidx')]+
        [('gravity_source_'+str(i),'gfielddata.ngrav>'+str(i)+' ? gfielddata.gravidx['+str(i)+'] : -1.') for i in range(4)],call='contact_stages::Current()'))
    # Exact inverse proof: additions are known observations, not replacements
    # of any arithmetic, conditions, staging, assignment or return statements.
    recovered=source.removeprefix(include)
    for replacement,anchor in reversed(changes):
        if recovered.count(replacement)!=1:raise ValueError('Cannot prove diagnostic insertion is reversible')
        recovered=recovered.replace(replacement,anchor)
    if recovered!=original:raise ValueError('Diagnostic preparation changed original calculation bytes')
    return source

def overlay(destination):
    if destination.exists():raise ValueError('Diagnostic overlay must be a new directory')
    destination.mkdir(parents=True)
    for name in ('Orbitersdk','Tests','Extern'):(destination/name).symlink_to(ROOT/name,target_is_directory=True)
    (destination/'Src/Orbiter').mkdir(parents=True)
    for path in (ROOT/'Src').iterdir():
        if path.name!='Orbiter':(destination/'Src'/path.name).symlink_to(path,target_is_directory=path.is_dir())
    for path in (ROOT/'Src/Orbiter').iterdir():
        target=destination/'Src/Orbiter'/path.name
        if path.name=='Production':shutil.copytree(path,target)
        elif path.name=='Vessel.cpp':shutil.copy2(path,target)
        else:target.symlink_to(path,target_is_directory=path.is_dir())

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--native-overlay',action='store_true');a=p.parse_args();source=a.source.resolve()
    if (ROOT/'out').resolve() not in source.parents:
        raise ValueError('Instrumentation requires an isolated out/ source copy')
    if a.native_overlay:overlay(source)
    path=source/'Src/Orbiter/Vessel.cpp';original=path.read_bytes().replace(b'\r\n',b'\n')
    if sha(original)!=ORIGINAL:raise ValueError('Unexpected production contact source; review new anchors explicitly')
    prepared=instrument(original.decode('cp1252')).encode('cp1252');path.write_bytes(prepared)
    shutil.copy2(HERE/'Observation.h',path.with_name('ContactStageObservation.h'))
    record=dict(diagnostic_only=True,original_sha256_lf=sha(original),instrumented_sha256_lf=sha(prepared),
        observer_sha256=sha((HERE/'Observation.h').read_bytes()),insertions_reversible=True,
        source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        time_windows_seconds=[[0,41]])
    (source/'contact-instrumentation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
