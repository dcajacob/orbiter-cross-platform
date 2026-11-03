#!/usr/bin/env python3
"""Run the original stock glass, panel and virtual cockpits in the native production engine."""
import argparse,csv,json,math,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT/'Tests/Production'),str(ROOT/'Tests/Production/Client')]
from reference import fixture
from compare import compare
from frozen import metadata
from regression import mfd_images
from mesa_runtime import require,digest
from run_client import png

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('executable','assets','data','modules','planets','frozen','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--configuration',choices=('Debug','Release'),required=True)
    p.add_argument('--case',action='append')
    a=p.parse_args();pins=metadata(HERE/'Reference/provenance.json')
    require(json.loads((a.frozen/'provenance.json').read_text())==pins,'Staged reference identity differs')
    for name,checksum in pins['reference_files_sha256'][a.configuration].items():
        require(digest(a.frozen/a.configuration/name)==checksum,'Frozen cockpit file differs: '+name)
    settings=json.loads((HERE/'cases.json').read_text())
    supported={c['id'] for c in settings['cases']}
    require(not a.case or set(a.case)<=supported,'Requested native cockpit case is unsupported')
    settings['cases']=[c for c in settings['cases'] if not a.case or c['id'] in a.case]
    require(settings['cases'],'No native cockpit cases selected')
    require(not a.output.exists(),'Candidate output exists; replacement is forbidden')
    output=a.output.resolve();output.mkdir(parents=True)
    report=dict(status='pending',reference_run=pins['run_id'],configuration=a.configuration,
        scope='Stock PB glass and DG/DG-S 2D and virtual cockpit rendering',cases={})
    try:
        for case in settings['cases']:
            name=case['id'];runs=[]
            for repeat in (1,2):
                directory=output/(name+'-'+str(repeat));directory.mkdir();runs.append(directory)
                (directory/'cockpit.scn').write_text(fixture(case))
                config=(ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()
                config+='\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'
                (directory/'Orbiter.cfg').write_text(config)
                (directory/'instrument-evidence.enabled').write_text('Original native cockpit comparison; unchanged budgets.\n')
                (directory/'replay.csv').write_text('tick,phase,action,value\n'
                    f"0,pre,mfd,0 {case['left']}\n0,pre,mfd,1 {case['right']}\n0,pre,hud,{case['hud']}\n"
                    f"10,pre,hud,{case['hud']%3+1}\n30,pre,hud,{case['hud']}\n")
                command=[str(a.executable.resolve())]
                for key in ('assets','data','modules','planets'):command+=['--'+key,str(getattr(a,key).resolve())]
                command+=['--config',str(directory/'Orbiter.cfg'),'--scenario',str(directory/'cockpit.scn'),
                    '--evidence',str(directory),'--replay',str(directory/'replay.csv'),
                    '--frames','60','--fixed-step','0.25','--run']
                (directory/'invocation.json').write_text(json.dumps(command,indent=2)+'\n')
                with (directory/'console.txt').open('w') as log:
                    process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240)
                require(process.returncode==0,'Native cockpit failed: '+str(directory))
                state=list(csv.DictReader((directory/'cockpit-state.csv').open()))
                require(len(state)==61 and all(math.isfinite(float(value)) for row in state for key,value in row.items() if key not in ('object','class')),'Incomplete or nonfinite native cockpit state')
                errors=directory/'graphics-errors.txt'
                require(not errors.exists() or not errors.read_text().strip(),'Native cockpit has OpenGL errors')
                lifecycle=json.loads((directory/'graphics-lifecycle.json').read_text())
                require(lifecycle['context_deleted'] and lifecycle['successful_presents']==60,'Native cockpit lifecycle incomplete')
                renderer=json.loads((directory/'renderer-info.json').read_text())
                require('llvmpipe' in renderer['renderer'].lower(),'Software correctness gate did not load llvmpipe')
                for frame in (20,50):
                    raw=directory/f'instrument-{frame}.rgba';require(len(raw.read_bytes())==1280*720*4,'Incomplete actual cockpit frame')
                    png(raw.with_suffix('.png'),raw.read_bytes(),1280,720)
                    for index in (0,1):
                        stem=directory/f'mfd-{index}-{frame}';image=json.loads(stem.with_suffix('.json').read_text())
                        require(image['colored_pixels']>20 and image['nonwhite_pixels']>image['width']*image['height']//4,'Native original MFD is blank')
                        png(stem.with_suffix('.png'),stem.with_suffix('.rgba').read_bytes(),image['width'],image['height'])
            for filename in ('cockpit-state.csv','instrument-text.csv','instrument-geometry.csv','instrument-self-blits.csv'):
                require((runs[0]/filename).read_bytes()==(runs[1]/filename).read_bytes(),'Native deterministic repeat differs: '+name+'/'+filename)
            for frame in (20,50):
                for stem in (f'instrument-{frame}',f'mfd-0-{frame}',f'mfd-1-{frame}'):
                    require((runs[0]/(stem+'.rgba')).read_bytes()==(runs[1]/(stem+'.rgba')).read_bytes(),'Native image repeat differs: '+name+'/'+stem)
            one={**settings,'cases':[case]}
            report['cases'][name]=dict(comparison=compare(a.frozen/a.configuration,output,one)[name],
                mfd_images=mfd_images(a.frozen/a.configuration,output,one)[name],identical_repeats=True)
            print(name+': native states, drawing, original Windows images and repeats passed',flush=True)
        report['status']='passed'
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:
        (output/'native-cockpit-report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
