#!/usr/bin/env python3
"""Compare native original glass-cockpit hit testing with frozen Windows clicks."""
import argparse,csv,json,math,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE.parent/'Cockpit'),str(HERE.parent),str(HERE.parent/'Client')]
from capture import settings
from reference import fixture
from compare import compare
from regression import mfd_images
from frozen_controls import metadata
from mesa_runtime import require,digest
from run_client import png

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','frozen','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    a=p.parse_args();config=settings();pins=metadata()
    require(json.loads((a.frozen/'provenance.json').read_text())==pins,'Staged original controls differ')
    for name,checksum in pins['reference_files_sha256'][a.configuration].items():
        require(digest(a.frozen/a.configuration/name)==checksum,'Frozen original control file differs: '+name)
    # Real DG/DG-S modules and panel/VC controls have separate, unfinished gates.
    config['cases']=[c for c in config['cases'] if c['cockpit']==1]
    require(len(config['cases'])==1,'Native glass control case is missing')
    require(not a.output.exists(),'Candidate output exists; replacement is forbidden')
    output=a.output.resolve();output.mkdir(parents=True)
    report=dict(status='pending',reference_run=pins['run_id'],configuration=a.configuration,
        scope='Original native glass Pane hit testing; replay dispatch, not an OS window transport test',cases={})
    try:
        for case in config['cases']:
            name=case['id'];runs=[]
            for repeat in (1,2):
                directory=output/(name+'-'+str(repeat));directory.mkdir();runs.append(directory)
                text=fixture(case);start=text.index('PB:ShuttlePB\n');end=text.index('\nEND\n',start)
                (directory/'cockpit.scn').write_text(text[:end]+'\n  RCSMODE 1'+text[end:])
                (directory/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+
                    '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                for marker in ('instrument-evidence.enabled','control-evidence.enabled'):
                    (directory/marker).write_text('Original native cockpit controls; unchanged frozen budgets.\n')
                replay=['tick,phase,action,value',f"0,pre,mfd,0 {case['left']}",f"0,pre,mfd,1 {case['right']}",f"0,pre,hud,{case['hud']}"]
                for action in case['actions']:
                    require(action['coordinates']=='pixel','Native glass controls require original pixel coordinates')
                    x,y=action['point'][:2];replay.append(f"{action['tick']},pre,mouse,{action['event']} {x} {y}")
                (directory/'replay.csv').write_text('\n'.join(replay)+'\n')
                command=[str(a.executable.resolve())]
                for key in ('assets','data','modules','planets'):command+=['--'+key,str(getattr(a,key).resolve())]
                command+=['--config',str(directory/'Orbiter.cfg'),'--scenario',str(directory/'cockpit.scn'),
                    '--evidence',str(directory),'--replay',str(directory/'replay.csv'),'--frames','60','--fixed-step','0.25','--run']
                (directory/'invocation.json').write_text(json.dumps(command,indent=2)+'\n')
                with (directory/'console.txt').open('w') as log:
                    process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240)
                require(process.returncode==0,'Native control process failed: '+str(directory))
                state=list(csv.DictReader((directory/'cockpit-state.csv').open()))
                require(len(state)==61 and all(math.isfinite(float(v)) for row in state for k,v in row.items() if k not in ('object','class')),'Native controls have incomplete/nonfinite state')
                for row in state:require(int(row['rcs_mode'])==(2 if 11<=int(row['tick'])<=30 else 1),'Native original hit testing did not switch the actual vessel RCS')
                errors=directory/'graphics-errors.txt'
                require(not errors.exists() or not errors.read_text().strip(),'Native controls have OpenGL errors')
                lifecycle=json.loads((directory/'graphics-lifecycle.json').read_text())
                require(lifecycle['context_deleted'] and lifecycle['successful_presents']==60,'Native control lifecycle incomplete')
                renderer=json.loads((directory/'renderer-info.json').read_text())
                require('llvmpipe' in renderer['renderer'].lower(),'Native control correctness gate requires llvmpipe')
                for frame in (20,50):
                    raw=directory/f'instrument-{frame}.rgba';png(raw.with_suffix('.png'),raw.read_bytes(),1280,720)
                    for index in (0,1):
                        stem=directory/f'mfd-{index}-{frame}';image=json.loads(stem.with_suffix('.json').read_text())
                        require(image['colored_pixels']>20 and image['nonwhite_pixels']>image['width']*image['height']//4,'Native original MFD is blank')
                        png(stem.with_suffix('.png'),stem.with_suffix('.rgba').read_bytes(),image['width'],image['height'])
            for filename in ('cockpit-state.csv','control-inputs.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
                require((runs[0]/filename).read_bytes()==(runs[1]/filename).read_bytes(),'Native control repeat differs: '+filename)
            original=a.frozen/a.configuration/(name+'-1')
            require((original/'control-inputs.csv').read_text()==(runs[0]/'control-inputs.csv').read_text(),'Native mouse coordinates, events or ticks differ from original Windows')
            for frame in (20,50):
                for stem in (f'instrument-{frame}',f'mfd-0-{frame}',f'mfd-1-{frame}'):
                    require((runs[0]/(stem+'.rgba')).read_bytes()==(runs[1]/(stem+'.rgba')).read_bytes(),'Native control image repeat differs')
            report['cases'][name]=dict(comparison=compare(a.frozen/a.configuration,output,config)[name],
                mfd_images=mfd_images(a.frozen/a.configuration,output,config)[name],identical_repeats=True,
                exact_original_discrete_inputs=True,actual_vessel_rcs_modes_verified=True)
        report['status']='passed';print(json.dumps(report,indent=2))
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:(output/'native-control-report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
