#!/usr/bin/env python3
"""Exercise the saved-state reader with actual Windows output and damaged copies."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from saved_state import parse_saved,content_differences,require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Fresh saved-state control output required')
    body=a.capture.read_bytes();text=body.decode('cp1252').replace('\r\n','\n');positive=parse_saved(a.capture);controls=[]
    with tempfile.TemporaryDirectory(prefix='orbiter-saved-state-controls-') as temporary:
        root=Path(temporary)
        for newline in ('lf','crlf'):
            target=root/(newline+'.scn');target.write_bytes((text if newline=='lf' else text.replace('\n','\r\n')).encode('cp1252'))
            require(not content_differences(positive,parse_saved(target)),'Transport line endings changed parsed state')
        for damage in ('missing_ship_list_end','missing_vessel_end','duplicate_vessel','missing_environment_end',
                       'wrong_block_end','nonfinite_date','missing_focus_target'):
            lines=text.splitlines()
            if damage=='missing_ship_list_end':lines.remove('END_SHIPS')
            elif damage=='missing_vessel_end':lines.remove('END')
            elif damage=='duplicate_vessel':
                start=lines.index('BEGIN_SHIPS')+1;end=lines.index('END',start)+1
                lines[lines.index('END_SHIPS'):lines.index('END_SHIPS')]=lines[start:end]
            elif damage=='missing_environment_end':lines.remove('END_ENVIRONMENT')
            elif damage=='wrong_block_end':lines[lines.index('END_ENVIRONMENT')]='END_CAMERA'
            elif damage=='nonfinite_date':
                index=next(i for i,line in enumerate(lines) if line.strip().startswith('Date MJD '));lines[index]='  Date MJD nan'
            else:
                index=next(i for i,line in enumerate(lines) if line.strip().startswith('Ship '));lines[index]='  Ship AbsentVessel'
            target=root/(damage+'.scn');target.write_text('\n'.join(lines)+'\n',encoding='cp1252')
            try:parse_saved(target)
            except (ValueError,OSError) as error:controls.append(dict(control=damage,reason=str(error)))
            else:raise ValueError('Malformed actual saved-state copy accepted: '+damage)
        for damage in ('changed_module_value','missing_module_record','changed_saved_class','changed_camera'):
            lines=text.splitlines()
            if damage in ('changed_module_value','missing_module_record'):
                index=next(i for i,line in enumerate(lines) if line.strip().startswith('TANK '))
                if damage=='missing_module_record':del lines[index]
                else:
                    value=lines[index].split();value[-1]=str(float(value[-1])+1);lines[index]='      '+' '.join(value)
            elif damage=='changed_saved_class':
                index=next(i for i,line in enumerate(lines) if ':' in line and line and not line[0].isspace());name=lines[index].split(':',1)[0];lines[index]=name+':DifferentClass'
            else:
                index=next(i for i,line in enumerate(lines) if line.strip().startswith('FOV '));lines[index]='  FOV 61.00'
            target=root/(damage+'.scn');target.write_text('\n'.join(lines)+'\n',encoding='cp1252')
            differences=content_differences(positive,parse_saved(target));require(differences,'Saved field change was discarded: '+damage)
            controls.append(dict(control=damage,reason='Complete parsed content differs',paths=[r['path'] for r in differences]))
    require(a.capture.read_bytes()==body,'Owning actual saved state changed')
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    a.output.write_text(json.dumps(dict(status='passed-reader-controls',actual_saved_state_sha256=positive['sha256'],
        actual_vessels=len(positive['ships']),actual_module_records=sum(len(v['records']) for v in positive['ships'].values()),
        controls=controls,owning_capture_unchanged=True,source_sha256=sha(Path(__file__)),reader_sha256=sha(Path(__file__).with_name('saved_state.py')),
        native_admission_qualified=False,phase6_complete=False,scope='Actual saved-state parser/content controls only. No numeric tolerance or physical/visual persistence qualification is inferred.'),indent=2)+'\n')
    print('Actual saved-state reader: two line-ending positives, seven malformed copies rejected and four field changes detected')


if __name__=='__main__':main()
