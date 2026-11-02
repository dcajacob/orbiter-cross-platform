#!/usr/bin/env python3
"""Apply existing orbital/image budgets and exact original control input checks."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
from compare import compare as cockpit_compare
from mesa_runtime import require
from behavior_suite import rows
from regression import mfd_images
from capture import settings,validate

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('debug','release','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();config=settings()
    for directory in (a.debug,a.release):require(json.loads((directory/'control-report.json').read_text())['status']=='passed','Failed original controls cannot be accepted')
    results=cockpit_compare(a.debug,a.release,config)
    for case in config['cases']:
        directories=[root/(case['id']+'-1') for root in (a.debug,a.release)]
        for directory in directories:validate(directory,case)
        for name in ('control-inputs.csv','control-landmarks.csv'):
            require((directories[0]/name).read_bytes()==(directories[1]/name).read_bytes(),'Original control inputs or projected landmarks differ between Windows configurations')
        require([r['rcs_mode'] for r in rows(directories[0]/'cockpit-state.csv')]==[r['rcs_mode'] for r in rows(directories[1]/'cockpit-state.csv')],'Original actual vessel control state differs')
    report=dict(status='passed',cases=results,mfd_texture_comparison=mfd_images(a.debug,a.release,config),exact_discrete_inputs_and_rcs_modes=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
