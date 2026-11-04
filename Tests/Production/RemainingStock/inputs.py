"""Frozen complete scene selection, original class configuration and playback inputs."""
import hashlib
import json
from pathlib import Path,PureWindowsPath
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'StockScenarios'))
from inventory import ships

CASE_FILE=HERE/'cases.json'


def require(value,message):
    if not value:raise ValueError(message)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sha_lf(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def playback_vessels(text):
    declared=ships(text);inside=False;current=None;result=[]
    for raw in text.splitlines():
        line=raw.strip()
        if line=='BEGIN_SHIPS':inside=True;continue
        if line=='END_SHIPS':inside=False
        if not inside:continue
        if line=='END':current=None
        elif raw and not raw[0].isspace() and not line.startswith(';'):current=line.split(':',1)[0]
        elif line=='FLIGHTDATA':
            require(current in declared,'Playback vessel is not declared');result.append(current)
    return result


def settings():
    value=json.loads(CASE_FILE.read_text())
    accepted=json.loads((HERE.parent/'Cockpit/cases.json').read_text())
    for key in ('application_source','frames','fixed_step','epoch','image_ssim_minimum','budgets'):
        require(value[key]==accepted[key],'Remaining stock source/clock/budget changed: '+key)
    lock_path=HERE.parent/'production-source.lock.json';lock=json.loads(lock_path.read_text())
    require(digest(lock_path)==value['corpus_lock_sha256'] and lock['scenario_count']==157,
            'Full original stock corpus identity changed')
    require(value['schema']==2 and value['protocol']=='remaining-stock-v2' and value['automatic_refresh'] is False and len(value['cases'])==38,
            'Remaining stock scene protocol changed')
    selected=set()
    for entry in lock['scenarios']:
        path=ROOT/entry['path'];text=path.read_bytes().decode('cp1252')
        if set(ships(text).values())&set(value['required_classes']):
            selected.add(path.relative_to(ROOT/'Scenarios').as_posix())
    require({c['scenario'] for c in value['cases']}==selected and len({c['id'] for c in value['cases']})==38,
            'Complete remaining-module scene selection changed')
    sources=dict(value['recording_files_sha256_lf'])
    for case in value['cases']:
        path=ROOT/'Scenarios'/case['scenario'];text=path.read_bytes().decode('cp1252')
        require(case['scenario_entry_point']=='Scenarios/'+case['scenario'] and
                case['declared_vessels']==ships(text) and case['playback_vessels']==playback_vessels(text),
                'Remaining scene vessel or playback manifest changed')
        sources[case['scenario_entry_point']]=case['sha256_lf']
        recordings(case,value)
    for item in value['classes'].values():sources[item['source']]=item['sha256_lf']
    repairs=value['delivery_repairs']
    require(len(repairs)==1 and repairs[0]['preserved_source']=='Meshes/Dragonfly.msh' and
            repairs[0]['target']=='Meshes/Dragonfly/Dragonfly.msh' and
            repairs[0]['source']=='Src/Vessel/Dragonfly/Meshes/Dragonfly.msh' and
            repairs[0]['install_rule']=='Src/Vessel/Dragonfly/CMakeLists.txt',
            'Original mesh delivery repair changed')
    for item in repairs:
        sources[item['source']]=item['sha256_lf'];sources[item['install_rule']]=item['install_rule_sha256_lf']
    require(set(value['classes'])=={kind for c in value['cases'] for kind in c['declared_vessels'].values()},
            'Declared class configuration closure incomplete')
    for name,checksum in sources.items():
        frozen=subprocess.check_output(['git','-C',str(ROOT),'show',value['application_source']+':'+name])
        require(hashlib.sha256(frozen.replace(b'\r\n',b'\n')).hexdigest()==checksum==sha_lf(ROOT/name),
                'Frozen remaining stock input changed: '+name)
    return value


def entry_point(out,case):return out/case['scenario_entry_point']
def argument(case):return '--scenariox='+str(PureWindowsPath(case['scenario']).with_suffix(''))


def recordings(case,config):
    if not case['playback_vessels']:
        require('recording_directory' not in case,'Unexpected recording alias');return {}
    require(case['recording_directory']==Path(case['scenario']).stem,'Original recording name changed')
    prefix='Flights/'+case['recording_directory']+'/'
    files={name:value for name,value in config['recording_files_sha256_lf'].items() if name.startswith(prefix)}
    require({prefix+name+'.pos' for name in case['playback_vessels']}<=set(files),
            'Required per-vessel position recording omitted')
    # Original system/attitude/event streams are optional when absent in stock.
    # Copy every existing stream; never substitute a similarly named recording.
    actual={p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).iterdir() if p.is_file()}
    require(set(files)==actual,'Recording directory closure changed')
    return files


def stage_recordings(out,case,config):
    for name,checksum in recordings(case,config).items():
        require(sha_lf(ROOT/name)==checksum,'Original recording changed before staging')
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)


def stage_delivery_repairs(out,config,preserved):
    result={}
    for item in config['delivery_repairs']:
        source=out/item['preserved_source'];target=out/item['target']
        require(not target.exists() and digest(source)==preserved[item['preserved_source']] and
                sha_lf(source)==item['sha256_lf'],'Original mesh delivery repair source differs')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        require(digest(target)==digest(source),'Original mesh delivery copy differs')
        result[item['target']]=dict(preserved_source=item['preserved_source'],sha256=digest(target),
            source=item['source'],install_rule=item['install_rule'],install_rule_sha256_lf=item['install_rule_sha256_lf'])
    return result


def inspect_inputs(out,case,config):
    invocation=json.loads((out/'invocation.json').read_text())
    require(invocation['scenario_entry_point']==case['scenario_entry_point'] and
            [v for v in invocation['argv'] if v.startswith('--scenariox=')]==[argument(case)],
            'Actual original Windows entry point changed')
    repairs=invocation['delivery_repairs']
    require(set(repairs)=={item['target'] for item in config['delivery_repairs']},'Original mesh delivery repair omitted')
    for item in config['delivery_repairs']:
        actual=repairs[item['target']]
        require(actual==dict(preserved_source=item['preserved_source'],sha256=invocation['preserved_inputs_sha256'][item['preserved_source']],
            source=item['source'],install_rule=item['install_rule'],install_rule_sha256_lf=item['install_rule_sha256_lf']) and
            invocation['input_sha256'][item['target']]==actual['sha256']==digest(out/item['target']) and
            sha_lf(out/item['target'])==item['sha256_lf'],
            'Original mesh delivery repair bytes or provenance differ')
    for name,checksum in {case['scenario_entry_point']:case['sha256_lf'],**recordings(case,config)}.items():
        require(sha_lf(out/name)==checksum and digest(out/name)==invocation['input_sha256'][name],
                'Executed scenario or recording changed: '+name)
    for name,item in config['classes'].items():
        if name in case['declared_vessels'].values():
            require(invocation['input_sha256'][item['target']]==invocation['preserved_inputs_sha256'][item['target']],
                    'Original class configuration changed: '+name)
    return len(recordings(case,config))
