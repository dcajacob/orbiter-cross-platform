#!/usr/bin/env python3
"""Measure then restore the exact original API reference once, with unchanged readers."""
import json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import require,load,sha,atomic_json
import measured_admission_reference as original
from frozen_admission_api import candidate,REFERENCE,hosted


def main():
    hosted();lock=candidate();folder=ROOT/'out/admission-reference-source';folder.mkdir(parents=True,exist_ok=False)
    path=original.source_archive(folder)
    measured=original.index_archive(path,lock,folder)
    atomic_json(folder/'measured-capacity.json',dict(status='measured-original-reference-only',**measured))
    require(original.index_archive(path,lock,folder,measured)==measured,'All actual original reference bodies must match the independently measured capacity')
    sys.path.insert(0,str(ROOT/'Tests/Production/GeneralApiCorrection'))
    import qualification
    require(len(qualification.inspect(REFERENCE)['evidence_sha256'])==1125,'Unchanged independent reference reader must verify every original guard')
    atomic_json(folder/'restored.json',dict(status='restored-exact-historical-reference-for-new-version-comparison',original_candidate_id=lock['id'],physics_version='assembly-contact-v2',
        original_reference_sha256=sha(REFERENCE),actual_original_guards=1125,materialized_files=len(measured['members']),unique_file_bytes=measured['unique_file_bytes'],eight_GiB_reserve=True,qualification_granted=False))


if __name__=='__main__':main()
