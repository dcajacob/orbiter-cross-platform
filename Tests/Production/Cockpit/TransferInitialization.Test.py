#!/usr/bin/env python3
"""Verify exact Transfer MFD initialization/lifetime repairs and their negative controls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent))
from cockpit_source import restore_transfer_initialization,restore_transfer_rotation_lifetime,restore_transfer_finite_indicators


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',args.baseline):raise ValueError('Baseline must be an immutable full commit')
    if args.output.exists():raise ValueError('Source-control output already exists')
    path='Src/Orbiter/MfdTransfer.cpp'
    before=subprocess.check_output(['git','-C',str(ROOT),'show',args.baseline+':'+path]).replace(b'\r\n',b'\n')
    after=(ROOT/path).read_bytes().replace(b'\r\n',b'\n')
    marker=b'\tprocess_num = false;\n\n\tSetSize (spec);'
    replacement=b'\tprocess_num = false;\n\tdv_manip = false;\n\n\tSetSize (spec);'
    expression=b'RotMatrix (shpel2->coso, shpel2->sino, shpel2->cost, shpel2->sint, shpel2->cosi, shpel2->sini)'
    expected=before.replace(marker,replacement,1).replace(b'\tMatrix rot2, *workr;',b'\tMatrix rot2, rot3, *workr;',1)
    expected=expected.replace(b'\t\tMatrix rot3 ('+expression+b');',b'\t\trot3.Set ('+expression+b');',1)
    expected=expected.replace(b'#include "MfdTransfer.h"',b'#include "MfdTransfer.h"\n#include <cmath>',1)
    line=b'\t\t\tskp->Line (ICNTX, ICNTY, ICNTX+(int)(v.x*pixrad), ICNTY-(int)(v.z*pixrad));'
    guarded=b'\t\t\tif (std::isfinite(v.x) && std::isfinite(v.z))\n\t'+line
    if expected.count(line)!=2:raise ValueError('Original indicator draw sites changed')
    expected=expected.replace(line,guarded)
    if before.count(marker)!=1 or after!=expected:
        raise ValueError('Repair changed more than initialization, matrix lifetime and finite indicators')
    current=after.decode('cp1252');original=before.decode('cp1252')
    if restore_transfer_finite_indicators(restore_transfer_rotation_lifetime(restore_transfer_initialization(current)))!=original:raise ValueError('Canonical source restoration changed')
    rejected=[]
    for label,bad in [('removed',current.replace('\tprocess_num = false;\n\tdv_manip = false;','\tprocess_num = false;',1)),
                      ('inverted',current.replace('\tprocess_num = false;\n\tdv_manip = false;','\tprocess_num = false;\n\tdv_manip = true;',1))]:
        try:restore_transfer_initialization(bad)
        except ValueError:rejected.append(label)
        else:raise ValueError('Invalid initializer was accepted: '+label)
    try:restore_transfer_rotation_lifetime(current.replace('\tMatrix rot2, rot3, *workr;','\tMatrix rot2, *workr;',1))
    except ValueError:rejected.append('branch_local_matrix')
    else:raise ValueError('Shortened matrix lifetime was accepted')
    try:restore_transfer_finite_indicators(current.replace(guarded.decode(),line.decode(),1))
    except ValueError:rejected.append('unguarded_nonfinite_indicator')
    else:raise ValueError('Nonfinite indicator conversion was accepted')
    result=dict(status='passed',baseline_commit=args.baseline,exact_initialization_lifetime_and_finite_indicator_delta=True,
                original_calculations_and_valid_indicator_bytes_unchanged=True,rejected=rejected,
                baseline_sha256_lf=hashlib.sha256(before).hexdigest(),fixed_sha256_lf=hashlib.sha256(after).hexdigest())
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Initialization, lifetime and finite indicators verified; four negative controls rejected; calculations unchanged')


if __name__=='__main__':main()
