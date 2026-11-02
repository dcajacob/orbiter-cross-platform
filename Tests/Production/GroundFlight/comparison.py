"""Agreed contact budgets for PB; unchanged orbital budgets for the orbiting ISS."""
import json,math
from pathlib import Path
from behavior_suite import rows,distance,quaternion,quaternion_angle
from mesa_runtime import require
MANIFEST=json.loads(Path(__file__).with_name('cases.json').read_text())
def transitions(states):return [int(b['tick']) for a,b in zip(states,states[1:]) if a['ground']!=b['ground']]

def compare_states(reference,candidate):
    old,new=rows(reference),rows(candidate)
    require(len(old)==len(new),'Ground-flight state sample count differs')
    maxima=dict(position_m=0.,velocity_m_s=0.,rotation_rad=0.,angular_velocity_rad_s=0.,mjd_days=0.,mass_fraction=0.)
    events={}
    for name in ('ISS','PB'):
        a=[r for r in old if r['object']==name];b=[r for r in new if r['object']==name]
        require(a and b,'Required original stock object missing: '+name)
        left,right=transitions(a),transitions(b)
        require(len(left)==len(right) and all(abs(x-y)<=MANIFEST['budgets']['contact_event_tick'] for x,y in zip(left,right)),
                'Terrain contact events differ by more than one recorded tick')
        require(a[0]['ground']==b[0]['ground'] and a[-1]['ground']==b[-1]['ground'],'Initial/final ground state differs')
        events[name]=dict(windows=left,candidate=right)
    for ref,got in zip(old,new):
        for key in ('tick','frame','seconds','object','class','dock','focus','navmask','attached'):
            require(ref[key]==got[key],'Discrete ground-flight state differs: '+key)
        limits=MANIFEST['orbital_budgets'] if ref['object']=='ISS' else MANIFEST['budgets']
        vector=lambda row,fields:[float(row[k]) for k in fields]
        errors=dict(position_m=distance(vector(ref,('rx','ry','rz')),vector(got,('rx','ry','rz'))),
                    velocity_m_s=distance(vector(ref,('vx','vy','vz')),vector(got,('vx','vy','vz'))),
                    rotation_rad=quaternion_angle(quaternion(ref),quaternion(got)),
                    angular_velocity_rad_s=distance(vector(ref,('wx','wy','wz')),vector(got,('wx','wy','wz'))),
                    mjd_days=abs(float(ref['mjd'])-float(got['mjd'])))
        for key,value in errors.items():
            require(math.isfinite(value),'Nonfinite ground-flight comparison')
            if key in limits:require(value<=limits[key],f'{ref["object"]} tick {ref["tick"]}: {key} exceeds {limits[key]}: {value}')
            maxima[key]=max(maxima[key],value)
        for field in ('mass','fuel'):
            fraction=abs(float(ref[field])-float(got[field]))/max(MANIFEST['budgets']['propulsion_absolute_kg'],abs(float(ref[field]))*MANIFEST['budgets']['propulsion_relative'])
            require(fraction<=1,'Ground propulsion mass/propellant budget exceeded')
            maxima['mass_fraction']=max(maxima['mass_fraction'],fraction)
    return dict(maxima=maxima,contact_events=events)

def compare_windows(reference,candidate):
    result=compare_states(reference/'behavior-state.csv',candidate/'behavior-state.csv')
    require((reference/'behavior-events.csv').read_bytes()==(candidate/'behavior-events.csv').read_bytes(),
            'Original Windows input/callback sequence differs')
    for name in ('behavior-propellant.csv','behavior-animations.csv'):
        left,right=rows(reference/name),rows(candidate/name)
        require(len(left)==len(right),'Original resource/animation sample counts differ')
        for a,b in zip(left,right):
            for key in a:
                if key in ('mass','capacity','state'):
                    limit=1e-12 if key=='state' else max(1e-8,abs(float(a[key]))*1e-8)
                    require(abs(float(a[key])-float(b[key]))<=limit,'Original resource/animation value differs')
                else:require(a[key]==b[key],'Original resource/animation identity differs')
    return result
