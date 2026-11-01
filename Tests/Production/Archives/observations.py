#!/usr/bin/env python3
"""Exact archive observations and independent fixed-width/zlib checks.

Capture refuses changed production source and cannot refresh accepted evidence.
No decoded texture/elevation payloads are retained in Git or the reports.
"""
import argparse
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ABSENT = 0xffffffff
LAYERS = ('Surf', 'Mask', 'Elev', 'Elev_mod', 'Label', 'Cloud')


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def stored_zlib(payload):
    """Deterministic RFC 1950/1951 stored blocks, independent of zlib version."""
    blocks = [payload[i:i+65535] for i in range(0,len(payload),65535)] or [b'']
    return (b'\x78\x01'+b''.join(bytes([int(i==len(blocks)-1)])+
        struct.pack('<HH',len(block),65535-len(block))+block for i,block in enumerate(blocks))+
        struct.pack('>I',zlib.adler32(payload)&ABSENT))


def fixtures(directory):
    """Write explicit disk records, including nonzero ignored node padding."""
    result = []
    cases = [('records', [b'DDS '+bytes(range(256))*32, b'BM'+b'\xff\x00'*1024,
        bytes(range(32)), b'', b'ELEV'+b'\x80\x00'*67129,
        b'northwest', b'northeast', b'southwest', b'southeast'], 0),
        ('sparse64', [b'offset exceeds four GiB\x00\xff'], (1<<32)+29)]
    for name, payloads, base in cases:
        path = directory/name/'Archive'/'Surf.tree'
        path.parent.mkdir(parents=True, exist_ok=True)
        blocks = [stored_zlib(value) if value else b'' for value in payloads]
        positions, offset = [], base
        for block in blocks:
            positions.append(offset)
            offset += len(block)
        count = len(blocks)
        data_offset = 48+32*count
        roots = [0, 1, 2, 3, 4] if count>1 else [ABSENT, ABSENT, ABSENT, 0, ABSENT]
        header = struct.pack('<4sIIIqIIIIII', b'TX\x01\0', 48, 1, data_offset, offset, count, *roots)
        nodes = b''.join(struct.pack('<qIIIII', pos, len(payloads[i]),
            *([5,6,7,8] if i==3 else [ABSENT]*4))+b'\xac\xbd\xce\xdf'
            for i, pos in enumerate(positions))
        with path.open('wb') as stream:
            if base and os.name=='nt':
                # Avoid allocating four GiB on NTFS. This is test provisioning,
                # not an engine compatibility layer.
                import msvcrt
                from ctypes import wintypes
                call = ctypes.WinDLL('kernel32', use_last_error=True).DeviceIoControl
                call.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
                call.restype = wintypes.BOOL
                returned = wintypes.DWORD()
                require(call(msvcrt.get_osfhandle(stream.fileno()), 0x900c4, None, 0, None, 0,
                             ctypes.byref(returned), None), 'Windows test volume does not support sparse files')
            stream.write(header+nodes)
            stream.seek(data_offset+base)
            for block in blocks:
                stream.write(block)
        result.append(('fixture/'+name, path, 0, dict(bytes=path.stat().st_size,
            records_sha256=sha(header+nodes), payloads_sha256=[sha(value) for value in payloads])))
    return result


