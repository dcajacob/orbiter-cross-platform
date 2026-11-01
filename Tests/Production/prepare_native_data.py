#!/usr/bin/env python3
"""Provision original, hash-locked data from its audited immutable mirror.

This development provisioner is not the release asset installer. The original
stock profile is unchanged; only its explicitly excluded restricted font is
omitted, and each selected file must retain the original hash and length.
"""
import argparse
import json
from pathlib import Path,PurePosixPath
import shutil
import urllib.request
import zipfile
from mesa_runtime import digest,require

HERE=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--group',choices=('all','celestial'),default='all')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    storage=json.loads((HERE/'input-storage.lock.json').read_text())
    stock=json.loads((HERE/'stock-data.lock.json').read_text())
    package=storage['manifest']['packages']['Orbiter-x64.zip'];mirror=package['mirrored_archive']
    require(package['sha256']==stock['sha256'] and package['bytes']==stock['bytes'],'storage/profile identity differs')
    excluded=set(package['excluded'])
    require(excluded=={'Fonts/architext.regular.ttf'},'unreviewed data exclusion')
    selected={name:record for name,record in stock['data_files'].items() if name not in excluded and
        (args.group=='all' or name.startswith(('Kernels/','GravityModels/')))}
    require({'Kernels/orbiter.bsp','Kernels/naif0012.tls','Kernels/pck00011.tpc'}<=set(selected),'SPICE kernel profile is incomplete')
    if not args.verify_only:
        archive=args.archive
        if not archive.is_file():
            archive.parent.mkdir(parents=True,exist_ok=True);temporary=archive.with_suffix('.partial')
            url='https://github.com/'+storage['repository']+'/releases/download/'+storage['tag']+'/'+mirror['name']
            with urllib.request.urlopen(url,timeout=180) as source,temporary.open('wb') as output:
                shutil.copyfileobj(source,output)
            require(temporary.stat().st_size==mirror['bytes'] and digest(temporary)==mirror['sha256'],'immutable mirrored package differs; do not refresh the profile')
            temporary.replace(archive)
        require(archive.stat().st_size==mirror['bytes'] and digest(archive)==mirror['sha256'],'mirrored package checksum differs')
        with zipfile.ZipFile(archive) as source:
            for name in selected:
                relative=PurePosixPath(name)
                require(not relative.is_absolute() and '..' not in relative.parts and chr(92) not in name,'invalid locked data path')
                target=args.destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                with source.open(name) as incoming,target.open('wb') as output:shutil.copyfileobj(incoming,output)
            for name in source.namelist():
                if name in ('LICENSE','readme.txt') or name.startswith('Licenses/'):
                    relative=PurePosixPath(name)
                    require(not relative.is_absolute() and '..' not in relative.parts and chr(92) not in name,'invalid notice path')
                    target=args.destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                    with source.open(name) as incoming,target.open('wb') as output:shutil.copyfileobj(incoming,output)
    for name,record in selected.items():
        path=args.destination/name
        require(path.is_file() and path.stat().st_size==record['bytes'] and digest(path)==record['sha256'],
                'missing/incompatible original data: '+name)
    print('Verified',len(selected),'original data files from immutable',storage['tag'],'profile',args.group)

if __name__=='__main__':main()
