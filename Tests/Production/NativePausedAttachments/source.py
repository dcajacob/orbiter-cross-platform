#!/usr/bin/env python3
"""Bind one native startup correction while retaining the exact v3 physics guard chain."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASELINE='ef2401bb059f429aec3b1d7880e58f94f8a7a56f'
VERSION='paused-attachments-v1'
TARGET='Src/Orbiter/Production/NativeApplication.cpp'
OLD_BUILDER='Tests/Production/PhysicsV3/build_native.py'
BUILDER='Tests/Production/NativePausedAttachments/build_native.py'
INPUTS=tuple('Tests/Production/NativePausedAttachments/'+name for name in
             ('source.py','version.json','correction.patch','build_native.py','Version.Test.py','Startup.Test.py','README.md'))

def require(value,message):
    if not value:raise ValueError(message)

def git(*args,root=ROOT):return subprocess.check_output(['git','-C',str(root),*args])
def normalized(value):return value.replace(b'\r\n',b'\n')
def digest(value):return hashlib.sha256(value).hexdigest()

def corrected_bootstrap(body):
    anchor=b'        render.graphics->PostCreation();system->PostCreation();\n'
    require(body.count(anchor)==1,'Exact original native post-creation boundary required')
    return body.replace(anchor,anchor+
        b'        // Attached children skip their serialized free-flight state. Resolve\n'
        b'        // their poses after every module has restored its attachment points,\n'
        b'        // before a paused session can render or save without a physics step.\n'
        b'        for(auto* vessel:system->GetVessels())\n'
        b'            if(!vessel->isAttached())vessel->UpdateAttachments();\n')

def versioned_builder(body):
    anchor=b'from PhysicsV3 import source as physics_source'
    report=b'    if physics_proof:report.update(physics_version=a.physics_version,physics_source_proof=physics_proof)'
    require(body.count(anchor)==body.count(report)==1,'Exact unchanged v3 builder boundaries required')
    return body.replace(anchor,b'from NativePausedAttachments import source as physics_source').replace(
        report,report+b"\n    if physics_proof:report['native_bootstrap_version']=physics_proof['native_bootstrap_version']")

def expected_sources():
    return {TARGET:corrected_bootstrap(normalized(git('show',BASELINE+':'+TARGET))),
            BUILDER:versioned_builder(normalized(git('show',BASELINE+':'+OLD_BUILDER)))}

def validate_current(root=ROOT):
    root=Path(root).resolve();manifest=json.loads((root/'Tests/Production/NativePausedAttachments/version.json').read_text())
    require(manifest['native_bootstrap_version']==VERSION and manifest['physics_version']=='assembly-contact-v3' and
            manifest['baseline_source']==BASELINE and manifest['target']==TARGET,'Exact separately versioned native bootstrap required')
    expected=expected_sources();checks={}
    for name,body in expected.items():
        actual=normalized((root/name).read_bytes());require(actual==body,'Unreviewed native bootstrap or builder change: '+name);checks[name]=digest(actual)
    require(checks[TARGET]==manifest['corrected_source_sha256_lf'] and
            digest(normalized(git('show',BASELINE+':'+TARGET)))==manifest['original_source_sha256_lf'] and
            digest(normalized(git('show',BASELINE+':'+OLD_BUILDER)))==manifest['original_builder_sha256_lf'],
            'Exact baseline and corrected native sources required')
    require(digest((root/'Tests/Production/NativePausedAttachments/correction.patch').read_bytes())==manifest['patch_sha256'],
            'Exact incremental bootstrap patch required')
    previous=json.loads(normalized(git('show',BASELINE+':Tests/Production/PhysicsV3/version.json')))
    previous_inputs=git('ls-tree','-r','--name-only',BASELINE,'--','Tests/Production/PhysicsV3').decode().splitlines()
    for name in previous_inputs+list(previous['original_guard_files_sha256_lf']):
        require(normalized((root/name).read_bytes())==normalized(git('show',BASELINE+':'+name)),
                'Original v3 physics version, builder or acceptance input changed: '+name)
    require(digest(normalized((root/'Tests/Production/PhysicsV3/version.json').read_bytes()))==manifest['previous_version_manifest_sha256_lf'],
            'Previous v3 manifest cannot be relabelled')
    changes=set(git('diff','--name-only',BASELINE,'--',root=root).decode().splitlines())
    changes.update(git('ls-files','--others','--exclude-standard',root=root).decode().splitlines())
    bad=sorted(n for n in changes if n!=TARGET and not n.startswith('Tests/Production/NativePausedAttachments/'))
    require(not bad,'Original tests, physics, readers, captures, tolerances or unrelated inputs changed: '+str(bad))
    return dict(native_bootstrap_version=VERSION,physics_version='assembly-contact-v3',baseline_source=BASELINE,
                actual_reviewed_sources_sha256_lf=checks,production_files_changed=[TARGET],
                original_v3_physics_guards_tests_captures_and_tolerances_unchanged=True,
                qualification_granted=False,normal_admission_qualified=False,phase6_complete=False)

def baseline_clone(destination):
    require(not destination.exists(),'Fresh preserved v3 source view required')
    subprocess.run(['git','clone','--quiet','--shared','--no-checkout',str(ROOT),str(destination)],check=True)
    subprocess.run(['git','-C',str(destination),'sparse-checkout','init','--no-cone'],check=True)
    sys.path.insert(0,str(HERE.parent));from PhysicsV2.source import SCOPES
    (destination/'.git/info/sparse-checkout').write_text(''.join('/'+n+('/' if '.' not in n.rsplit('/',1)[-1] else '')+'\n' for n in SCOPES))
    subprocess.run(['git','-C',str(destination),'checkout','--quiet','--detach',BASELINE],check=True)

def verify(output=None):
    proof=validate_current();base=ROOT/'out/native-paused-attachments-baseline-v1';base.mkdir(parents=True,exist_ok=True);view=base/'source'
    if not view.exists():baseline_clone(view)
    require(git('rev-parse','HEAD',root=view).decode().strip()==BASELINE and not git('status','--porcelain','--untracked-files=no',root=view).strip(),
            'Preserved v3 source view changed')
    prior=base/'original-v3-source-guards.json';log=base/'original-v3-source-guards.log'
    with log.open('w') as stream:
        result=subprocess.run([sys.executable,'-B',str(view/'Tests/Production/PhysicsV3/source.py'),'--output',str(prior)],cwd=view,stdout=stream,stderr=subprocess.STDOUT)
    require(result.returncode==0,'Original v3 source guards must pass their exact retained source; see '+str(log))
    old=json.loads(prior.read_text());require(old['actual_source']==BASELINE and old['physics_version']=='assembly-contact-v3' and
        old['original_v1_and_v2_guards_captures_tolerances_unchanged'],'Exact original-to-v3 guard chain required')
    require(validate_current()==proof,'Native bootstrap inputs changed during original guard replay')
    proof.update(actual_source=git('rev-parse','HEAD').decode().strip(),baseline_view=str(view),
        previous_version_source_guards=dict(actual_returncode=result.returncode,proof_sha256=digest(prior.read_bytes()),log_sha256=digest(log.read_bytes())),
        scope='Native paused attachment initialization only; existing v3 captures retain their actual original source/runtime identities')
    body=json.dumps(proof,indent=2)+'\n';(base/'verification.json').write_text(body)
    if output:Path(output).write_text(body)
    return proof

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();verify(args.output)
    print('Native paused attachment delta verified; original v3, v2 and original guards passed their retained source views')
