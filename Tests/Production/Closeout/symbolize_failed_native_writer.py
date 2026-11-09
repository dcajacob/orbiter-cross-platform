#!/usr/bin/env python3
"""Map original leaked-allocation PCs to retained provider ELF bytes without executing them."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import zipfile
from contracts import require,sha
from inspect_failed_native_writers import PINS,SOURCE,RUN
import restore_hosted_native_providers as providers


def load(path):return json.loads(Path(path).read_text())


def mappings(text):
    result=[]
    for line in text.splitlines():
        fields=line.split(None,5)
        if len(fields)!=6 or not fields[5].startswith('/'):continue
        first,last=fields[0].split('-')
        result.append(dict(first=int(first,16),last=int(last,16),offset=int(fields[2],16),path=fields[5]))
    require(result,'Actual original /proc mapping records required');return result


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true','Hosted immutable symbol inspection only')
    root=Path('out/native-writer-symbols');writer=root/'writer';dependency=root/'providers';output=root/'inspection'
    require(not output.exists(),'Fresh independent symbol inspection required');output.mkdir(parents=True)
    api=load(writer/'api.json');job_id,ident,size,digest=PINS['Debug-sse2'];job=next(j for j in api['jobs'] if j['id']==job_id)
    require(api['run']['id']==RUN and api['run']['head_sha']==SOURCE and api['run']['run_attempt']==1 and
            job['status']=='completed' and job['conclusion']=='failure' and job['head_sha']==SOURCE and
            api['artifact']['id']==ident and api['artifact']['workflow_run']['id']==RUN and api['artifact']['workflow_run']['head_sha']==SOURCE and
            api['artifact']['digest']=='sha256:'+digest and api['artifact']['size_in_bytes']==size and
            (writer/'producer.zip').stat().st_size==size and sha(writer/'producer.zip')==digest,'Actual retained failed writer API ZIP required')
    provider_api=load(dependency/'api.json');providers.validate_api(provider_api)
    require((dependency/'producer.zip').stat().st_size==providers.SIZE and sha(dependency/'producer.zip')==providers.DIGEST,'Exact original provider API ZIP required')
    maps={};consoles={};raw={};allocations={};wanted=set();workspace='/home/runner/work/orbiter-cross-platform/orbiter-cross-platform/'
    with zipfile.ZipFile(writer/'producer.zip') as archive:
        for identity in ('remaining_stock_001-1','remaining_stock_002-1'):
            prefix='native-stock-writer/Debug-sse2/'+identity+'/'
            for name in ('observer-loaded-maps.txt','console.log','graphics-lifecycle.json','stock-vessel-complete.txt','process-result.json'):
                body=archive.read(prefix+name);target=output/identity/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
                raw[prefix+name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
            maps[identity]=mappings((output/identity/'observer-loaded-maps.txt').read_text())
            consoles[identity]=(output/identity/'console.log').read_text()
            require('ERROR: LeakSanitizer:' in consoles[identity],'Actual allocation diagnostic missing')
            stack=consoles[identity].split('ERROR: LeakSanitizer:',1)[1];frames=[]
            for value in re.findall(r'#\d+ (0x[0-9a-f]+)',stack):
                address=int(value,16);found=[m for m in maps[identity] if m['first']<=address<m['last']]
                require(len(found)<=1,'Ambiguous actual original mapped allocation frame')
                frame=dict(address=value,mapping=found[0] if found else None)
                if found:
                    path=found[0]['path'];frame['elf_offset']=hex(address-found[0]['first']+found[0]['offset'])
                    if path.startswith(workspace+'out/hosted-native-providers/'):
                        relative=path[len(workspace):];providers.safe(relative);wanted.add(relative);frame['provider_member']=relative
                frames.append(frame)
            require(frames,'Actual original LSan allocation frames missing');allocations[identity]=frames
    with zipfile.ZipFile(dependency/'producer.zip') as archive:
        def member(leaf):
            names=[n for n in archive.namelist() if Path(n).name==leaf];require(len(names)==1,'Unique original sealed provider payload required');return names[0]
        sealed=json.loads(archive.read(member('hosted-native-provider.json')))
        bundle=dependency/'providers.tar.gz'
        with archive.open(member('hosted-native-providers.tar.gz')) as incoming,bundle.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
    require(sealed['source_commit']==providers.PRODUCER and sha(bundle)==sealed['archive_sha256'] and bundle.stat().st_size==sealed['archive_bytes'],
            'Original source-bound provider inner archive differs')
    require(wanted and all(name in sealed['members'] for name in wanted),'Actual mapped allocation provider absent from exact retained package')
    extracted={}
    with tarfile.open(bundle,'r:gz') as archive:
        for entry in archive:
            if entry.name not in wanted:continue
            require(entry.isfile() and entry.name not in extracted and entry.size<512*1024**2,'Exact finite provider ELF member required')
            target=output/'elf'/entry.name;target.parent.mkdir(parents=True,exist_ok=True)
            with archive.extractfile(entry) as incoming,target.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
            require(sha(target)==sealed['members'][entry.name]['sha256'],'Actual mapped provider ELF differs from complete original manifest')
            with target.open('rb') as stream:require(stream.read(4)==b'\x7fELF','Mapped provider is not an ELF object')
            extracted[entry.name]=target
    require(set(extracted)==wanted,'Every mapped allocation provider ELF must be retained')
    for identity,frames in allocations.items():
        for frame in frames:
            if 'provider_member' not in frame:continue
            path=extracted[frame['provider_member']]
            frame['provider_sha256']=sha(path)
            frame['addr2line']=subprocess.check_output(['addr2line','-f','-C','-e',str(path),frame['elf_offset']],text=True)
        print(identity+' actual allocation mapping:\n'+json.dumps(frames,indent=2),flush=True)
    report=dict(status='mapped-original-failed-allocation-PCs-to-retained-provider-bytes-only',original_capture_source=SOURCE,
        original_capture_run=RUN,original_capture_artifact=ident,provider_source=providers.PRODUCER,
        original_provider_artifact=providers.ARTIFACT,files=raw,allocations=allocations,
        simulation_executed=False,binaries_rebuilt=False,qualification_granted=False,phase6_complete=False)
    (output/'symbols.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
