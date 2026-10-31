#!/usr/bin/env python3
"""Verify accepted real-client provenance and files. No reference refresh path."""
import argparse
import json
from pathlib import Path

from mesa_runtime import digest,require

ROOT=Path(__file__).resolve().parent


def verify(directory,artifacts=None):
    metadata=json.loads((directory/'provenance.json').read_text())
    require(metadata['status']=='accepted' and metadata['automatic_refresh'] is False,'client reference is not accepted')
    for name,checksum in metadata['input_profiles_sha256'].items():
        require(digest(ROOT/name)==checksum,'accepted client input profile changed: '+name)
    for name,checksum in metadata['reference_files_sha256'].items():
        path=(directory/name).resolve()
        require(directory.resolve() in path.parents and digest(path)==checksum,'accepted client evidence changed: '+name)
    require(metadata['budgets']==dict(position_m=.01,velocity_m_s=1e-5,rotation_rad=1e-8,
        angular_velocity_rad_s=1e-10,mjd_days=1e-10,mass_relative=1e-8,mass_absolute_kg=1e-8,
        projected_landmark_pixels=1.,ssim_minimum=.98),'accepted client budgets changed')
    if artifacts:
        for entry in metadata['artifacts'].values():
            require(digest(artifacts/(entry['name']+'.zip'))==entry['sha256'],'accepted original artifact ZIP changed')
    return dict(status='passed',run_id=metadata['run_id'],source_commit=metadata['source_commit'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=ROOT/'ClientReference')
    parser.add_argument('--artifacts',type=Path)
    args=parser.parse_args();print(json.dumps(verify(args.reference,args.artifacts),indent=2))
