#!/usr/bin/env python3
"""Compare original Lua scheduling, AAP controls and rendered vessel states."""
import argparse
import json
from pathlib import Path
from capture import settings,validate,require,mfd_images
from compare import compare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('debug','release','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();config=settings()
    for root in (args.debug,args.release):
        require(json.loads((root/'lua-report.json').read_text())['status']=='passed','Failed Lua captures cannot be accepted')
    results=compare(args.debug,args.release,config)
    for case in config['cases']:
        directories=[root/(case['id']+'-1') for root in (args.debug,args.release)]
        for directory in directories:validate(directory,case)
        for name in ('lua-events.csv','lua-controls.csv','lua-isolation.txt'):
            require((directories[0]/name).read_bytes()==(directories[1]/name).read_bytes(),'Original Lua execution differs: '+name)
    report=dict(status='passed',cases=results,mfd_images=mfd_images(args.debug,args.release,config),exact_lua_execution=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
