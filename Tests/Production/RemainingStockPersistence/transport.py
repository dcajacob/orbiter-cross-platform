"""Bind decoded Windows observations to the retained, hashed artifact ZIP bytes."""
import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import zipfile

from observations import require,sha

PROFILES={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')}


def safe(name):
    path=PurePosixPath(name)
    require(name and not path.is_absolute() and '..' not in path.parts and ':' not in name and
            '\\' not in name and str(path)==name.rstrip('/'),'Unsafe artifact member path: '+name)
    return path


def inspect_archive(archive,decoded,checksum,size):
    require(archive.is_file() and archive.stat().st_size==size and sha(archive)==checksum,
            'Exact retained artifact ZIP bytes/hash/size differ')
    members={};seen=set()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            path=safe(member.filename);folded=str(path).casefold()
            require(folded not in seen and not stat.S_ISLNK(member.external_attr>>16),
                    'Duplicate, case-colliding or symlink artifact member')
            seen.add(folded)
            if member.is_dir():continue
            actual=decoded/str(path)
            require(actual.is_file() and not actual.is_symlink() and
                    sha(actual)==hashlib.sha256(source.read(member)).hexdigest(),
                    'Decoded Windows observation differs from retained ZIP member: '+str(path))
            members[str(path)]=sha(actual)
    require(members,'Empty Windows persistence artifact')
    require({p.relative_to(decoded).as_posix() for p in decoded.rglob('*') if p.is_file()}==set(members),
            'Unmanifested decoded Windows observation file')
    require(sha(archive)==checksum,'Retained Windows ZIP changed during inspection')
    return members


def inspect_matrix(manifest,archive_root,decoded,producer):
    require(manifest['status']=='passed' and manifest['source_commit']==producer and
            re.fullmatch('[0-9a-f]{40}',producer) and len(manifest['artifacts'])==4 and
            {v['profile'] for v in manifest['artifacts']}==PROFILES and set(decoded)==PROFILES,
            'Complete matching four-profile Windows artifact transport required')
    result={}
    for item in manifest['artifacts']:
        profile=item['profile']
        require(item['name']=='matched-clock-remaining-stock-v2-'+profile,
                'Full persistence requires the complete-scene artifact, not a selected diagnostic')
        archive=archive_root/str(safe(item['path']))
        members=inspect_archive(archive,decoded[profile],item['sha256'],item['bytes'])
        result[profile]=dict(archive=str(archive),archive_sha256=item['sha256'],archive_bytes=item['bytes'],
                             decoded_members_sha256=members)
    return result


def parent_guards(decoded,report,parent):
    """Resolve only exact retained parent/build suffixes of Windows execution paths."""
    prefix='remaining-stock-repaired/'
    expected={prefix+'capture.json':sha(decoded/prefix/'capture.json'),
              'remaining-stock-repaired-build/build.json':sha(decoded/'remaining-stock-repaired-build/build.json')}
    for identity,case in parent['cases'].items():
        require(re.fullmatch('remaining_stock_[0-9]{3}',identity) and len(case['runs'])==2,
                'Complete actual Windows parent repetitions required')
        for repeat,run in enumerate(case['runs'],1):
            directory=prefix+identity+'-'+str(repeat)+'/'
            expected.update({directory+str(safe(n)):v for n,v in run['files_sha256'].items()})
            saved=directory+'Scenarios/(Current state).scn'
            expected[saved]=sha(decoded/saved)
    actual={};roots=set()
    for name,value in report['guarded_parent_files_sha256'].items():
        path=PureWindowsPath(name)
        require(path.is_absolute() and '..' not in path.parts,'Unsafe original Windows guarded path')
        anchors=[i for i,n in enumerate(path.parts) if n in ('remaining-stock-repaired','remaining-stock-repaired-build')]
        require(len(anchors)==1,'Windows parent guard has missing or ambiguous retained root')
        index=anchors[0];relative='/'.join(path.parts[index:]);roots.add(tuple(path.parts[:index]))
        require(relative in expected and relative not in actual and value==expected[relative],
                'Windows parent guard omitted, substituted or changed actual evidence')
        actual[relative]=value
    require(actual==expected and len(roots)==1,'Complete Windows parent guard closure from one owning output root required')
    require(all(sha(decoded/name)==value for name,value in expected.items()),'Actual retained Windows parent bytes changed')
    return expected
