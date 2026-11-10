#!/usr/bin/env python3
"""Independently replay the exact published provisioning proof without simulator credit."""
import argparse
import hashlib
from pathlib import Path,PurePosixPath
import re
import stat
import subprocess
import zipfile
from urllib.parse import unquote
from contracts import ROOT,require,load,sha,atomic_json
import verify_original_package_pool_preflight as original

SOURCE='a1c48b762333c084e8c8321668c5fd87a94cc0f6'
RUN=42868076233
BRANCH='qualification/class-package-official-pool-preflight-v2'
WORKFLOW='.github/workflows/phase6-original-package-official-pool-preflight-retry.yml'
PINNED={
 'raw':(13789795378,63441040,'a83693ddec0408090682e14c4c8a9e0b89b4232d7d8b604a1e35abc442b587ae','original-package-official-pool-full-provisioning-evidence'),
 'small':(13789930127,98817,'d10e09042bbb2aadc8d6933d80d15dce426213bb650d80d4dfc4504756652a94','original-package-official-pool-small-preflight-receipt')}
PREFIX='snapshot.ubuntu.com_ubuntu_20261109T212432Z_dists_'


def bind_api(api):
    run=api['run'];jobs=api['jobs'];require(api['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform') and run['id']==RUN and run['head_sha']==SOURCE and run['head_branch']==BRANCH and run['path']==WORKFLOW and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success' and run['repository']['private'] is False and run['repository']['full_name']=='dcajacob/orbiter-cross-platform','Exact successful public original provisioning source/run required')
    require(len(jobs)==1 and jobs[0]['id']==130011660555 and jobs[0]['run_id']==RUN and jobs[0]['head_sha']==SOURCE and jobs[0]['status']=='completed' and jobs[0]['conclusion']=='success' and jobs[0]['labels']==['ubuntu-24.04'],'Exact successful standard Ubuntu provisioning job required')
    for kind,(identity,size,digest,name) in PINNED.items():
        a=api['artifacts'][kind];require(a['id']==identity and a['size_in_bytes']==size and a['digest']=='sha256:'+digest and a['name']==name and a['expired'] is False and a['workflow_run']['id']==RUN and a['workflow_run']['head_sha']==SOURCE and a['workflow_run']['head_branch']==BRANCH,'Exact published original provisioning artifact required: '+kind)


def restore_zip(root,archive):
    seen=set();count=0;total=0
    with zipfile.ZipFile(archive) as incoming:
        for item in incoming.infolist():
            name=item.filename;p=PurePosixPath(name)
            require(name and (str(p)==name or item.is_dir() and str(p)+'/'==name) and not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name and name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16),'Safe unique original provisioning ZIP members required')
            seen.add(name.casefold());total+=item.file_size;require(total<512*1024**2 and item.file_size<256*1024**2 and len(seen)<2000,'Bounded metadata-only provisioning archive required')
            dest=root/'out'/name;require(not any(v.is_symlink() for v in [dest,*dest.parents] if v!=root.parent),'Provisioning restoration cannot traverse aliases')
            if item.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
            body=incoming.read(item);require(len(body)==item.file_size,'Complete original provisioning ZIP body required')
            if dest.exists():require(dest.is_file() and dest.read_bytes()==body,'Existing provisioning input cannot be overwritten')
            else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
            count+=1
    return dict(files=count,uncompressed_bytes=total)


def release_hashes(body):
    lines=body.splitlines();require(lines.count('SHA256:')==1,'One signed Release SHA256 table required');table={}
    for line in lines[lines.index('SHA256:')+1:]:
        if not line.startswith(' '):break
        values=line.split();require(len(values)==3 and re.fullmatch('[0-9a-f]{64}',values[0]) and values[1].isdigit() and values[2] not in table,'Unique strong signed Release hash/size/name required')
        table[values[2]]=(values[0],int(values[1]))
    require(table,'Nonempty signed Release hash table required');return table


def planned_package(fields,wanted,pins,found):
    name=fields.get('Filename')
    if name not in wanted:return
    row=wanted[name];require(fields.get('SHA256')==row[4] and fields.get('Size')==row[3] and fields.get('Package') in pins and fields.get('Version')==pins[fields['Package']],'Every planned blob must equal a signed package-index hash/size and original pinned version')
    found.add(name)



def package_path(uri):
    prefix='https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/'
    require(uri.startswith(prefix),'Exact original signed snapshot URI required')
    encoded=uri[len(prefix):]
    # APT escapes literal plus and tilde in URI segments. Decode only those two
    # observed spellings; never apply form decoding (+ is not a space), path
    # traversal decoding, redirects, or changes to any original retained URI.
    require(all(code.lower() in ('%2b','%7e') for code in re.findall('%..',encoded)),'Only observed literal plus/tilde URI escapes may match signed package paths')
    decoded=unquote(encoded,errors='strict')
    require('%' not in decoded and decoded.startswith('pool/') and all(re.fullmatch('[-A-Za-z0-9+_.~]+',part) and part not in ('.','..') for part in decoded.split('/')),'Exact safe signed package filename required')
    return decoded


