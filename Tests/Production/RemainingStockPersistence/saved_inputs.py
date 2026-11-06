"""Name exact Windows saved states as derived inputs without replacing stock scenes."""
import hashlib
import json
from pathlib import Path,PurePosixPath

from saved_state import parse_saved,require

HERE=Path(__file__).resolve().parent


def protocol():
    value=json.loads((HERE/'protocol.json').read_text())
    require(value['schema']==1 and value['protocol']=='remaining-stock-persistence-v1' and
            value['original_application_and_sdk_source']=='f725194209634f7fd5d1d44d426cfa9b5e303e37' and
            value['parent_observation_protocol']=='remaining-stock-matched-clock-v2' and
            value['complete_scenes']==38 and value['repeats']==2 and value['frames']==960 and
            value['fixed_step']==1/64 and value['system_elapsed_input']==.1 and
            value['system_startup_steps']==[.01,.01,.01] and value['capture_tick']==800 and
            value['profiles']==['Debug-automatic','Debug-sse2','Release-automatic','Release-sse2'] and
            value['native_save_command']==dict(input_tick=959,phase='after',action='save',value=0,finalized_tick=960) and
            value['native_save_boundary']=='windows-close-session-v2' and
            value['native_before_save_command']==dict(input_tick=959,phase='after',action='endplayback',value=0,finalized_tick=960) and
            value['automatic_refresh'] is False and value['native_admission_qualified'] is False and
            value['phase6_complete'] is False,'Complete persistence protocol differs')
    return value


def derived_case(parent,config,path,expected_sha256):
    """Keep the original recording basename and every actual saved vessel/class."""
    saved=parse_saved(path);body=Path(path).read_bytes()
    require(saved['sha256']==hashlib.sha256(body).hexdigest()==expected_sha256,
            'Exact original Windows saved input changed')
    require(parent['scenario_entry_point']=='Scenarios/'+parent['scenario'] and
            parent in config['cases'],'Derived input has no complete frozen parent case')
    scenario=PurePosixPath('_Phase6Persistence')/parent['id']/PurePosixPath(parent['scenario']).name
    require(scenario.suffix=='.scn','Original scene suffix differs')
    vessels={name:ship['class_name'] for name,ship in saved['ships'].items()}
    require(set(vessels.values())<=set(config['classes']),'Saved vessel class has no frozen configuration witness')
    playback=[name for name,ship in saved['ships'].items() if ['FLIGHTDATA'] in ship['records']]
    result=dict(parent,scenario=scenario.as_posix(),scenario_entry_point='Scenarios/'+scenario.as_posix(),
                declared_vessels=vessels,playback_vessels=playback,sha256_lf=saved['sha256_lf'])
    if playback:
        require(parent.get('recording_directory')==scenario.stem,'Saved playback has no exact original recording directory')
    else:result.pop('recording_directory',None)
    provenance=dict(protocol=protocol()['protocol'],original_parent_case=parent,
        derived_scenario_entry_point=result['scenario_entry_point'],saved_input_sha256=saved['sha256'],
        saved_input_sha256_lf=saved['sha256_lf'],system=saved['system'],mjd=saved['mjd'],focus=saved['focus'],
        saved_vessels=vessels,saved_playback_vessels=playback,
        original_recording_basename_preserved=PurePosixPath(parent['scenario']).stem==scenario.stem,
        original_scenarios_and_scripts_unchanged=True,native_admission_qualified=False,phase6_complete=False)
    return result,provenance
