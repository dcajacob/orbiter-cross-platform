#!/usr/bin/env python3
"""Stage explicit repaired module sources while retaining the untouched Windows baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
sys.path[:0]=[str(HERE.parent),str(HERE.parent/'RemainingStock')]
from Dragonfly.source_audit import verify as verify_dragonfly
from Atlantis.source_audit import verify as verify_atlantis
from inputs import settings


def digest(body):return hashlib.sha256(body).hexdigest()


def git(*arguments):return subprocess.check_output(['git','-C',str(ROOT),*arguments])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve()
    if a.output.exists():raise ValueError('Repaired module source output exists; replacement forbidden')
    config=settings();verify_atlantis();verify_dragonfly()
    if config['application_source']!=BASE or len(config['cases'])!=38:
        raise ValueError('Complete original scene source closure differs')
    producer=git('rev-parse','HEAD').decode().strip()
    paths=git('ls-tree','-r','--name-only',BASE,'--','Src/Vessel/Atlantis','Src/Vessel/Dragonfly').decode().splitlines()
    if not paths:raise ValueError('Original module sources unavailable')
    original={name:git('show',BASE+':'+name) for name in paths}
    modified=dict(original)
    tank='Src/Vessel/Atlantis/Atlantis_Tank/Atlantis_Tank.cpp'
    text=original[tank].decode('cp1252').replace('\r\n','\n')
    old='\tif (GetAltitude() < 0.0) oapiDeleteVessel (GetHandle());'
    if text.count(old)!=1:raise ValueError('Original tank lifetime callback changed')
    modified[tank]=text.replace(old,
        '\t// The orbiter owns this propellant while connected, including on the pad.\n'
        '\tif (!GetDockStatus (GetDockHandle (0)) && GetAltitude() < 0.0)\n'
        '\t\toapiDeleteVessel (GetHandle());').encode('cp1252')
    # Keep the original Windows Atlantis header and ABI spellings. The native
    # port's aliases/factories are not copied into the preserved-SDK variant.
    dragonfly=['Src/Vessel/Dragonfly/'+name for name in
               ('instruments.cpp','instruments.h','WglContext.h','WglBitmapTarget.h','Esystems.cpp')]
    producer_sources={}
    for name in dragonfly:
        body=git('show',producer+':'+name)
        if body.replace(b'\r\n',b'\n')!=(ROOT/name).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Repaired source differs from immutable producer: '+name)
        modified[name]=body;producer_sources[name]=digest(body)
    a.output.mkdir(parents=True)
    source=a.output/'source';source.mkdir()
    for name,body in modified.items():
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
    changes={name:dict(original_sha256=digest(original[name]) if name in original else None,
                       repaired_sha256=digest(body)) for name,body in modified.items() if original.get(name)!=body}
    if set(changes)!={tank,*dragonfly}:
        raise ValueError('Module source variant differs beyond the exact lifetime/platform/initial-state repairs')
    for name,body in modified.items():
        if (source/name).read_bytes()!=body:raise ValueError('Staged source copy differs: '+name)
    for name in paths:
        if name not in changes and (source/name).read_bytes()!=original[name]:
            raise ValueError('An original source, resource, config or mesh was altered')
    report=dict(schema=1,status='prepared-awaiting-build-and-independent-audit',
        protocol='remaining-stock-repaired-sources-v3',original_application_and_sdk_source=BASE,
        producer_commit=producer,preparer_sha256=digest(Path(__file__).read_bytes()),
        original_files_sha256={name:digest(body) for name,body in original.items()},
        staged_files_sha256={name:digest(body) for name,body in modified.items()},
        declared_changes=changes,current_dragonfly_producer_sha256=producer_sources,
        initialization_repair=dict(field='FCell::Amperes',initial_value=0,
            policy='Define previous current before the first thermal update; retain every original update formula and callback order.'),
        adi_reference_request_repair=dict(field='ADI::ref_handle',initial_value=0,
            policy='No reference capture request before user input; preserve loaded reference and all original attitude/drawing operations.'),
        complete_scenes=38,declared_classes=len(config['classes']),recording_files=len(config['recording_files_sha256_lf']),
        staged_original_module_files_unchanged_except_declared_changes=True,
        repository_scene_class_and_recording_inputs_verified=True,
        runtime_assets_staged=False,
        intended_runtime_policy='Fresh copy of the retained original Windows application/SDK; '
            'explicit tank/Dragonfly/client replacements with old/new binary identities. '
            'The original application, SDK and failed reference trees must remain untouched.',
        numerical_configuration_policy='Separately versioned use of original production propagator defaults; '
            'all original numerical/image budgets and complete scene inputs remain required.',
        native_admission_qualified=False,phase6_complete=False,
        scope='Source preparation only. Rebuilt DLL/import compatibility, actual loaded binary checks, '
              'all 38 complete scenes twice in four profiles, independent audit, native comparisons and '
              'interactions remain required before any reference acceptance.')
    (a.output/'source-variant.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Prepared exact original Windows module source closure with six declared repaired/added files, including initial fuel-cell current and ADI request; no reference qualification')


if __name__=='__main__':main()