def inspect_signed_indexes(folder,plan,output):
    output.mkdir();metadata=folder/'signed-metadata';wanted={package_path(r[0]):r for r in plan};require(len(wanted)==len(plan),'Unique original pool paths required')
    pins={}
    for row in (folder/'original-system-packages.txt').read_text().splitlines():
        name,version=row.split('=',1);base=name.split(':')[0];require(base not in pins or pins[base]==version,'One original version per package required');pins[base]=version
    found=set();records=[]
    for suite in ('resolute','resolute-updates','resolute-backports','resolute-security'):
        release=metadata/(PREFIX+suite+'_InRelease');require(release.is_file(),'Every original snapshot suite InRelease must be retained')
        clear=output/(suite+'.Release');status=output/(suite+'.signature-status.log');log=output/(suite+'.signature-stderr.log')
        with status.open('wb') as stdout,log.open('wb') as stderr:
            code=subprocess.run(['gpgv','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg','--status-fd','1','--output',str(clear),str(release)],stdout=stdout,stderr=stderr,timeout=60).returncode
        require(code==0 and '[GNUPG:] VALIDSIG ' in status.read_text(),'Independent standard runner Ubuntu keyring must validate original snapshot signature')
        text=clear.read_text();require('Suite: '+suite+'\n' in text,'Original signed snapshot suite differs');hashes=release_hashes(text)
        for index in sorted(metadata.glob(PREFIX+suite+'_*_binary-amd64_Packages.lz4')):
            component=index.name[len(PREFIX+suite+'_'):].split('_binary-amd64_',1)[0];relative=component+'/binary-amd64/Packages';require(relative in hashes,'Every original Packages index must be covered by signed Release')
            unpacked=output/(suite+'-'+component+'.Packages');require(not unpacked.exists(),'Fresh independently decoded package index required')
            with unpacked.open('wb') as stream:code=subprocess.run(['/usr/lib/apt/apt-helper','cat-file',str(index)],stdout=stream,stderr=subprocess.PIPE,timeout=120).returncode
            require(code==0 and (sha(unpacked),unpacked.stat().st_size)==hashes[relative],'Independently decoded complete Packages bytes must equal signed Release SHA256/size')
            fields={}
            with unpacked.open() as stream:
                for line in stream:
                    if line=='\n':planned_package(fields,wanted,pins,found);fields={}
                    elif not line.startswith((' ','\t')):
                        key,separator,value=line.rstrip('\n').partition(':');require(separator and key not in fields,'Unique package record fields required');fields[key]=value.lstrip(' ')
                if fields:planned_package(fields,wanted,pins,found)
            records.append(dict(suite=suite,component=component,retained_index_sha256=sha(index),signed_uncompressed_sha256=hashes[relative][0],signed_uncompressed_bytes=hashes[relative][1]))
            unpacked.unlink() # only independently derived duplicate; all retained originals stay untouched
    atomic_json(output/'signed-index-comparison.json',dict(expected_original_blob_paths=sorted(wanted),matched_signed_blob_paths=sorted(found),missing_signed_blob_paths=sorted(set(wanted)-found),actual_snapshot_index_records=records,original_retained_URI_plan_rewritten=False))
    require(set(wanted)==found and len(records)==13,'Every one of402 original planned blobs and all13 snapshot indexes must match signed metadata')
    return dict(all_four_original_snapshot_signatures_independently_verified=True,all_thirteen_original_snapshot_indexes_SHA256_and_sizes_verified=True,original_planned_blobs_matched_to_signed_indexes=len(found),index_records=records,runner_archive_keyring_sha256=sha('/usr/share/keyrings/ubuntu-archive-keyring.gpg'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();require(not a.output.exists(),'Fresh independent provisioning receipt required')
    api=load(a.inputs/'api.json');bind_api(api);restored={}
    for kind,(_,size,digest,_) in PINNED.items():
        archive=a.inputs/(kind+'.zip');require(archive.stat().st_size==size and sha(archive)==digest,'Actual published provisioning ZIP differs: '+kind);restored[kind]=restore_zip(ROOT,archive)
    proof=load(ROOT/'out/original-package-pool-proof.json');require(proof['source']==SOURCE and proof['actual_downloaded_blob_count']==402,'Exact source-bound actual original provisioning proof required')
    controls=load(ROOT/'out/original-pool-controls.json');require(controls['status']=='passed' and controls['tests_run']==419 and all(controls[k]==0 for k in ('skipped','failures','errors')) and controls['producer_commit']==SOURCE and controls['sources_match_producer'] is True,'All419 original controls must actually pass without omissions')
    prefix='/home/runner/work/orbiter-cross-platform/orbiter-cross-platform/'
    for name,digest in controls['sources_sha256'].items():
        require(name.startswith(prefix),'Exact original standard runner source root required');relative=name[len(prefix):];body=subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':'+relative]);require(hashlib.sha256(body).hexdigest()==digest and sha(ROOT/relative)==digest,'Original provisioning inspector/control source changed')
    retained=load(ROOT/'out/original-package-pool-retention.json');require(retained['source']==SOURCE and retained['run_id']==RUN and retained['qualification_granted'] is False,'Exact source-bound published raw provisioning retention required')
    for key in ('id','name','size_in_bytes','digest','workflow_run'):require(retained['artifact'][key]==api['artifacts']['raw'][key],'Actual raw artifact differs from published receipt')
    replay=original.inspect('Debug-sse2');replay['source']=SOURCE;require(replay==proof,'Every original provisioning audit field must reproduce exactly; fresh auditor source recorded separately')
    folder=ROOT/'out/original-package-official-pool/Debug-sse2';signed=inspect_signed_indexes(folder,proof['actual_original_blob_plan'],a.inputs/'signature-audit')
    atomic_json(a.output,dict(protocol='phase6-independently-replayed-published-original-package-pool-v1',status='independently-verified-original488-package-provisioning-only',original_source=SOURCE,original_run=RUN,auditor_source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),published_artifacts=api['artifacts'],restored_archives=restored,original_proof_sha256=sha(ROOT/'out/original-package-pool-proof.json'),original_preflight_reproduced_exactly=True,original_provisioning_files_verified=len(proof['provisioning_files_sha256']),original_controls_passed=419,signed_metadata=signed,new_simulator_processes=0,complete_class_eligibility_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False))


if __name__=='__main__':main()
