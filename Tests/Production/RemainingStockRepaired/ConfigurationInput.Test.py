#!/usr/bin/env python3
"""Reject changed copies of a real startup configuration, including coherent hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import capture
import configuration_input as configuration


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--kind',choices=('repaired-windows','native'),default='repaired-windows')
    a=p.parse_args();configuration.require(not a.output.exists(),'Fresh startup-configuration control output required')
    producer=subprocess.check_output(['git','-C',str(capture.ROOT),'rev-parse','HEAD'],text=True).strip()
    expected=configuration.expected(capture.ROOT,producer,a.kind)
    positive=configuration.inspect(a.capture,expected)
    names=('invocation.json',configuration.SNAPSHOT,'Orbiter.cfg')
    before={n:configuration.sha(a.capture/n) for n in names}
    initial=(a.capture/configuration.SNAPSHOT).read_bytes();final=(a.capture/'Orbiter.cfg').read_bytes();rewritten=initial!=final
    damages=['missing_snapshot','missing_descriptor','changed_hash','wrong_protocol','wrong_runtime_path','wrong_snapshot_path',
             'forced_propagators_with_consistent_hash','changed_physics_with_consistent_hash','mixed_newlines_with_consistent_hash']
    if rewritten:damages.append('rewritten_output_as_input')
    controls=[]
    with tempfile.TemporaryDirectory(prefix='orbiter-startup-configuration-controls-') as temporary:
        root=Path(temporary)
        for label in ('lf','crlf',*damages):
            out=root/label;out.mkdir()
            for name in names:shutil.copy2(a.capture/name,out/name)
            invocation=json.loads((out/'invocation.json').read_text());record=invocation['configuration_input']
            body=initial.replace(b'\r\n',b'\n');coherent=False
            if label in ('lf','crlf'):
                body=body if label=='lf' else body.replace(b'\n',b'\r\n');coherent=True
            elif label=='missing_snapshot':(out/configuration.SNAPSHOT).unlink()
            elif label=='missing_descriptor':del invocation['configuration_input']
            elif label=='changed_hash':record['sha256']='0'*64
            elif label=='wrong_protocol':record['protocol']='stock-staged-configuration-v0'
            elif label=='wrong_runtime_path':record['runtime_path']='Different.cfg'
            elif label=='wrong_snapshot_path':record['snapshot_path']='../staged-Orbiter.cfg'
            elif label=='forced_propagators_with_consistent_hash':body+=b'\nPropStages = 1\nPropStage0 = 1 1 1\n';coherent=True
            elif label=='changed_physics_with_consistent_hash':
                anchor=b'VesselCollision = FALSE';configuration.require(body.count(anchor)==1,'Actual startup physics control anchor differs')
                body=body.replace(anchor,b'VesselCollision = TRUE',1);coherent=True
            elif label=='mixed_newlines_with_consistent_hash':body=body.replace(b'\n',b'\r\n',1);coherent=True
            else:body=final;coherent=True
            if coherent:
                (out/configuration.SNAPSHOT).write_bytes(body);record['sha256']=configuration.sha(out/configuration.SNAPSHOT)
            (out/'invocation.json').write_text(json.dumps(invocation,indent=2)+'\n')
            if label in ('lf','crlf'):configuration.inspect(out,expected);continue
            try:configuration.inspect(out,expected)
            except (ValueError,OSError,KeyError) as error:controls.append(dict(control=label,reason=str(error)))
            else:raise ValueError('Changed actual startup input accepted: '+label)
    configuration.require(before=={n:configuration.sha(a.capture/n) for n in names},'Owning startup/runtime configuration or invocation changed')
    a.output.write_text(json.dumps(dict(status='passed',protocol=configuration.PROTOCOL,producer_commit=producer,kind=a.kind,
        positive=positive,line_ending_reader_positives=2,runtime_configuration_was_rewritten=rewritten,controls=controls,
        owning_configuration_files_sha256=before,owning_capture_unchanged=True,test_sha256=configuration.sha(Path(__file__)),
        reader_sha256=configuration.sha(Path(configuration.__file__)),native_admission_qualified=False,phase6_complete=False),indent=2)+'\n')
    print('Actual startup configuration passes;',len(controls),'damaged descriptor/hash/physics/format copies rejected')


if __name__=='__main__':main()
