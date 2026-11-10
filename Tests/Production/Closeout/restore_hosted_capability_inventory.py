#!/usr/bin/env python3
"""Inspect the exact published SDK inventory and its original source/control closure."""
import hashlib
import stat
import subprocess
import zipfile
from pathlib import PurePosixPath
from hosted_native_package import ROOT,load,require,sha
from contracts import atomic_json
from hosted_class_capabilities import reference_inventory,INVENTORY_SOURCE


def main():
    base=ROOT/'out/class-capability-inventory';api=load(base/'api.json');archive=base/'producer.zip'
    require(api['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and
            api['run']['id']==42754222747 and api['run']['head_sha']==INVENTORY_SOURCE and
            api['run']['status']=='completed' and api['run']['conclusion']=='success' and api['run']['run_attempt']==1 and
            api['artifact']['id']==13734667876 and api['artifact']['workflow_run']['head_sha']==INVENTORY_SOURCE and
            api['artifact']['size_in_bytes']==archive.stat().st_size==68946 and
            api['artifact']['digest']=='sha256:'+sha(archive)=='sha256:103eb95d3b2da79fe0366dea26bfdf6b55d419cac3287ab3a6acad9cfbae5c24',
            'Exact actual published SDK inventory API/source/digest required')
    seen=set();bodies={};members={}
    with zipfile.ZipFile(archive) as incoming:
        require(len(incoming.infolist())<20 and sum(i.file_size for i in incoming.infolist())<3000000,'Bounded inventory metadata required')
        for info in incoming.infolist():
            name=info.filename;p=PurePosixPath(name)
            require(not info.is_dir() and name and str(p)==name and not p.is_absolute() and '..' not in p.parts and
                    ':' not in name and '\\' not in name and name.casefold() not in seen and not stat.S_ISLNK(info.external_attr>>16),
                    'Unsafe duplicate or nonregular inventory member')
            seen.add(name.casefold());bodies[name]=incoming.read(info);members[name]=hashlib.sha256(bodies[name]).hexdigest()
    import json
    controls=json.loads(bodies['capability-reference-controls.json'])
    require(controls['status']=='passed' and controls['tests_run']==336 and controls['failures']==controls['errors']==controls['skipped']==0 and
            controls['sources_match_producer'] is True and controls['producer_commit']==INVENTORY_SOURCE,
            'Every original reference-reader control must have passed at its immutable source')
    for absolute,value in controls['sources_sha256'].items():
        name=PurePosixPath(absolute).relative_to('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform').as_posix()
        require(PurePosixPath(name).parts[0]=='Tests' and '..' not in PurePosixPath(name).parts and
                hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show',INVENTORY_SOURCE+':'+name])).hexdigest()==value,
                'Published reference helper source differs from its immutable commit')
    destination=base/'reference';require(not destination.exists(),'Fresh inventory inspection required');destination.mkdir()
    (destination/'inventory.json').write_bytes(bodies['hosted-original-capability-inventory/inventory.json'])
    report=reference_inventory()
    require(len(report['reference_files_sha256'])==612 and len(report['full_17_field_variants_not_in_original_nine_cases'])==5,
            'Complete original four-profile SDK/descriptor/parent inventory required')
    atomic_json(base/'restoration.json',dict(status='restored-exact-published-original-full-SDK-inventory-only',
        producer=INVENTORY_SOURCE,api_sha256=sha(base/'api.json'),archive_sha256=sha(archive),members_sha256=members,
        inventory_sha256=sha(destination/'inventory.json'),normal_admission_qualified=False,phase6_complete=False))
    print('Original full SDK inventory and complete original helper source closure verified; all runtime facets remain pending')


if __name__=='__main__':main()
