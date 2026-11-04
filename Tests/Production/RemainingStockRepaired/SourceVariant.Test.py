#!/usr/bin/env python3
"""Reject self-consistent damaged copies of the declared repaired module sources."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

import audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('sources','output'):p.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
    a=p.parse_args();audit.require(not a.output.exists(),'Fresh source-variant control output required')
    manifest=json.loads((a.sources/'source-variant.json').read_text());producer=manifest['producer_commit']
    positive=audit.source_variant(a.sources,producer)
    def hashes(root):return {p.relative_to(root).as_posix():audit.sha(p) for p in root.rglob('*') if p.is_file()}
    before=hashes(a.sources);controls=[]
    electrical='Src/Vessel/Dragonfly/Esystems.cpp'
    adi='Src/Vessel/Dragonfly/instruments.cpp'
    header='Src/Vessel/Dragonfly/instruments.h'
    cases=['missing_initial_current','changed_initial_current','changed_thermal_formula','false_initialization_policy']
    if manifest['protocol'] in ('remaining-stock-repaired-sources-v3','remaining-stock-repaired-sources-v4'):
        cases+=['missing_initial_adi_request','changed_initial_adi_request','changed_adi_attitude_formula','false_adi_initialization_policy','falsely_label_as_v2']
    if manifest['protocol']=='remaining-stock-repaired-sources-v4':
        cases+=['missing_gauge_terminator','changed_gauge_capacity','false_gauge_storage_policy','falsely_label_as_v3']
    with tempfile.TemporaryDirectory(prefix='orbiter-electrical-source-control-') as temporary:
        for name in cases:
            out=Path(temporary)/name;shutil.copytree(a.sources,out)
            report=json.loads((out/'source-variant.json').read_text())
            if name=='false_initialization_policy':report['initialization_repair']['initial_value']=1
            elif name=='false_adi_initialization_policy':report['adi_reference_request_repair']['initial_value']=1
            elif name=='false_gauge_storage_policy':report['gauge_unit_buffer_repair']['capacity']=5
            elif name=='falsely_label_as_v3':
                report['protocol']='remaining-stock-repaired-sources-v3';del report['gauge_unit_buffer_repair']
            elif name=='falsely_label_as_v2':
                report['protocol']='remaining-stock-repaired-sources-v2';del report['adi_reference_request_repair']
            else:
                relative=header if name in ('missing_gauge_terminator','changed_gauge_capacity') else adi if name in ('missing_initial_adi_request','changed_initial_adi_request','changed_adi_attitude_formula') else electrical
                path=out/'source'/relative;body=path.read_bytes()
                anchor=b'  Amperes=0; // No previous current before the first refresh.\n'
                if name in ('missing_gauge_terminator','changed_gauge_capacity'):
                    anchor=b'char unit[6];';replacement=b'char unit[5];' if name=='missing_gauge_terminator' else b'char unit[7];'
                elif name in ('missing_initial_adi_request','changed_initial_adi_request'):
                    anchor=b'ref_handle=0; // No pending reference capture before user input.\n'
                    replacement=b'' if name=='missing_initial_adi_request' else anchor.replace(b'ref_handle=0;',b'ref_handle=1;')
                elif name=='changed_adi_attitude_formula':
                    anchor=b'glRotatef(-now.z/Pi*180.0';replacement=anchor.replace(b'180.0',b'180.1')
                elif name=='missing_initial_current':replacement=b''
                elif name=='changed_initial_current':replacement=anchor.replace(b'Amperes=0;',b'Amperes=1;')
                else:
                    anchor=b'energy=(Amperes*Volts / max_power) * clogg*0.05*dt;'
                    replacement=anchor.replace(b'0.05',b'0.5')
                audit.require(body.count(anchor)==1,'Actual electrical control anchor differs')
                path.write_bytes(body.replace(anchor,replacement,1));value=audit.sha(path)
                # Make the damaged manifest internally consistent. The reader
                # must derive the permitted delta from the frozen original.
                report['staged_files_sha256'][relative]=value
                report['declared_changes'][relative]['repaired_sha256']=value
                report['current_dragonfly_producer_sha256'][relative]=value
            (out/'source-variant.json').write_text(json.dumps(report,indent=2)+'\n')
            try:audit.source_variant(out,producer)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=name,reason=str(error)))
            else:raise ValueError('Damaged initialization/drawing source variant accepted: '+name)
    audit.require(hashes(a.sources)==before,'Owning repaired source tree changed during controls')
    source=Path(__file__)
    a.output.write_text(json.dumps(dict(status='passed',producer_commit=producer,positive=positive,controls=controls,
        owning_source_files_sha256=before,owning_sources_unchanged=True,test_sha256=audit.sha(source),
        independent_reader_sha256=audit.sha(source.parent/'audit.py'),native_admission_qualified=False,phase6_complete=False),indent=2)+'\n')
    print('Actual repaired source',manifest['protocol'],'passes;',len(controls),'self-consistent damaged initialization/drawing/policy copies rejected')


if __name__=='__main__':main()
