"""Complete original scene inputs and strict raw diagnostic readers."""
import csv,hashlib,json,math,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'StockScenarios'))
from inventory import ships

def require(value,message):
    if not value:raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def rows(path):
    with Path(path).open() as stream:return list(csv.DictReader(stream))

def settings():
    value=json.loads((HERE/'cases.json').read_text())
    require(value['frames']==60 and value['fixed_step']==.25 and value['repetitions']==2,'Diagnostic bounds changed')
    require(value['application_source']=='f725194209634f7fd5d1d44d426cfa9b5e303e37' and value['parent_scenario']=='Scenarios/Delta-glider/DG Mk4 in orbit.scn','Original diagnostic parent changed')
    original=subprocess.check_output(['git','-C',str(ROOT),'show',value['application_source']+':'+value['parent_scenario']]).replace(b'\r\n',b'\n')
    require(hashlib.sha256(original).hexdigest()==value['parent_sha256_lf'],'Diagnostic parent was coherently retagged away from the original source')
    return value

def scenario(case):
    config=settings();raw=(ROOT/config['parent_scenario']).read_bytes().replace(b'\r\n',b'\n')
    require(hashlib.sha256(raw).hexdigest()==config['parent_sha256_lf'],'Original full scene identity differs')
    text=raw.decode('cp1252');expected=ships(text)
    require(len(expected)==8,'All eight original scene objects are required')
    if case['id']=='full_dg_saved_hud_contrast':
        before='BEGIN_HUD\n  TYPE Surface\nEND_HUD';require(text.count(before)==1,'Original HUD block differs')
        text=text.replace(before,'BEGIN_HUD\n  TYPE Orbit\nEND_HUD',1)
        for name,mode in (('GL-01',1),('GL-02',2)):
            pattern=re.compile(r'(?ms)^('+re.escape(name)+r':DeltaGlider\n)(.*?)(^END$)')
            matches=list(pattern.finditer(text));require(len(matches)==1,'Original DG declaration differs')
            match=matches[0];require('HUDMode' not in match[2],'Unexpected original saved HUD mode')
            text=text[:match.start()]+match[1]+match[2]+f'  HUDMode {mode}\n'+match[3]+text[match.end():]
    else:
        require(case['id']=='full_scene_landed_pb_focus','Unknown diagnostic case')
        before='  Ship GL-01\n';require(text.count(before)==1,'Original focus declaration differs')
        text=text.replace(before,'  Ship PB-01\n',1)
    require(ships(text)==expected,'A diagnostic input changed the complete vessel graph')
    return text.encode('cp1252'),expected

def configuration(body):
    for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
        require(body.count(line)==1,'Original fixture propagator declarations differ');body=body.replace(line,'')
    return body+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'

def summarize(folder,case):
    config=settings();state=rows(folder/'named-hud-state.csv');_,expected=scenario(case)
    require(len(state)==61 and [int(r['tick']) for r in state]==list(range(61)),'Incomplete actual HUD snapshots')
    require(all(r['object']==case['target'] and int(r['cockpit'])==case['cockpit'] and r['left_mfd']=='1' and r['right_mfd']=='2' and r['vessels']=='8' for r in state),'Actual focused cockpit, instruments or complete scene differs')
    require(int(state[0]['hud'])==case['hud'],'Derived initial HUD mode differs')
    require(all(float(r['seconds'])==int(r['tick'])*.25 and math.isfinite(float(r['mjd'])) for r in state),'Actual original simulation clock differs')
    vessel=rows(folder/'named-vessel-state.csv');require(len(vessel)==61*8,'Incomplete complete-scene vessel snapshots')
    for tick in range(61):
        batch=[r for r in vessel if r['tick']==str(tick)]
        require(len(batch)==8 and {r['object']:r['class'] for r in batch}==expected,'An actual original scene object is missing or replaced')
        require(all(math.isfinite(float(v)) for r in batch for k,v in r.items() if k not in ('object','class')),'Nonfinite actual vessel state')
    changes=[]
    for r in state:
        if not changes or changes[-1]['hud']!=int(r['hud']):changes.append(dict(tick=int(r['tick']),seconds=float(r['seconds']),hud=int(r['hud'])))
    text=rows(folder/'instrument-text.csv');titles={};nonfinite=[];anomaly_text={}
    for row in text:
        value=bytes.fromhex(row['text_hex']).decode('ascii',errors='replace')
        if value.startswith(('Orbit:','Surface:')):titles[row['surface']]=value
        if value.startswith(('TrA ','TrL ')):
            label=value.split()[0];anomaly_text.setdefault(label,dict(first=value));anomaly_text[label]['last']=value
        if re.search(r'(?i)(?<![a-z])[-+]?(?:nan|inf)(?![a-z])',value):nonfinite.append(dict(surface=row['surface'],label=value.split()[0],text=value))
    visual=rows(folder/'visual-events.csv');gl2=[int(r['frame']) for r in visual if r['event']=='register' and r['object']=='GL-02']
    require(len(gl2)==1,'Complete second DG visual registration missing or repeated')
    life=json.loads((folder/'graphics-lifecycle.json').read_text());require(life['context_deleted'] and life['successful_presents']==60,'Incomplete real renderer lifecycle')
    for frame in (20,50):require((folder/f'instrument-{frame}.rgba').stat().st_size==1280*720*4,'Actual renderer readback missing')
    return dict(initial_hud=int(state[0]['hud']),final_hud=int(state[-1]['hud']),hud_changes=changes,second_DG_visual_registration_frames=gl2,nonfinite_text_labels=sorted({r['label'] for r in nonfinite}),nonfinite_text_values=sorted({r['text'] for r in nonfinite}),nonfinite_text_draws=len(nonfinite),orbital_anomaly_first_last=anomaly_text,actual_vessels=expected,successful_presents=60,raw_state_sha256=sha(folder/'named-hud-state.csv'),raw_vessel_state_sha256=sha(folder/'named-vessel-state.csv'))
