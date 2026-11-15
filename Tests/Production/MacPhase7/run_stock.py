"""Try one locked stock flight with the native production Cocoa renderer."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import subprocess

STOCK = 'Scenarios/Delta-glider/DG Mk4 in orbit.scn'
ROSTER = {'ISS','Mir','Luna-OB1','GL-01','SH-03','PB-01','GL-02','SH-01'}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def run(args):
    output = args.output
    output.mkdir(parents=True)
    root = Path.cwd()
    lock = json.loads((root/'Tests/Production/production-source.lock.json').read_text())
    scenario = args.assets/STOCK
    data = scenario.read_bytes()
    original_sha = next(item['sha256'] for item in lock['scenarios'] if item['path']==STOCK)
    require(sha256(data.replace(b'\r\n',b'\n')).hexdigest()==original_sha and data==(root/STOCK).read_bytes(),
            'The original stock scenario changed')
    cfg = output/'Orbiter.cfg'
    cfg.write_bytes((root/'Tests/Production/NativeScene/Orbiter.cfg').read_bytes())
    argv=[str(args.engine/'orbiter-production'), '--assets', str(args.assets),
          '--data', str(args.data), '--modules', str(args.engine/'NativeModules'),
          '--planets', str(args.planets), '--config', str(cfg), '--scenario', str(scenario),
          '--save', str(output/'Flight.scn'), '--evidence', str(output),
          '--run', '--frames', '60', '--fixed-step', '0.0625', '--capture-time', '3.125']
    (output/'invocation.json').write_text(json.dumps(argv,indent=2)+'\n')
    with (output/'console.log').open('w') as log:
        proc=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    require(proc.returncode==0, f'Native stock simulator returned {proc.returncode}')
    life=json.loads((output/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=60,successful_presents=60,context_deleted=True),
            'Native stock render/present/cleanup incomplete')
    window=json.loads((output/'native-window.json').read_text())
    require(window['backend']=='cocoa', 'Native window did not use Cocoa')
    renderer=json.loads((output/'renderer-info.json').read_text())
    require('Apple Software Renderer' in renderer['renderer'], 'Hosted macOS software-renderer identity differs')
    with (output/'scene.csv').open(newline='') as stream:
        scene=list(csv.DictReader(stream))
    require({row['object'] for row in scene if row['type']=='vessel'}==ROSTER,
            'The stock vessel roster changed')
    require(any(row['object']=='GL-01' and row['class']=='DeltaGlider' and int(row['groups'])>0
                for row in scene), 'The focused production Delta-glider mesh was not available')
    geometry=json.loads((output/'scene-summary.json').read_text())
    require(geometry['mesh_draw_calls']>0 and geometry['indices']>0,
            'The production renderer submitted no mesh geometry')
    console=(output/'console.log').read_text(errors='replace')
    require('Production DeltaGlider flight.' in console, 'Original Delta-glider cockpit did not start')
    errors=output/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(), 'OpenGL reported errors')
    require(scenario.read_bytes()==data, 'The stock flight file changed while running')
    result=dict(source=args.source,scenario=STOCK,input_sha256=sha256(data).hexdigest(),
                lifecycle=life,renderer=renderer['renderer'],vessels=sorted(ROSTER),
                full_runs_invoked=False,physical_graphics_qualified=False)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('engine','assets','data','planets','output'):
        parser.add_argument('--'+name,type=lambda path:Path(path).resolve(),required=True)
    parser.add_argument('--source',required=True)
    run(parser.parse_args())
