#!/usr/bin/env python3
"""Preserve the four audited original ZIPs as verified, content-pinned release assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from frozen_original import ArtifactRedirect, digest, require

HERE = Path(__file__).resolve().parent
TAG = 'phase6-shuttle-a-controls-original-v1'
TITLE = 'Phase 6 Shuttle-A original controls observations v1'
BODY = ('preserved-original-windows: four audited Debug/Release automatic/SSE2 profiles. '
        '64 complete-scene keyboard/persistence sessions and 3,648 presentations. '
        'Application/SDK/client source f725194209634f7fd5d1d44d426cfa9b5e303e37; '
        'observer producer 8c5b87fb3afbd8bdcec8097eb4dbd97d9c7f42ef. '
        'ZIP sizes and SHA-256 identities are pinned in '
        'Tests/Production/ShuttleA/Controls/observations.lock.json. '
        'These original observations do not declare overall native or Phase 6 acceptance.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cache', 'audit', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    require(not args.output.exists(), 'Preservation output already exists')
    pins = json.loads((HERE/'observations.lock.json').read_text())
    audit = json.loads(args.audit.read_text())
    require(pins['automatic_refresh'] is False and pins['repository'] == 'dcajacob/orbiter-cross-platform' and
        audit['status'] == 'passed' and audit['producer_commit'] == pins['producer_commit'] and
        audit['processes'] == 64 and audit['scene_presents'] == 3648 and len(audit['profiles']) == 4,
        'Preservation requires all four audited original profiles')
    files = {item['name']+'.zip': args.cache/(item['name']+'.zip') for item in pins['artifacts']}
    expected = {item['name']+'.zip': item for item in pins['artifacts']}
    require(len(files) == 4, 'Original asset matrix incomplete')
    for name, path in files.items():
        require(path.stat().st_size == expected[name]['bytes'] and digest(path) == expected[name]['sha256'],
                'Original cached archive differs: '+name)
    record = dict(status='validated-local', tag=TAG, source_commit=pins['producer_commit'],
                  files={name: dict(bytes=p.stat().st_size, sha256=digest(p)) for name, p in files.items()})
    if args.publish:
        token = os.environ.get('GITHUB_TOKEN')
        require(bool(token), 'Publishing requires the workflow-scoped GITHUB_TOKEN')
        repo = pins['repository']
        opener = urllib.request.build_opener(ArtifactRedirect())
        def request(path, method='GET', payload=None, upload=False):
            host = 'uploads.github.com' if upload else 'api.github.com'
            headers = {'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json',
                       'X-GitHub-Api-Version': '2026-03-10'}
            if payload is not None:
                headers['Content-Type'] = 'application/zip' if upload else 'application/json'
                payload = payload if upload else json.dumps(payload).encode()
            with opener.open(urllib.request.Request('https://'+host+'/repos/'+repo+path,
                             data=payload, headers=headers, method=method), timeout=180) as response:
                return json.load(response)
        def check_tag():
            ref = request('/git/ref/tags/'+TAG)['object']
            if ref['type'] == 'tag':
                ref = request('/git/tags/'+ref['sha'])['object']
            require(ref['type'] == 'commit' and ref['sha'] == pins['producer_commit'],
                    'Preservation tag differs from the audited producer')
        check_tag()
        # The tag is created by the authorized Git push, before this workflow.
        # Never create or move a tag, overwrite an asset, or replace a release.
        releases = request('/releases?per_page=100')
        matches = [r for r in releases if r['tag_name'] == TAG]
        require(len(matches) <= 1, 'Ambiguous preservation release')
        release = matches[0] if matches else request('/releases', 'POST',
            dict(tag_name=TAG, name=TITLE, body=BODY, draft=True, prerelease=True))
        require(release['name'] == TITLE and release['prerelease'] and
                'preserved-original-windows:' in release['body'], 'Conflicting preservation release')
        release_id = int(release['id'])
        assets = request('/releases/'+str(release_id)+'/assets?per_page=100')
        require({a['name'] for a in assets} <= set(files), 'Unexpected existing preservation assets')
        by_name = {a['name']: a for a in assets}
        require(len(by_name) == len(assets), 'Duplicate preservation assets')
        verified = {}
        for name, path in files.items():
            asset = by_name.get(name)
            if asset is None:
                asset = request('/releases/'+str(release_id)+'/assets?name='+urllib.parse.quote(name),
                                'POST', path.read_bytes(), upload=True)
            require(asset['size'] == expected[name]['bytes'] and asset['state'] == 'uploaded' and
                    asset['digest'] == 'sha256:'+expected[name]['sha256'], 'Release asset identity differs: '+name)
            headers = {'Authorization': 'Bearer '+token, 'Accept': 'application/octet-stream',
                       'X-GitHub-Api-Version': '2026-03-10'}
            checksum = hashlib.sha256()
            count = 0
            with opener.open(urllib.request.Request('https://api.github.com/repos/'+repo+
                '/releases/assets/'+str(int(asset['id'])), headers=headers), timeout=180) as response:
                while chunk := response.read(1024*1024):
                    checksum.update(chunk)
                    count += len(chunk)
            require(count == expected[name]['bytes'] and checksum.hexdigest() == expected[name]['sha256'],
                    'Downloaded release asset bytes differ: '+name)
            verified[name] = dict(id=asset['id'], bytes=count, sha256=checksum.hexdigest())
        check_tag()
        if release['draft']:
            release = request('/releases/'+str(release_id), 'PATCH', dict(draft=False, prerelease=True))
        require(not release['draft'] and release['prerelease'], 'Preservation release was not published')
        record.update(status='published-and-byte-verified', release=release['html_url'], assets=verified)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2)+'\n')
    print(record['status'], TAG)


if __name__ == '__main__':
    main()
