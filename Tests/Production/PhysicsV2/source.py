#!/usr/bin/env python3
"""Verify the approved v2 engine delta and execute all unchanged v1 source guards on v1."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent))
from PhysicsV2.transforms import VERSION,BASELINE,TARGET,BUILDER,CLIENT,corrected_physics,versioned_builder,versioned_client
INPUTS=('Tests/Production/PhysicsV2/source.py','Tests/Production/PhysicsV2/transforms.py','Tests/Production/PhysicsV2/version.json','Tests/Production/PhysicsV2/correction.patch','Tests/Production/PhysicsV2/units.py')
SCOPES=('Src','Orbitersdk','Extern','OVP','Tests','Scenarios','Config','Meshes','Flights','Script','Docs','cmake','CMakeLists.txt','CMakePresets.json','LICENSE','README.md','.github','.gitignore','.gitattributes','.editorconfig')


def require(value,message):
    if not value:raise ValueError(message)


def git(*args,root=ROOT):return subprocess.check_output(['git','-C',str(root),*args])
def normalized(data):return data.replace(b'\r\n',b'\n')
def digest(data):return hashlib.sha256(data).hexdigest()
def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')


def expected_sources():
    transforms={TARGET:corrected_physics,BUILDER:versioned_builder,CLIENT:versioned_client}
    return {name:transform(normalized(git('show',BASELINE+':'+name)).decode()).encode() for name,transform in transforms.items()}


def validate_current(root=ROOT):
    root=Path(root).resolve();manifest=json.loads((root/'Tests/Production/PhysicsV2/version.json').read_text())
    require(manifest['physics_version']==VERSION and manifest['baseline_source']==BASELINE,'Exact explicit original baseline and physics version required')
    expected=expected_sources();checks={}
    for name,body in expected.items():
        actual=normalized((root/name).read_bytes());require(actual==body,'Unreviewed physics/harness change: '+name);checks[name]=digest(actual)
    require(checks[TARGET]==manifest['corrected_source_sha256_lf'] and digest(normalized(git('show',BASELINE+':'+TARGET)))==manifest['original_source_sha256_lf'],'Approved patch/source identity differs')
    patch=root/'Tests/Production/PhysicsV2/correction.patch';require(digest(patch.read_bytes())==manifest['patch_sha256'],'Exact independently tested patch required')
    changes=set(git('diff','--name-only',BASELINE,'--',root=root).decode().splitlines())
    changes.update(git('ls-files','--others','--exclude-standard',root=root).decode().splitlines())
    added=lambda n:n.startswith('Tests/Production/PhysicsV2/') or n.startswith('.github/workflows/phase6-physics-v2-') and n.endswith('.yml')
    require(all(n in expected or added(n) for n in changes),'Original guard, test, capture, tolerance or unrelated source changed: '+str(sorted(n for n in changes if n not in expected and not added(n))))
    for name,pin in manifest['original_guard_files_sha256_lf'].items():require(digest(normalized((root/name).read_bytes()))==pin,'Original source guard/ledger bytes changed: '+name)
    return dict(physics_version=VERSION,baseline_source=BASELINE,actual_reviewed_sources_sha256_lf=checks,all_original_guards_captures_and_tolerances_unchanged=True,production_files_changed=[TARGET],normal_admission_qualified=False,phase6_complete=False)


def baseline_clone(destination,root=ROOT):
    destination=Path(destination);require(not destination.exists(),'Fresh isolated original-source view required')
    subprocess.run(['git','clone','--quiet','--shared','--no-checkout',str(root),str(destination)],check=True)
    subprocess.run(['git','-C',str(destination),'sparse-checkout','init','--no-cone'],check=True)
    sparse=destination/'.git/info/sparse-checkout';sparse.write_text(''.join('/'+n+('/' if '.' not in n.rsplit('/',1)[-1] else '')+'\n' for n in SCOPES))
    subprocess.run(['git','-C',str(destination),'checkout','--quiet','--detach',BASELINE],check=True)
    require(git('rev-parse','HEAD',root=destination).decode().strip()==BASELINE,'Original baseline view HEAD differs')
    return destination


def verify(output=None):
    proof=validate_current();base=ROOT/'out/physics-v2-baseline';base.mkdir(parents=True,exist_ok=True);view=base/'source'
    if not view.exists():baseline_clone(view)
    require(git('rev-parse','HEAD',root=view).decode().strip()==BASELINE and not git('status','--porcelain','--untracked-files=no',root=view).strip(),'Original baseline source view changed')
    guards={}
    for name in ('observation_source.py','vessel_source.py'):
        path=view/'Tests/Production'/name;body=normalized(path.read_bytes());require(body==normalized(git('show',BASELINE+':Tests/Production/'+name)),'Original baseline guard changed')
        log=base/(name+'.log')
        with log.open('w') as stream:result=subprocess.run([sys.executable,'-B',str(path)],cwd=view,stdout=stream,stderr=subprocess.STDOUT)
        require(result.returncode==0,'Unchanged original source guard rejected original baseline: '+name+'; see '+str(log))
        guards[name]=dict(source=BASELINE,guard_sha256_lf=digest(body),actual_returncode=result.returncode,log_sha256=digest(log.read_bytes()))
    require(validate_current()==proof,'Corrected production or original inputs changed during guard replay')
    proof.update(original_guards=guards,baseline_view=str(view),actual_source=git('rev-parse','HEAD').decode().strip(),scope='Explicitly versioned corrected physics; original-source qualification is retained as historical baseline, never relabelled')
    write(base/'verification.json',proof)
    if output:write(output,proof)
    return proof


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--baseline-controls',type=Path);a=p.parse_args();proof=verify(a.output)
    if a.baseline_controls:
        view=Path(proof['baseline_view']);a.baseline_controls=a.baseline_controls.resolve();a.baseline_controls.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run([sys.executable,'-B',str(view/'Tests/Production/Closeout/run_controls.py'),'--output',str(a.baseline_controls)],cwd=view,check=True)
        controls=json.loads(a.baseline_controls.read_text());require(controls['status']=='passed' and controls['tests_run']==506 and controls['sources_match_producer'] is True and controls['producer_commit']==BASELINE,'Every unchanged v1 closeout control must pass on its exact original source')
    print('Approved '+VERSION+' delta verified; unchanged original guards passed their preserved original baseline')


if __name__=='__main__':main()
