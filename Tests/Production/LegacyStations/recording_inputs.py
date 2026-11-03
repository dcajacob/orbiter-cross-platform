"""Original scenario entry points and mandatory complete recording inputs."""
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CASE_FILE=HERE/'cases-v2.json'
LOCK_FILE=HERE/'observations-v2.lock.json'


def require(value,message):
    if not value:raise ValueError(message)


def sha_lf(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def entry_point(out,case):
    require(case['scenario_entry_point']=='Scenarios/'+case['scenario'],'Original legacy scenario entry point changed')
    return out/case['scenario_entry_point']


def recordings(case,config):
    directory=case.get('recording_directory')
    if not directory:
        require(not case['playback_vessels'],'Playback scene has no named recording directory')
        return {}
    require(directory==Path(case['scenario']).stem,'Recording directory does not match original scenario name')
    prefix='Flights/'+directory+'/'
    result={name:value for name,value in config['recording_files_sha256_lf'].items() if name.startswith(prefix)}
    required={prefix+'system.dat'}|{prefix+name+'.pos' for name in case['playback_vessels']}
    require(result and required<=set(result),'Required playback streams missing from frozen input manifest')
    return result


def stage_recordings(source,out,case,config):
    for name,expected in recordings(case,config).items():
        path=source/name
        require(path.is_file() and sha_lf(path)==expected,'Required original recording missing or changed: '+name)
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)


def inspect_inputs(out,case,config,rows):
    invocation=json.loads((out/'invocation.json').read_text())
    require(invocation['scenario_entry_point']==case['scenario_entry_point'],'Executed scenario entry point differs')
    files={case['scenario_entry_point']:case['sha256_lf'],**recordings(case,config)}
    for name,expected in files.items():
        path=out/name
        require(path.is_file() and sha_lf(path)==expected,'Executed original scenario/recording bytes differ: '+name)
        require(digest(path)==invocation['input_sha256'][name],'Scenario/recording changed after staging: '+name)
    names=set(case['playback_vessels'])
    states=rows(out/'stock-vessel-state.csv')
    declared={row['object'] for row in states if row['tick']=='0'}
    require(names<=declared,'Playback manifest substitutes a declared vessel')
    flags=rows(out/'stock-playback.csv');seen=set()
    for row in flags:
        key=(int(row['tick']),row['object'])
        require(key not in seen,'Duplicate actual playback observation');seen.add(key)
        require(row['playback']==('1' if row['object'] in names else '0'),'Actual vessel playback state differs')
    require(seen=={(tick,name) for tick in range(config['frames']+1) for name in declared},
            'Actual per-vessel playback observations incomplete')
    return dict(recording_files=len(files)-1,playback_rows=len(flags),playback_vessels=sorted(names))
