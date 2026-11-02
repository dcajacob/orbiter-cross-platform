#!/usr/bin/env python3
"""Apply predeclared cockpit budgets to original Windows Debug/Release runs."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'Tests/Production'),str(ROOT/'Tests/Production/Client')]
from behavior_suite import rows,distance,quaternion,quaternion_angle
from mesa_runtime import require
from compare_client import image_ssim
def compare(debug,release,settings):
    budgets=settings['budgets'];results={}
    for case in settings['cases']:
        name=case['id'];a=debug/(name+'-1');b=release/(name+'-1')
        left,right=rows(a/'cockpit-state.csv'),rows(b/'cockpit-state.csv')
        require(len(left)==len(right)==61,'Incomplete original cockpit state sequence')
        maxima=dict(position_m=0.,velocity_m_s=0.,rotation_rad=0.,angular_velocity_rad_s=0.,mjd_days=0.,propellant_fraction=0.)
        for x,y in zip(left,right):
            for key in ('tick','seconds','object','class','cockpit','hud','left_mfd','right_mfd','meshes','thrusters'):require(x[key]==y[key],'Original discrete cockpit state differs: '+key)
            vector=lambda row,keys:[float(row[k]) for k in keys]
            errors={'position_m':distance(vector(x,('x','y','z')),vector(y,('x','y','z'))),
                    'velocity_m_s':distance(vector(x,('vx','vy','vz')),vector(y,('vx','vy','vz'))),
                    'rotation_rad':quaternion_angle(quaternion(x),quaternion(y)),
                    'angular_velocity_rad_s':distance(vector(x,('wx','wy','wz')),vector(y,('wx','wy','wz'))),
                    'mjd_days':abs(float(x['mjd'])-float(y['mjd']))}
            for k,v in errors.items():require(v<=budgets[k],'Original cockpit budget exceeded: '+k);maxima[k]=max(maxima[k],v)
            for key in ('mass','fuel'):
                ratio=abs(float(x[key])-float(y[key]))/max(budgets['propellant_absolute_kg'],abs(float(x[key]))*budgets['propellant_relative'])
                require(ratio<=1,'Original cockpit mass/propellant budget exceeded');maxima['propellant_fraction']=max(maxima['propellant_fraction'],ratio)
        require((a/'instrument-text.csv').read_bytes()==(b/'instrument-text.csv').read_bytes(),'Original displayed instrument values/order differ between configurations')
        images={str(frame):image_ssim((a/f'instrument-{frame}.rgba').read_bytes(),(b/f'instrument-{frame}.rgba').read_bytes(),1280,720) for frame in (20,50)}
        require(all(v>=settings['image_ssim_minimum'] for v in images.values()),'Original cockpit images exceed predeclared budget')
        results[name]=dict(maxima=maxima,identical_display_text=True,ssim=images)
    return results
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('debug','release','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();settings=json.loads(Path(__file__).with_name('cases.json').read_text())
    for directory in (a.debug,a.release):require(json.loads((directory/'cockpit-report.json').read_text())['status']=='passed','Failed original probe cannot be accepted')
    report={'status':'passed','cases':compare(a.debug,a.release,settings)};a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