def expected(path):
    """Independent decoder, with no ctypes or invocation of Orbiter code."""
    with path.open('rb') as stream:
        header = struct.unpack('<4sIIIqIIIIII', stream.read(48))
        magic, size, flags, start, length, count, *roots = header
        require(magic==b'TX\x01\0' and size==48 and flags in (0,1), 'unexpected archive header')
        require(0<count<1_000_000 and start>=48+32*count and path.stat().st_size>=start+length,
                'invalid original fixture extent')
        nodes = [struct.unpack('<qIIIII4x', stream.read(32)) for _ in range(count)]
        canonical = b''.join(struct.pack('<qIIIII', *node) for node in nodes)
        queries = [(1,0,0),(2,0,0),(3,0,0),(4,0,0),(4,0,1)]
        for level in range(5,13):
            nlat = 1<<(level-4)
            queries.extend((level,lat,lng) for lat in (0,nlat-1) for lng in (0,2*nlat-1))
        queries.extend((0,index,0) for index in (0,count//2,count-1))

        def index(level, lat, lng):
            if level<=4:
                return roots[level-1] if level<4 else roots[3+lng]
            parent = index(level-1, lat//2, lng//2)
            return ABSENT if parent==ABSENT else nodes[parent][2+((lat&1)<<1)+(lng&1)]

        output = io.BytesIO()
        output.write(b'OTREE1\r\n'+struct.pack('<I',count)+canonical+struct.pack('<I',len(queries)))
        observations = []
        for level,lat,lng in queries:
            idx = index(level,lat,lng) if level else lat
            compressed = inflated = 0
            payload = b''
            if idx!=ABSENT:
                position, inflated, *_ = nodes[idx]
                compressed = (nodes[idx+1][0] if idx+1<count else length)-position
                require(0<=position<=length and 0<=compressed<=0xffffffff, 'invalid node extent')
                if inflated:
                    stream.seek(start+position)
                    payload = zlib.decompress(stream.read(compressed))
                    require(len(payload)==inflated, 'independent inflated size differs')
            output.write(struct.pack('<IIIIIII',level,lat,lng,idx,compressed,inflated,len(payload))+payload)
            observations.append(dict(query=[level,lat,lng], index=idx, compressed=compressed,
                inflated=inflated, decoded=len(payload), payload_sha256=sha(payload)))
        raw = output.getvalue()
        return raw, dict(nodes=count, toc_sha256=sha(canonical), queries=observations, observation_sha256=sha(raw))


def protocol(original=False):
    lock = json.loads((HERE/'protocol.json').read_text())
    require(lock['automatic_refresh'] is False and lock['comparison']=='exact integer identities and decoded bytes',
            'archive acceptance policy changed')
    for name, checksum in lock['inputs_sha256_lf'].items():
        require(sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==checksum, 'archive input changed: '+name)
    if original:
        for name, checksum in lock['production_source_sha256_lf'].items():
            require(sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==checksum,
                    'production archive changed before Windows capture: '+name)
    return lock


def observe(executable, data, output):
    stock_lock = json.loads((ROOT/'Tests/Production/standard-planets.lock.json').read_text())
    paths = fixtures(output/'fixtures')
    for name, info in stock_lock['data_files'].items():
        path = data/name
        require(path.stat().st_size==info['bytes'] and file_sha(path)==info['sha256'], 'archive input differs: '+name)
        paths.append((name,path,LAYERS.index(path.stem),info))
    reports = {}
    for ordinal, (name,path,layer,inputs) in enumerate(paths):
        golden, observation = expected(path)
        for repeat in (1,2):
            target = output/f'observation-{ordinal}-{repeat}.bin'
            result = subprocess.run([str(executable), str(path.parent.parent), str(layer), str(target)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            (output/f'run-{ordinal}-{repeat}.log').write_bytes(result.stdout)
            require(result.returncode==0, 'production archive observer failed: '+name)
            require(target.read_bytes()==golden, 'production decode/index/TOC differs from explicit disk interpretation: '+name)
            target.unlink()  # Do not retain decoded visual assets in reference Git history.
        reports[name] = dict(inputs=inputs, **observation)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--configuration', choices=('Debug','Release'), required=True)
    args = parser.parse_args()
    lock = protocol(original=True)
    require(platform.system()=='Windows', 'pre-extraction archive capture requires native Windows')
    output = args.output.resolve()
    require(not output.exists() and output!=HERE/'Reference' and HERE/'Reference' not in output.parents,
            'capture requires a new directory outside accepted evidence')
    executable = args.executable.resolve(strict=True)
    output.mkdir(parents=True)
    try:
        observations = observe(executable,args.data.resolve(),output)
    finally:
        import shutil
        shutil.rmtree(output/'fixtures',ignore_errors=True)
    report = dict(status='passed',automatic_refresh=False,configuration=args.configuration,
        source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        host=platform.platform(),executable_sha256=file_sha(executable),
        protocol_sha256=sha((HERE/'protocol.json').read_bytes()), protocol=lock, observations=observations,
        scope='Actual original ZTreeMgr, 28 publisher archives and explicit/sparse fixtures; not native world initialization')
    (output/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Verified two exact production decodes per archive:',len(observations),'archives; native Windows',args.configuration)


if __name__=='__main__':
    main()
