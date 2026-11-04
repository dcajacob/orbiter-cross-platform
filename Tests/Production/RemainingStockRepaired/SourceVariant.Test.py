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
    with tempfile.TemporaryDirectory(prefix='orbiter-electrical-source-control-') as temporary:
        for name in ('missing_initial_current','changed_initial_current','changed_thermal_formula','false_initialization_policy'):
            out=Path(temporary)/name;shutil.copytree(a.sources,out)
            report=json.loads((out/'source-variant.json').read_text())
            if name=='false_initialization_policy':report['initialization_repair']['initial_value']=1
            else:
                path=out/'source'/electrical;body=path.read_bytes()
                anchor=b'  Amperes=0; // No previous current before the first refresh.\n'
                if name=='missing_initial_current':replacement=b''
                elif name=='changed_initial_current':replacement=anchor.replace(b'Amperes=0;',b'Amperes=1;')
                else:
                    anchor=b'energy=(Amperes*Volts / max_power) * clogg*0.05*dt;'
                    replacement=anchor.replace(b'0.05',b'0.5')
                audit.require(body.count(anchor)==1,'Actual electrical control anchor differs')
                path.write_bytes(body.replace(anchor,replacement,1));value=audit.sha(path)
                # Make the damaged manifest internally consistent. The reader
                # must derive the permitted delta from the frozen original.
                report['staged_files_sha256'][electrical]=value
                report['declared_changes'][electrical]['repaired_sha256']=value
                report['current_dragonfly_producer_sha256'][electrical]=value
            (out/'source-variant.json').write_text(json.dumps(report,indent=2)+'\n')
            try:audit.source_variant(out,producer)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=name,reason=str(error)))
            else:raise ValueError('Damaged electrical source variant accepted: '+name)
    audit.require(hashes(a.sources)==before,'Owning repaired source tree changed during controls')
    source=Path(__file__)
    a.output.write_text(json.dumps(dict(status='passed',producer_commit=producer,positive=positive,controls=controls,
        owning_source_files_sha256=before,owning_sources_unchanged=True,test_sha256=audit.sha(source),
        independent_reader_sha256=audit.sha(source.parent/'audit.py'),native_admission_qualified=False,phase6_complete=False),indent=2)+'\n')
    print('Actual repaired source v2 passes; four self-consistent damaged electrical-source/policy copies rejected')


if __name__=='__main__':main()
