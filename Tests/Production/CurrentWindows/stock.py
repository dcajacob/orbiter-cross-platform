"""Current-SDK stock capture adapter; original-SDK identity readers stay strict."""
import json
from pathlib import Path
import re


def require(value,message):
    if not value: raise ValueError(message)


def selection(cfg,config):
    scope=cfg['capture_scope'];ids=scope['cases'];all_ids=[case['id'] for case in config['cases']]
    require(scope['gate']=='remaining-stock' and ids and ids==sorted(set(ids)) and set(ids)<=set(all_ids),
            'Known unique ordered complete-scene selection required')
    diagnostic=scope['kind']=='diagnostic'
    require(diagnostic or ids==all_ids, 'Complete current stock scope requires all 38 scenes')
    require(cfg['math_profile']=='matrix' and cfg['scene_workers']==1, 'Two serial math lanes and one scene per worker required')
    require(cfg['minimum_free_bytes']>=(1024**3 if diagnostic else 8*1024**3), 'Current stock capacity reserve too small')
    return [case for case in config['cases'] if case['id'] in ids],diagnostic


def inspect_run(out,case,config,reader,producer,source):
    """Use existing physical/clock/frame coverage checks without claiming f725 SDK identity."""
    out=Path(out);load=lambda name:json.loads((out/name).read_text())
    require(not (out/'stock-vessel-failure.txt').exists() and
            (out/'stock-vessel-complete.txt').read_text().strip()==str(config['frames']), 'Current stock observer ended early or failed')
    require(load('process-result.json')==dict(returncode=0), 'Current stock simulator failed')
    result=reader.shared.inspect_trace(out,case,config)
    result['clock_observation']=reader.shared.inspect_clock(out,config['frames'])
    require(load('graphics-lifecycle.json')==dict(rendered_frames=960,successful_presents=960,context_deleted=True),
            'Current stock graphics lifetime incomplete')
    renderer=load('renderer-info.json')
    require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width']==1280 and renderer['client_height']==720,
            'Current stock renderer/viewport differs')
    error=out/'graphics-errors.txt';require(not error.exists() or not error.read_text().strip(), 'Current stock OpenGL error')
    text=(out/'Orbiter.log').read_text(errors='replace')+(out/'console.txt').read_text(errors='replace')
    require(not any(s in text for s in ('Lua error:','LuaCall (','runtime error:','Could not find a module','Assertion failed',
                                      'ERROR: AddressSanitizer','ERROR: LeakSanitizer')), 'Current stock runtime diagnostic')
    actual_cfg=(out/'staged-Orbiter.cfg').read_text()
    require(not re.search(r'^\s*(?:PropStages|PropStage\d+|PropSubsampling)\s*=',actual_cfg,re.M|re.I),
            'Current stock overrides production propagators')
    result['configuration_input']=reader.configuration_input.inspect(out,reader.configuration_input.expected(source,producer,'repaired-windows'))
    require((out/reader.protocols.MARKER).read_bytes()==reader.protocols.marker_bytes(config), 'Current stock finalized-frame descriptor differs')
    require(len((out/'scene.rgba').read_bytes())==1280*720*4, 'Current stock full framebuffer incomplete')
    reader.protocols.inspect_frame(load('scene-summary.json'),config,result['matched_clock_observation'])
    scene=reader.shared.rows(out/'scene.csv');tick=str(config['capture_tick'])
    meshes={(row['object'],row['index']) for row in reader.shared.rows(out/'stock-vessel-meshes.csv')
            if row['tick']==tick and row['present']=='1'}
    actual=[(row['object'],row['index']) for row in scene if row['type']=='vessel']
    require(set(actual)==meshes and len(actual)==len(meshes), 'Current stock renderer omitted/substituted a physical mesh')
    classes={row['object']:row['class'] for row in reader.shared.rows(out/'stock-vessel-state.csv') if row['tick']==tick}
    require(all(row['class'].lower()==classes[row['object']].lower() for row in scene if row['type']=='vessel'),
            'Current rendered class differs from physical object')
    result['actual_math']=(out/'math-profile.txt').read_text().strip()
    require(result['actual_math'] in ('sse2','fma3'), 'Current stock actual math mode missing')
    result['renderer']=renderer
    return result
