"""Explicit observation protocols; the preserved v1 contract remains selectable."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
V1='remaining-stock-repaired-v1'
V2='remaining-stock-matched-clock-v2'
NAMES=(V1,V2)
MARKER='remaining-stock-finalized-frame-v2.txt'


def require(value,message):
    if not value:raise ValueError(message)


def path(name):
    require(name in NAMES,'Unknown complete-scene observation protocol')
    return HERE/('protocol.json' if name==V1 else 'matched-clock-v2.json')


def read(name):
    value=json.loads(path(name).read_text())
    require(value['protocol']==name and value['complete_scenes']==38 and value['frames']==960 and
            value['fixed_step']==1/64 and value['capture_tick']==800 and value['repeats']==2 and
            value['original_application_and_sdk_source']=='f725194209634f7fd5d1d44d426cfa9b5e303e37' and
            value['automatic_refresh'] is False and value['native_admission_qualified'] is False and
            value['phase6_complete'] is False,'Complete-scene protocol contract changed')
    if name==V1:
        require(value['schema']==1 and value['capture_time']==12.5 and value['duration_seconds']==15 and
                value['epoch']==51982.5 and value['frames']*value['fixed_step']==value['duration_seconds'] and
                value['capture_tick']*value['fixed_step']==value['capture_time'],'Repaired v1 protocol changed')
    else:
        require(value['schema']==2 and value['system_elapsed_input']==.1 and
                value['system_startup_steps']==[.01,.01,.01] and value['capture_time'] is None and
                value['original_propagator_defaults'] is True and value['script_controlled_warp'] is True,
                'Matched-clock v2 protocol changed')
    return value


def load(original,name=V1):
    value=read(name)
    require(value['original_application_and_sdk_source']==original['application_source'] and
            value['complete_scenes']==len(original['cases'])==38,'Original scene/source scope differs')
    if name==V1:require(value['epoch']==original['epoch'],'Repaired v1 fallback epoch differs')
    result=dict(original,protocol=name,frames=value['frames'],fixed_step=value['fixed_step'],
                capture_tick=value['capture_tick'])
    if name==V2:
        result.update(system_elapsed_input=value['system_elapsed_input'],system_startup_steps=value['system_startup_steps'],
                      capture_time=None,duration_seconds=None)
    return result


def marker_bytes(config):
    require(config['protocol']==V2 and config['capture_tick']==800,'Finalized-frame marker requires explicit v2')
    return (V2+' '+str(config['capture_tick'])+'\n').encode('ascii')


def inspect_frame(summary,config,matched_clock=None):
    require(summary['frames']==config['capture_tick'] and summary['width']==1280 and summary['height']==720,
            'Actual finalized full-frame capture tick/viewport differs')
    if config['protocol']==V2:
        require(matched_clock is not None and summary['capture_protocol']==V2 and
                summary['finalized_tick']==config['capture_tick'] and
                summary['simulation_seconds']==matched_clock['capture_simulation_seconds'],
                'Actual finalized-frame capture is not associated with its observed SDK clock')
    else:require(summary['simulation_seconds']==12.5,'Repaired v1 full-frame capture time differs')
