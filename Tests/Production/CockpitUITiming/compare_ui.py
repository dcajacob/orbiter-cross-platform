#!/usr/bin/env python3
"""Compare original Windows UI captures using the frozen cockpit budgets."""
import argparse
import json
from pathlib import Path
from capture import settings, validate, require, mfd_images
from compare import compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('debug','release','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    config = settings()
    for root in (args.debug, args.release):
        require(json.loads((root/'ui-report.json').read_text())['status'] == 'passed', 'Failed UI captures cannot be accepted')
    results = compare(args.debug,args.release,config)
    for case in config['cases']:
        directories = [root/(case['id']+'-1') for root in (args.debug,args.release)]
        for directory in directories:
            validate(directory,case)
        for name in ('ui-inputs.csv','ui-state.csv','ui-callbacks.csv'):
            require((directories[0]/name).read_bytes() == (directories[1]/name).read_bytes(), 'Original UI differs across configurations: '+name)
    report = dict(status='passed',cases=results,mfd_images=mfd_images(args.debug,args.release,config),exact_ui=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
