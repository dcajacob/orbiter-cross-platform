#!/usr/bin/env python3
"""Reject damaged copies of real original legacy station observations."""
import argparse
import csv
import io
import json
from pathlib import Path
import tempfile

from original import digest,inspect_artifacts,require,rows,settings


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture',type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--case',required=True)
    p.add_argument('--output',type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Legacy station gate output exists')
    config=settings();case=next(c for c in config['cases'] if c['id']==a.case)
    positive=inspect_artifacts(a.capture,case,config)
    before={str(p.relative_to(a.capture)):digest(p) for p in a.capture.rglob('*') if p.is_file()}
    controls=[]
    with tempfile.TemporaryDirectory(prefix='orbiter-legacy-station-gate-') as temporary:
        root=Path(temporary)
        names=['missing_background_iss','missing_background_module1','missing_docking_port','duplicate_docking_port',
               'changed_iss_capabilities','nonfinite_state','shifted_clock','missing_final_tick',
               'changed_scenario','rewritten_scenario_line_endings','incomplete_teardown','wrong_renderer']
        for name in names:
            out=root/name;out.mkdir()
            for file in a.capture.rglob('*'):
                if file.is_file():
                    target=out/file.relative_to(a.capture);target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(file)
            def replace(file,data):
                path=out/file;path.unlink();path.write_bytes(data)
            def rewrite(file,values):
                stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(values[0]))
                writer.writeheader();writer.writerows(values);replace(file,stream.getvalue().encode())
            if name in ('missing_background_iss','missing_background_module1'):
                kind='iss' if name.endswith('_iss') else 'module1'
                values=rows(out/'stock-vessel-state.csv')
                target=next(r for r in values if r['tick']=='3' and r['class'].lower()==kind)
                values.remove(target);rewrite('stock-vessel-state.csv',values)
            elif name in ('missing_docking_port','duplicate_docking_port'):
                values=rows(out/'stock-vessel-docks.csv')
                if name=='missing_docking_port':del values[3]
                else:values.append(values[3])
                rewrite('stock-vessel-docks.csv',values)
            elif name in ('changed_iss_capabilities','nonfinite_state','shifted_clock','missing_final_tick'):
                values=rows(out/'stock-vessel-state.csv')
                target=next(r for r in values if r['class'].lower()=='iss')
                if name=='changed_iss_capabilities':target['docks']='2'
                elif name=='nonfinite_state':target['x']='nan'
                elif name=='shifted_clock':target['seconds']='1'
                else:values=[r for r in values if r['tick']!='60']
                rewrite('stock-vessel-state.csv',values)
            elif name.startswith('changed_scenario') or name=='rewritten_scenario_line_endings':
                path='Scenarios/Behavior.scn';value=(out/path).read_bytes()
                value=value+b'\n; changed\n' if name=='changed_scenario' else value.replace(b'\r\n',b'\n')
                if value==(out/path).read_bytes():value=value.replace(b'\n',b'\r\n')
                replace(path,value)
            else:
                file='graphics-lifecycle.json' if name=='incomplete_teardown' else 'renderer-info.json'
                value=json.loads((out/file).read_text())
                value['context_deleted' if name=='incomplete_teardown' else 'renderer']=False if name=='incomplete_teardown' else 'wrong GPU'
                replace(file,(json.dumps(value)+'\n').encode())
            try:inspect_artifacts(out,case,config)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=name,reason=str(error)))
            else:raise ValueError('Damaged original legacy capture accepted: '+name)
    require(before=={str(p.relative_to(a.capture)):digest(p) for p in a.capture.rglob('*') if p.is_file()},
            'Owning original legacy capture changed')
    a.output.write_text(json.dumps(dict(status='passed',controls=controls,positive=positive,
        source_sha256=digest(Path(__file__)),original_capture_unchanged=True),indent=2)+'\n')
    print('Twelve damaged original legacy station captures rejected')


if __name__=='__main__':main()
