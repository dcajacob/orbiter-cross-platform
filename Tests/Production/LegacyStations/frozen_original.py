#!/usr/bin/env python3
"""Stage and audit pinned additional Windows observations without refreshing them."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

from recording_inputs import CASE_FILE,LOCK_FILE

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ArtifactRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,*args,**kwargs):
        result=super().redirect_request(request,*args,**kwargs)
        if result and urllib.parse.urlparse(result.full_url).hostname!='api.github.com':
            result.remove_header('Authorization')
        return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','output','audit'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--offline',action='store_true')
    a=p.parse_args()
    for name in ('cache','output','audit'):setattr(a,name,getattr(a,name).resolve())
    require(not a.output.exists() and not a.audit.exists(),'Original observation output exists')
    require(LOCK_FILE.is_file(),'Corrected original v2 observations have not been independently pinned')
    pins=json.loads(LOCK_FILE.read_text())
    require(pins['status']=='audited-original-observations' and pins['automatic_refresh'] is False and pins['protocol']==2,
            'Original legacy station observations are not pinned')
    require(hashlib.sha256(CASE_FILE.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==
            pins['cases_sha256_lf'],'Original legacy station case matrix changed')
    require(digest(HERE/'audit_original.py')==pins['audit_verifier_sha256'],'Pinned original v2 auditor changed')
    expected={'original-legacy-stations-v2-'+c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')}
    require({v['name'] for v in pins['artifacts']}==expected and len(pins['artifacts'])==4,
            'Pinned original profile matrix is incomplete')
    a.cache.mkdir(parents=True,exist_ok=True);a.output.mkdir(parents=True)
    records=[]
    for item in pins['artifacts']:
        archive=a.cache/(item['name']+'.zip')
        if not archive.exists():
            require(not a.offline,'Pinned original archive unavailable offline: '+item['name'])
            release=pins.get('durable_release')
            if release:
                require(release['tag']=='phase6-legacy-stations-original-v2','Unexpected original release tag')
                url='https://github.com/'+pins['repository']+'/releases/download/'+release['tag']+'/'+urllib.parse.quote(item['name']+'.zip')
                request=urllib.request.Request(url)
            else:
                token=os.environ.get('GITHUB_TOKEN')
                require(bool(token),'GITHUB_TOKEN is required to read pinned Actions artifacts')
                url='https://api.github.com/repos/'+pins['repository']+'/actions/artifacts/'+str(item['id'])+'/zip'
                request=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,
                    'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
            temporary=archive.with_suffix('.partial')
            try:
                with urllib.request.build_opener(ArtifactRedirect()).open(request,timeout=180) as incoming,temporary.open('xb') as target:
                    while chunk:=incoming.read(1024*1024):target.write(chunk)
                require(temporary.stat().st_size==item['bytes'] and digest(temporary)==item['sha256'],
                        'Downloaded original observation archive differs: '+item['name'])
                temporary.rename(archive)
            except Exception:
                raise ValueError('Unable to obtain the pinned archive: '+item['name']) from None
            finally:temporary.unlink(missing_ok=True)
        require(archive.stat().st_size==item['bytes'] and digest(archive)==item['sha256'],
                'Cached original observation archive differs: '+item['name'])
        folder=a.output/item['name'].removeprefix('original-legacy-stations-v2-');folder.mkdir()
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                path=PurePosixPath(member.filename)
                require(not path.is_absolute() and '..' not in path.parts and
                        '\\' not in member.filename and ':' not in member.filename and
                        not stat.S_ISLNK(member.external_attr>>16),'Unsafe observation archive member')
                if member.is_dir():continue
                target=folder.joinpath(*path.parts)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as output:output.write(source.read(member))
        records.append(dict(item,path=str(archive.relative_to(ROOT)),output=str(folder.relative_to(ROOT))))
    manifest=a.output/'downloads.json'
    manifest.write_text(json.dumps(dict(status='passed',run_id=pins['run_id'],
        source_commit=pins['producer_commit'],artifacts=records),indent=2)+'\n')
    subprocess.run([sys.executable,'-B',str(HERE/'audit_original.py'),
        '--artifacts',str(a.output),'--download-manifest',str(manifest),
        '--producer-commit',pins['producer_commit'],'--metadata-lock',str(LOCK_FILE),'--output',str(a.audit)],check=True)


if __name__=='__main__':main()
