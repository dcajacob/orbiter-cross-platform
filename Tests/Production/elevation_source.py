#!/usr/bin/env python3
"""Conserve the original terrain formulas, with bounded edge stencils."""
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='c1fb3fadadbe57a241961e002914c4749396197e'
def original(name):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).replace(b'\r\n',b'\n')
def current(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n')
def types(source):
    for before,after in [(b'std::int16_t',b'INT16'),(b'std::uint8_t',b'UINT8'),(b'unsigned char',b'BYTE'),
        (b'orbiter::production::UInt32',b'DWORD')]:source=source.replace(before,after)
    return source
def verify():
    old=original('Src/Orbiter/elevmgr.cpp');source=types(current('Src/Orbiter/elevmgr.cpp'))
    a=old.index(b'ElevationManager::~ElevationManager');b=old.index(b'bool ElevationManager::HasElevationTile(')
    if source[source.index(b'ElevationManager::~ElevationManager'):source.index(b'// Tile quadrants and mask bits')].strip()!=old[a:b].strip():
        raise ValueError('production terrain destruction/coordinate indexing changed')
    source=source[source.index(b'// Tile quadrants and mask bits'):]
    # These exact guards already exist in the original grid interpolation.
    # Use them for point interpolation/derivatives too, avoiding the confirmed
    # heap overflow when the +2 sample lies beyond a tile's one-sample padding.
    guard=b'''\t\t\t\t// Use the same boundary stencil as the production grid sampler.
\t\t\t\t// A tile includes one padding sample, not two past its last edge.
\t\t\t\tint latstencil[4] = {-elev_stride,0,elev_stride,2*elev_stride};
\t\t\t\tint lngstencil[4] = {-1,0,1,2};
\t\t\t\tif (lat0 < 0) latstencil[0] = 0;
\t\t\t\telse if (lat0 >= elev_grid) latstencil[3] = elev_stride;
\t\t\t\tif (lng0 < 0) lngstencil[0] = 0;
\t\t\t\telse if (lng0 >= elev_grid) lngstencil[3] = 1;
'''
    if source.count(guard)!=1:raise ValueError('terrain point boundary guard changed')
    point_end=source.index(b'void ElevationManager::ElevationGrid (')
    point=source[:point_end].replace(guard,b'')
    for row,r in enumerate(['-elev_stride','0','elev_stride','2*elev_stride']):
        for col,c in enumerate(['-1','0','1','2']):
            index=c if row==1 else r if col==1 else r+('+' if col>=2 else '')+c
            point=point.replace(('eptr[latstencil['+str(row)+']+lngstencil['+str(col)+']]').encode(),('eptr['+index+']').encode())
    for before,after in [(b'eptr[lngstencil[2]]',b'eptr[1]'),(b'eptr[lngstencil[0]]',b'eptr[-1]'),
        (b'eptr[lngstencil[3]]',b'eptr[2]'),(b'eptr[latstencil[2]]',b'eptr[elev_stride]'),
        (b'eptr[latstencil[0]]',b'eptr[-elev_stride]'),(b'eptr[latstencil[3]]',b'eptr[elev_stride*2]')]:point=point.replace(before,after)
    # The normal derivative spells its old 2*stride offset in the opposite order.
    point=point.replace(b'double dez11 = 0.5*(eptr[2*elev_stride+1]',b'double dez11 = 0.5*(eptr[elev_stride*2+1]')
    source=point+source[point_end:]
    source=source.replace(b'services->SystemTime()',b'td.SysT0').replace(
        b'services->Filter(*cbody,ilat,ilng,lvl,elev_res,t->data);',
        b'auto gc = g_pOrbiter->GetGraphicsClient();\n\t\t\t\t\tif (gc) gc->clbkFilterElevation((OBJHANDLE)cbody, ilat, ilng, lvl, elev_res, t->data);')
    if source.rstrip(b'\n')!=old[old.index(b'// Tile quadrants and mask bits'):].rstrip(b'\n'):
        raise ValueError('production terrain interpolation, normals, cache selection or grid formulas/order changed')
    # Preserve the ordered scale/offset/mask/output expressions for both file
    # and archive paths. Ownership, checked reads and path access are adapters.
    actual=types(current('Src/Orbiter/elevmgrFile.cpp'))
    def conversions(data):
        lines=[]
        for line in data.splitlines():
            if re.search(rb'elev\[i\]\s*(?:=|\+=)|(?:^\s*(?:double |INT16 )?(?:scale|offset|rescale|sofs)\s*=)|const (?:INT16|UINT8) mask',line):
                lines.append(re.sub(rb'\s+',b'',line))
        return lines
    if conversions(actual)!=conversions(old):raise ValueError('production elevation scale/offset/mask conversion changed')
    print('Original production terrain formulas/order conserved; explicit file/services and bounded point/normal stencils')

if __name__=='__main__':verify()
