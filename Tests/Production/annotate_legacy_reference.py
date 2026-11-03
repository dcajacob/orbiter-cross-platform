#!/usr/bin/env python3
"""Publish the verified v1 playback limitation without changing reference assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

HERE=Path(__file__).resolve().parent
TAG='phase6-legacy-stations-original-v1'
PRODUCER='e81279b9ca108b27b56925bfe034141416f20f1d'
NOTICE=('**Version 1 playback limitation:** the rescue fixture used `Behavior.scn` and omitted '
    'its named flight recordings. The preserved application silently fell back from playback. '
    'The three non-playback cases retain their original observations; the rescue case is '
    'unqualified for complete stock playback. All version 1 archives, asset identities and '
    'the observer tag remain unchanged. Corrected observations use a separate version 2 protocol. '
    'This release does not establish native parity or Phase 6 acceptance.')


def require(value,message):
    if not value:raise ValueError(message)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--publish',action='store_true')
    a=p.parse_args();require(not a.output.exists(),'Reference annotation output exists')
    pins=json.loads((HERE/'LegacyStations/observations.lock.json').read_text())
    require(pins['status']=='limited-original-observations-playback-unqualified' and
        pins['automatic_refresh'] is False and pins['producer_commit']==PRODUCER and
        pins['repository']=='dcajacob/orbiter-cross-platform' and
        pins['durable_release']['tag']==TAG,'Original v1 limitation is not independently recorded')
    token=os.environ.get('GITHUB_TOKEN')
    require(not a.publish or token,'Publishing the limitation requires the workflow-scoped GITHUB_TOKEN')
    def request(path,body=None):
        headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
        if token:headers['Authorization']='Bearer '+token
        if body is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request('https://api.github.com/repos/'+pins['repository']+path,
            data=None if body is None else json.dumps(body).encode(),headers=headers,
            method='GET' if body is None else 'PATCH')
        with urllib.request.urlopen(req,timeout=60) as incoming:return json.load(incoming)
    def verify(release):
        ref=request('/git/ref/tags/'+TAG)['object']
        if ref['type']=='tag':ref=request('/git/tags/'+ref['sha'])['object']
        require(ref['type']=='commit' and ref['sha']==PRODUCER,'Original v1 tag differs')
        require(release['id']==433308879 and release['tag_name']==TAG and
            not release['draft'] and release['prerelease'],'Original v1 release identity differs')
        expected={item['name']+'.zip':item for item in pins['artifacts']}
        assets=request('/releases/'+str(release['id'])+'/assets?per_page=100')
        require(len(assets)==4 and {item['name'] for item in assets}==set(expected),'Original v1 assets differ')
        for asset in assets:
            item=expected[asset['name']]
            require(asset['size']==item['bytes'] and asset['digest']=='sha256:'+item['sha256'] and
                asset['state']=='uploaded','Original v1 asset identity differs')
        return {item['name']:dict(id=item['id'],bytes=item['size'],digest=item['digest']) for item in assets}
    release=request('/releases/tags/'+TAG);before=verify(release)
    old=release['body'];body=old if NOTICE in old else NOTICE+'\n\n'+old
    if a.publish:
        request('/releases/'+str(release['id']),dict(body=body))
        actual=request('/releases/tags/'+TAG)
        require(actual['body']==body and verify(actual)==before,'Published limitation or preserved assets differ')
    record=dict(status='published-and-verified' if a.publish else 'validated-reviewable',
        release=release['html_url'],tag=TAG,producer_commit=PRODUCER,assets=before,
        original_body_sha256=hashlib.sha256(old.encode()).hexdigest(),
        proposed_body_sha256=hashlib.sha256(body.encode()).hexdigest(),body=body,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),phase6_complete=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'],TAG)


if __name__=='__main__':main()
