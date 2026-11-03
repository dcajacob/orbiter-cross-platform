#!/usr/bin/env python3
"""Compare original Lua scheduling, AAP controls and rendered vessel states."""
import argparse
import json
from pathlib import Path
from capture import settings,validate,require,mfd_images,rows
from compare import compare


def compare_captures(debug,release):
    config=settings()
    for root in (debug,release):
        require(json.loads((root/'lua-report.json').read_text())['status']=='passed','Failed Lua captures cannot be accepted')
    profiles=[json.loads((d/'lua-report.json').read_text()).get('math_profile','original-default') for d in (debug,release)]
    require(profiles[0]==profiles[1],'Original CRT profile changed between builds')
    results=compare(debug,release,config)
    divergence={}
    for case in config['cases']:
        directories=[root/(case['id']+'-1') for root in (debug,release)]
        for directory in directories:validate(directory,case)
        for name in ('lua-events.csv','lua-isolation.txt'):
            require((directories[0]/name).read_bytes()==(directories[1]/name).read_bytes(),'Original Lua execution differs: '+name)
        a,b=directories
        if (a/'lua-controls.csv').read_bytes()!=(b/'lua-controls.csv').read_bytes():
            differences=[]
            for x,y in zip(rows(a/'lua-controls.csv'),rows(b/'lua-controls.csv')):
                for key in ('elevator','aileron','main'):
                    if x[key]!=y[key]:
                        differences.append(dict(tick=int(x['tick']),control=key,debug=x[key],release=y[key]))
            divergence[case['id']]=dict(controls=differences,controller_inputs={build:rows(d/'lua-controller.csv') for build,d in zip(('Debug','Release'),directories)},
                pre_lua_horizon={build:rows(d/'lua-horizon.csv') for build,d in zip(('Debug','Release'),directories)})
    report=dict(status='failed' if divergence else 'passed',math_profile=profiles[0],cases=results,mfd_images=mfd_images(debug,release,config),exact_lua_execution=not divergence)
    if divergence:report['cross_build_differences']=divergence
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('debug','release','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    try:
        report=compare_captures(args.debug,args.release)
    except Exception as error:
        report=dict(status='failed',error=str(error),inputs={})
        for name,root in (('Debug',args.debug),('Release',args.release)):
            path=root/'lua-report.json'
            if path.is_file():
                try:
                    capture=json.loads(path.read_text())
                    report['inputs'][name]={key:capture.get(key) for key in
                        ('status','source','configuration','math_profile','host','failures')}
                except (ValueError,AttributeError) as invalid:
                    report['inputs'][name]=dict(status='invalid',path=str(path),error=str(invalid))
            else:
                report['inputs'][name]=dict(status='missing',path=str(path))
        args.output.write_text(json.dumps(report,indent=2)+'\n')
        raise
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    require(report['status']=='passed','Original Debug/Release Lua control traces differ')

if __name__=='__main__':main()
