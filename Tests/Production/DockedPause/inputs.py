"""Read the exact original docked scenes and the declared paused-clock diagnostic."""
import hashlib,json,math,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'StockScenarios'))
from inventory import ships

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def settings():
    value=json.loads((HERE/'cases.json').read_text())
    require(value['application_source']=='f725194209634f7fd5d1d44d426cfa9b5e303e37','Original application source changed')
    require(value['fixed_step']==1/60 and value['paused_frames']==8 and value['repetitions']==2,'Diagnostic clock or repetitions changed')
    actual=[(c['id'],c['scenario'],c['cockpit'],c['pause_tick']) for c in value['cases']]
    require(actual==[('docked_ISS','Scenarios/Delta-glider/Docked at ISS.scn',3,293),('docked_ISS_demo','Scenarios/Demo/Docked at ISS.scn',2,272)],'Original entry points or observed native pause ticks changed')
    return value

def scenario(case):
    config=settings();original=subprocess.check_output(['git','-C',str(ROOT),'show',config['application_source']+':'+case['scenario']]).replace(b'\r\n',b'\n')
    require(hashlib.sha256(original).hexdigest()==case['sha256_lf'],'Diagnostic parent was retagged away from its original Git blob')
    current=(ROOT/case['scenario']).read_bytes().replace(b'\r\n',b'\n')
    require(current==original,'Original complete scene bytes changed')
    expected=ships(original.decode('cp1252'))
    require(len(expected)==6 and expected.get('GL-02')=='DeltaGlider' and 'Mir' in expected and 'Luna-OB1' in expected,'All original docked-scene objects required')
    return original,expected

def configuration(body):
    for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
        require(body.count(line)==1,'Original fixture propagator declarations differ');body=body.replace(line,'')
    require(body.count('StartPaused = FALSE\n')==1,'Original fixture startup declaration differs')
    # The legacy StartPaused option intentionally performs a physics step first.
    # The reload observer requests pause through the public SDK before the first
    # BeginTimeStep instead; every reload physics callback is rejected.
    return body+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'


def physical_clocks(path,configuration_name,math_profile):
    """Bind every profile/case to an independently captured native pause clock."""
    path=Path(path);value=settings();request=json.loads(path.read_text())
    require(request['schema']==1 and request['protocol']=='original-stock-docked-physical-clock-inputs-v1','Unknown physical clock input protocol')
    require(request['native_runtime_source']=='693ce8cfb44617889d3a7218281d769a3f29cfd6' and request['original_application_source']==value['application_source'],'Physical clock source producer differs')
    profiles={'Debug-automatic','Debug-sse2','Release-automatic','Release-sse2'}
    require(set(request['profiles'])==profiles,'All four physical clock profiles required')
    require(re.fullmatch('[0-9a-f]{64}',request['independent_native_matrix_sha256']) is not None,'Independent native clock matrix binding missing')
    expected={c['id']:c for c in value['cases']}
    for name,entries in request['profiles'].items():
        require(set(entries)==set(expected),'Both complete docked entry points required in every profile')
        for key,entry in entries.items():
            case=expected[key];body,objects=scenario(case)
            require(entry['scenario']==case['scenario'] and entry['sha256_lf']==case['sha256_lf'],'Physical clock original parent differs')
            tick=entry['pause_tick'];require(type(tick) is int and 6<tick<3600,'Physical pause tick outside measured diagnostic bounds')
            require(re.fullmatch('[0-9a-f]{64}',entry['native_verification_sha256']) is not None,'Native physical-flow binding missing')
            elapsed=0.0
            for _ in range(tick):elapsed+=value['fixed_step']
            require(isinstance(entry['paused_seconds'],str) and math.isfinite(float(entry['paused_seconds'])) and float(entry['paused_seconds'])==elapsed,'Exact native physical tick/seconds association differs')
            dates=[row.split()[2] for row in body.decode('cp1252').splitlines() if row.strip().startswith('Date MJD ')]
            require(len(dates)==1 and isinstance(entry['paused_mjd'],str) and math.isfinite(float(entry['paused_mjd'])) and float(entry['paused_mjd'])==float(dates[0])+elapsed/86400,'Exact native physical tick/epoch association differs')
    profile=configuration_name+'-'+math_profile;require(profile in profiles,'Unknown requested physical profile')
    value['cases']=[dict(case,pause_tick=request['profiles'][profile][case['id']]['pause_tick'],native_clock_request=request['profiles'][profile][case['id']]) for case in value['cases']]
    value.update(clock_input_scope='actual-complete-native-physical-keyboard-flows',physical_clock_input_sha256=sha(path),independent_native_matrix_sha256=request['independent_native_matrix_sha256'])
    return value
