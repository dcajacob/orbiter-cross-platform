"""Read the exact original docked scenes and the declared paused-clock diagnostic."""
import hashlib,json,subprocess,sys
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
