#!/usr/bin/env python3
"""Compare original Lua scheduling, AAP controls and rendered vessel states."""
import argparse
import json
from pathlib import Path
from capture import settings,validate,require,mfd_images,rows
from compare import compare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('debug','release','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();config=settings()
    for root in (args.debug,args.release):
        require(json.loads((root/'lua-report.json').read_text())['status']=='passed','Failed Lua captures cannot be accepted')
    results=compare(args.debug,args.release,config)
    divergence={}
    for case in config['cases']:
        directories=[root/(case['id']+'-1') for root in (args.debug,args.release)]
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
            divergence[case['id']]=dict(controls=differences,controller_inputs={build:rows(d/'lua-controller.csv') for build,d in zip(('Debug','Release'),directories)})
    report=dict(status='failed' if divergence else 'passed',cases=results,mfd_images=mfd_images(args.debug,args.release,config),exact_lua_execution=not divergence)
    if divergence:report['cross_build_differences']=divergence
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    require(not divergence,'Original Debug/Release Lua control traces differ')

if __name__=='__main__':main()
