#!/usr/bin/env python3
"""Run the diagnostic Windows build; reject observations if physical traces change."""
import argparse,hashlib,importlib.util,json,sys,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRODUCTION=HERE.parent
sys.path.insert(0,str(PRODUCTION));sys.path.insert(0,str(PRODUCTION/'GroundFlight'))
from behavior_suite import stage,FILES
from frozen import verify as verify_ground
from reference import CASES,validate
from mesa_runtime import require,digest

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('orbiter','data','planets','output','instrumentation'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();require(sys.platform=='win32','This observer requires real Windows execution')
    proof=verify_ground();controlled=load('stage_controlled_frozen',PRODUCTION/'ControlledLanding/frozen.py').verify()
    metadata=json.loads(a.instrumentation.read_text());require(metadata['diagnostic_only'] and metadata['insertions_reversible'],'Not an isolated contact diagnostic')
    runtime=json.loads((a.orbiter.parent/'test-runtime.json').read_text())
    require(runtime['source_commit']==proof['application_source'],'Wrong frozen source for diagnostic rebuild')
    for name,sha in runtime['files'].items():require(digest(a.orbiter.parent/name)==sha,'Mixed diagnostic runtime: '+name)
    a.output.mkdir(parents=True,exist_ok=False);results=[]
    for name,driver,reference in (('impact','ProductionBehaviorDriver',proof),('controlled','ProductionLandingDriver',controlled)):
        case=dict(next(c for c in CASES if c['id']=='pb_takeoff_landing'))
        if name=='controlled':case.update(frames=6000)
        def setup(directory):
            (directory/'Scenarios/Behavior.scn').write_bytes((PRODUCTION/'GroundFlight/Edwards-ShuttlePB.scn').read_bytes())
            (directory/'Orbiter.cfg').write_text((PRODUCTION/'GroundFlight/Orbiter.cfg').read_text()+
                '\nACTIVE_MODULES\n  '+driver+'\nEND_MODULES\n',encoding='ascii')
        directory=a.output/name
        stage(a.orbiter.resolve(),a.data.resolve(),a.planets.resolve(),directory,case,None,setup)
        validate(directory,case)
        key='controlled-landing' if name=='controlled' else 'pb_takeoff_landing'
        folder='ControlledReference' if name=='controlled' else 'GroundReference'
        record=reference['artifacts']['Debug'];checksums={}
        with zipfile.ZipFile(PRODUCTION/folder/record['path']) as archive:
            for filename in FILES:
                expected=archive.read('production-behavior/'+key+'/'+filename)
                require((directory/filename).read_bytes()==expected,'Diagnostic build changed frozen '+name+': '+filename)
                checksums[filename]=hashlib.sha256(expected).hexdigest()
        stages=directory/'contact-stages.jsonl';require(stages.is_file() and stages.stat().st_size>0,'No intermediate contact observations')
        results.append(dict(case=name,unchanged_physical_trace_sha256=checksums,stages_sha256=digest(stages)))
    report=dict(status='passed observation-only proof',diagnostic_only=True,instrumentation=metadata,
                runtime_manifest_sha256=digest(a.orbiter.parent/'test-runtime.json'),cases=results)
    (a.output/'stage-observation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
