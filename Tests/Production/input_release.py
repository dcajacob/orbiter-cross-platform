#!/usr/bin/env python3
"""Prepare unmodified, digest-locked inputs and notices for versioned storage.

The 2016 ZIP exceeds GitHub's per-asset limit. Its byte ranges are stored as
parts; concatenating them recovers the exact original publisher archive.
The current package is filtered to the consumed data with permitted redistribution;
its restricted Architext font and executables are not mirrored.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

from mesa_runtime import digest, require

HERE=Path(__file__).resolve().parent
CHUNK=1500000000


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.cache.mkdir(parents=True,exist_ok=True);args.output.mkdir(parents=True,exist_ok=False)
    result=dict(schema=1,tag='production-inputs-v1',scope='Windows production references and renderer integration',packages={})
    for lock_name,archive_name in (('stock-data.lock.json','Orbiter-x64.zip'),('standard-planets.lock.json','Orbiter2016.zip')):
        lock=json.loads((HERE/lock_name).read_text());archive=args.cache/archive_name
        if not archive.exists():
            partial=archive.with_suffix('.partial')
            with urllib.request.urlopen(lock['url'],timeout=180) as source,partial.open('wb') as target:shutil.copyfileobj(source,target)
            require(partial.stat().st_size==lock['bytes'] and digest(partial)==lock['sha256'],'publisher archive differs from lock')
            partial.replace(archive)
        require(archive.stat().st_size==lock['bytes'] and digest(archive)==lock['sha256'],'cached package differs from lock')
        record=dict(source=lock['url'],sha256=lock['sha256'],bytes=lock['bytes'],parts=[],notices=[])
        if archive_name=='Orbiter-x64.zip':
            # The upstream package contains Architext under a separate FFC license.
            # Do not mirror that package or publish the font independently.
            name='production-stock-data-v1.zip'
            with zipfile.ZipFile(archive) as source,zipfile.ZipFile(args.output/name,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as target:
                for member in lock['data_files']:
                    if member=='Fonts/architext.regular.ttf':continue
                    data=source.read(member)
                    require(hashlib.sha256(data).hexdigest()==lock['data_files'][member]['sha256'],'data member differs from profile')
                    info=zipfile.ZipInfo(member,(2026,10,31,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    target.writestr(info,data)
                for member in ('LICENSE','readme.txt'):
                    info=zipfile.ZipInfo(member,(2026,10,31,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    target.writestr(info,source.read(member))
                for notice in ('Lekton - SIL License.txt','License-FA.txt'):
                    info=zipfile.ZipInfo('Licenses/'+notice,(2026,10,31,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    target.writestr(info,(HERE.parents[1]/'Extern/imgui'/notice).read_bytes())
                for notice in ('Cousine-LICENSE.txt','Roboto-LICENSE.txt'):
                    info=zipfile.ZipInfo('Licenses/'+notice,(2026,10,31,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    target.writestr(info,(HERE/'Licenses'/notice).read_bytes())
            record.update(distribution='filtered data only; no executables or Architext font',excluded=['Fonts/architext.regular.ttf'],
                          mirrored_archive=dict(name=name,bytes=(args.output/name).stat().st_size,sha256=digest(args.output/name)))
        elif archive.stat().st_size<2**31:
            shutil.copy2(archive,args.output/archive_name)
            record['parts'].append(dict(name=archive_name,bytes=lock['bytes'],sha256=lock['sha256']))
        else:
            with archive.open('rb') as source:
                part=0
                while source.tell()<lock['bytes']:
                    part+=1;name=f'{archive_name}.part{part:02d}'
                    with (args.output/name).open('wb') as target:
                        remaining=CHUNK
                        while remaining:
                            data=source.read(min(8*1024*1024,remaining))
                            if not data:break
                            target.write(data);remaining-=len(data)
                    p=args.output/name;record['parts'].append(dict(name=name,bytes=p.stat().st_size,sha256=digest(p)))
            combined=hashlib.sha256()
            for p in record['parts']:
                with (args.output/p['name']).open('rb') as source:
                    for data in iter(lambda:source.read(8*1024*1024),b''):combined.update(data)
            require(combined.hexdigest()==lock['sha256'],'split archive does not reconstruct original bytes')
        with zipfile.ZipFile(archive) as source:
            names=['readme.txt']+(['Doc/Orbiter.pdf'] if archive_name=='Orbiter2016.zip' else ['LICENSE'])
            for name in names:
                p=args.output/(archive_name+'-'+Path(name).name);p.write_bytes(source.read(name))
                record['notices'].append(dict(name=p.name,sha256=digest(p),archive_member=name))
        result['packages'][archive_name]=record
        shutil.copy2(HERE/lock_name,args.output/lock_name)
    (args.output/'inputs.json').write_text(json.dumps(result,indent=2)+'\n')
    shutil.copy2(HERE/'Licenses/INPUTS.md',args.output/'INPUTS.md')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
