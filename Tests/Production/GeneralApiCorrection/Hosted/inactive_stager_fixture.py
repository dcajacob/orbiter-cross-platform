"""Restore the real same-SDK inactive file that the original staging receipt hashes."""
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
from general_api_provider import APPLICATION,require,sha,load
import restore_observer as original
PROTOCOL='phase6-inactive-original-C08-stager-fixture-v1'
NAME='Modules/Plugin/ProductionCockpitDriver.dll'


def describe(configuration):
    record_path=ROOT/'out/current-observer-restoration/restoration.json';record=load(record_path)
    binary=ROOT/'out/current-stock-preparation/observer/ProductionCockpitDriver.dll'
    require(record['status']=='restored-original-passive-observer-only' and record['configuration']==configuration and
            record['compiled_application_source']==record['compiled_observer_source']==APPLICATION and
            record['original_preparation_source']==original.PRODUCER and record['original_run_id']==original.RUN and
            record['restorer_source']==os.environ['GITHUB_SHA'] and record['observer_rebuilt'] is False and record['stock_simulation_executed'] is False,
            'Exact original same-SDK fixture restoration required')
    return dict(protocol=PROTOCOL,binary=str(binary),sha256=record['observer_binary_sha256'],restoration_path=str(record_path),
                restoration_sha256=sha(record_path),original_run_id=record['original_run_id'],original_artifact_id=record['original_artifact_id'],
                compiled_source=APPLICATION,preparation_source=original.PRODUCER,sdk_manifest_sha256=sha(ROOT/'out/current-windows-sdk/runtime/test-runtime.json'),
                intended_module_enabled=False)


def guarded(cfg):
    declaration=describe(cfg['configuration']);require(cfg['inactive_stager_fixture']==declaration and
            declaration['sdk_manifest_sha256']==cfg['roles']['sdk']['manifest_sha256'],'Inactive fixture cannot substitute an active observer or SDK')
    record=load(declaration['restoration_path']);api=ROOT/'out/current-observer-download/api.json'
    original.validate_api(load(api),cfg['configuration'])
    ident,size,digest,_=original.PINS[cfg['configuration']];archive=ROOT/'out/current-observer-download/producer.zip'
    require(archive.stat().st_size==size and sha(archive)==digest and record['original_artifact_id']==ident and
            record['source_api_sha256']==sha(api) and record['original_api_archive_sha256']==digest and
            record['sdk_restoration_sha256']==sha(ROOT/'out/current-windows-sdk/restoration.json'),'Original fixture actual API/ZIP/SDK byte binding differs')
    base=ROOT/'out/current-stock-preparation';result={str(base/name):value for name,value in record['restored_files_sha256'].items()}
    for path in (api,archive,Path(declaration['restoration_path'])):result[str(path)]=sha(path)
    require(sha(declaration['binary'])==declaration['sha256'] and result and all(sha(name)==value for name,value in result.items()),'Every original inactive fixture/source/compiler member must remain unchanged')
    return result


def inactive_configuration(text):
    lines=[line.split(';',1)[0].strip() for line in text.splitlines()]
    require(lines.count('ACTIVE_MODULES')==lines.count('END_MODULES')==1,'Actual complete active-module block required')
    start=lines.index('ACTIVE_MODULES');end=lines.index('END_MODULES');require(start<end,'Actual module block order differs')
    names=[line.casefold().removesuffix('.dll') for line in lines[start+1:end] if line]
    require(len(names)==len(set(names))==2 and set(names)=={'productiongeneralapiobserver','oglclient'},
            'Inactive original stock driver must never become an active API module')
    return names


def stage(directory,cfg):
    protected=guarded(cfg);directory=Path(directory);declaration=cfg['inactive_stager_fixture'];target=directory/NAME
    target.parent.mkdir(parents=True,exist_ok=True)
    require(target.parent.resolve()==target.parent and not target.is_symlink(),'Real private inactive fixture destination required')
    if target.exists():require(sha(target)==declaration['sha256'],'Conflicting private inactive fixture byte')
    else:shutil.copy2(declaration['binary'],target)
    require(sha(target)==declaration['sha256'],'Original inactive fixture changed while staging')
    receipt=directory/'inactive-stager-fixture.json';require(not receipt.exists(),'Fresh inactive fixture source receipt required')
    import json
    receipt.write_text(json.dumps(dict(protocol=PROTOCOL,source=declaration,actual_private_fixture_sha256=sha(target),
        unchanged_original_stager_hash_guard_retained=True,qualification_granted=False),indent=2)+'\n')
    require(all(sha(name)==value for name,value in protected.items()),'Original fixture/SDK source changed while staging')
    return {str(target):sha(target),str(receipt):sha(receipt)}


def verify_staged(directory,cfg):
    directory=Path(directory);guarded(cfg);declaration=cfg['inactive_stager_fixture'];target=directory/NAME
    receipt=load(directory/'inactive-stager-fixture.json')
    require(receipt==dict(protocol=PROTOCOL,source=declaration,actual_private_fixture_sha256=declaration['sha256'],
        unchanged_original_stager_hash_guard_retained=True,qualification_granted=False) and
        sha(target)==declaration['sha256'],'Actual inactive fixture source/private byte receipt differs')
    snapshot=directory/'staged-Orbiter.cfg';config=snapshot if snapshot.exists() else directory/'Orbiter.cfg'
    inactive_configuration(config.read_text())
    invocation=directory/'invocation.json'
    if invocation.exists():require(load(invocation)['driver_sha256']==declaration['sha256'],'Original unchanged stager driver hash differs')
    return dict(status='verified-original-fixture-byte-and-inactive-module-configuration',sha256=declaration['sha256'],module_enabled=False)
