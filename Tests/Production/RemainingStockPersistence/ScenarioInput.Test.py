#!/usr/bin/env python3
"""Preserve read-only stock copies and reject derived-input collisions."""
import argparse
import json
from pathlib import Path
import shutil
import stat
import tempfile

from capture_native import stage_scenario_input,sha


def rejected(action):
    try:action()
    except ValueError:return True
    return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert not args.output.exists()
    with tempfile.TemporaryDirectory(prefix='orbiter-scenario-input-') as folder:
        root=Path(folder);source=root/'original.scn'
        source.write_bytes(b'BEGIN_SHIPS\nISS:ProjectAlpha_ISS\nEND\nEND_SHIPS\n')
        source.chmod(0o444);target=root/'copied.scn';shutil.copy2(source,target)
        original=sha(source);copied=sha(target);mode=stat.S_IMODE(target.stat().st_mode)
        stage_scenario_input(source,target,'stock-writer')
        stage_scenario_input(source,target,'stock-writer')
        assert sha(source)==original and sha(target)==copied and stat.S_IMODE(target.stat().st_mode)==mode==0o444
        changed=root/'changed.scn';changed.write_bytes(source.read_bytes()+b'\n');changed.chmod(0o444)
        assert rejected(lambda:stage_scenario_input(source,changed,'stock-writer'))
        assert rejected(lambda:stage_scenario_input(source,root/'missing.scn','stock-writer'))
        saved=root/'Windows saved input.scn'
        saved.write_bytes(b'BEGIN_DESC\r\nExact saved bytes: \xff\r\nEND_DESC\r\n')
        saved.chmod(0o444)
        derived=root/'Scenarios/_Phase6Persistence/exact.scn'
        stage_scenario_input(saved,derived,'windows-save-reload')
        assert sha(derived)==sha(saved) and derived.read_bytes()==saved.read_bytes()
        assert rejected(lambda:stage_scenario_input(saved,derived,'windows-save-reload'))
        link=root/'dangling.scn';link.symlink_to(root/'not-present.scn')
        assert rejected(lambda:stage_scenario_input(source,link,'windows-save-reload'))
        assert rejected(lambda:stage_scenario_input(source,target,'unknown'))
        assert sha(source)==original and sha(target)==copied
    result=dict(status='passed',source_sha256=sha(Path(__file__)),read_only_stock_mode_and_bytes_preserved=True,
                repeated_stock_staging_preserved=True,exact_derived_input_written=True,
                rejected_controls=['changed_stock_copy','missing_stock_copy','existing_derived_input',
                                   'dangling_derived_symlink','unknown_phase'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Read-only stock input preserved; five damaged/colliding inputs rejected')


if __name__=='__main__':main()
