#!/usr/bin/env python3
"""Preserve read-only stock copies and reject derived-input collisions."""
import argparse
import json
from pathlib import Path
import shutil
import stat
import tempfile

from capture_native import stage_asset_tree,stage_scenario_input,sha,PrivateAssetCache


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
        assets=root/'assets';scenario=assets/'Scenarios/Space Shuttle Atlantis/original.scn'
        scenario.parent.mkdir(parents=True);scenario.write_bytes(source.read_bytes())
        cfg=assets/'Orbiter.cfg';cfg.write_bytes(b'Original configuration\n')
        for path in (scenario,cfg):path.chmod(0o444)
        source_hashes={path.relative_to(assets).as_posix():sha(path) for path in (scenario,cfg)}
        source_directories=[assets,assets/'Scenarios',scenario.parent]
        for path in source_directories:path.chmod(0o555)
        staged=root/'private-world';stage_asset_tree(assets,staged)
        stage_scenario_input(scenario,staged/scenario.relative_to(assets),'stock-writer')
        private_cfg=staged/'Orbiter.cfg';private_cfg.unlink();private_cfg.write_bytes(b'Private test configuration\n')
        for name in ('finalized-frame.json','persistence-replay.csv','persistence-input.json'):
            (staged/name).write_bytes(b'Private test evidence\n')
        stage_scenario_input(saved,staged/'Scenarios/_Phase6Persistence/exact.scn','windows-save-reload')
        assert stat.S_IMODE((staged/scenario.relative_to(assets)).stat().st_mode)==0o444
        assert all(stat.S_IMODE((staged/path.relative_to(assets)).stat().st_mode)==0o755 for path in source_directories)
        assert all(stat.S_IMODE(path.stat().st_mode)==0o555 for path in source_directories)
        assert all(sha(assets/name)==value for name,value in source_hashes.items())
        cache_root=root/'cache-owner';cache_root.mkdir()
        cache=PrivateAssetCache({str(assets/name):value for name,value in source_hashes.items()},cache_root)
        controls=cache.controls(assets,'Orbiter.cfg')
        for name in ('one','two'):
            world=cache_root/name;stage_asset_tree(assets,world,cache)
            stage_scenario_input(scenario,world/scenario.relative_to(assets),'stock-writer')
            cfg=world/'Orbiter.cfg';cfg.unlink();cfg.write_bytes(b'Private test configuration\n')
            stage_scenario_input(saved,world/'Scenarios/_Phase6Persistence/exact.scn','windows-save-reload')
            assert (world/scenario.relative_to(assets)).read_bytes()==scenario.read_bytes()
        one=cache_root/'one'/scenario.relative_to(assets);two=cache_root/'two'/scenario.relative_to(assets)
        assert one.stat().st_ino==two.stat().st_ino and one.stat().st_ino!=scenario.stat().st_ino
        assert not cache.fallback and all(sha(assets/name)==value for name,value in source_hashes.items())
        cache.close()
        # TemporaryDirectory must be able to remove this deliberately read-only source tree.
        for path in source_directories:path.chmod(0o755)
    result=dict(status='passed',source_sha256=sha(Path(__file__)),read_only_stock_mode_and_bytes_preserved=True,
                repeated_stock_staging_preserved=True,exact_derived_input_written=True,
                read_only_asset_sources_and_scenario_preserved=True,private_directory_and_evidence_staging_passed=True,
                private_cached_links_share_no_canonical_file_records=True,private_cached_controls=controls,
                rejected_controls=['changed_stock_copy','missing_stock_copy','existing_derived_input',
                                   'dangling_derived_symlink','unknown_phase'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Read-only stock input preserved; five damaged/colliding inputs rejected')


if __name__=='__main__':main()
