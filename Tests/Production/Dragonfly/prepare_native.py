#!/usr/bin/env python3
"""Generate mechanically bound native copies of the complete original Dragonfly module."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
PREFIX='Src/Vessel/Dragonfly/'
sys.path.insert(0,str(HERE.parent))
from Dragonfly.source_audit import verify
from Dragonfly.native_source_audit import verify as verify_generated


def sha(body):return hashlib.sha256(body).hexdigest()
def canonical(body):return body.replace(b'\r\n',b'\n')
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])


def remove_platform_dispatch(source,name):
    signature=re.search(r'^[^\n]*\b'+name+r'\s*\(',source,re.M)
    if signature is None:raise ValueError('Original Windows dispatcher missing: '+name)
    start=signature.start();begin=source.index('{',signature.end());depth=0
    tokens=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',re.S)
    for token in tokens.finditer(source,begin):
        if token.group()=='{':depth+=1
        elif token.group()=='}':
            depth-=1
            if not depth:return source[:start]+source[token.end():]
    raise ValueError('Original Windows dispatcher unclosed: '+name)


def adapt(name,body,names):
    source=body.decode('cp1252').replace('\r\n','\n')
    if name=='Dragonfly.cpp':source=remove_platform_dispatch(source,'DllMain')
    if name=='panel.cpp':source=remove_platform_dispatch(source,'MsgProc')
    # The original owning lists delete polymorphic hydraulic/electrical objects
    # through these base pointers. Give the native copies concrete destruction;
    # all fields, construction and simulation method bodies remain unchanged.
    for header,kind in (('Hsystems.h','h_object'),('Esystems.h','e_object')):
        if name==header:
            anchor='\t'+kind+'();'
            if source.count(anchor)!=1:raise ValueError('Original system constructor boundary differs: '+kind)
            source=source.replace(anchor,anchor+'\n\tvirtual ~'+kind+'()=default;',1)
    source=re.sub(r'#include\s*<\s*windows\.h\s*>','',source,flags=re.I)
    source=re.sub(r'#include\s*<\s*GL[\\/](gl|glu)\.h\s*>',lambda m:'#include <GL/'+m[1]+'.h>',source)
    def include(match):
        incoming=match[1]
        if incoming.lower()=='orbitersdk.h':target='NativeDrawing.h'
        elif incoming in ('WglBitmapTarget.h','WglContext.h'):target='NativeInstrument.h'
        else:target=names.get(incoming.casefold(),incoming)
        return '#include "'+target+'"'
    source=re.sub(r'#include\s*"([^"\n]+)"',include,source)
    types={'DWORD':'oapi::UInt32','UINT':'oapi::UInt','byte':'std::uint8_t','POINT':'dragonfly::drawing::Point',
        'HDC':'dragonfly::drawing::Context','HBITMAP':'dragonfly::drawing::Bitmap','HFONT':'dragonfly::drawing::Font',
        'HPEN':'dragonfly::drawing::Pen','HBRUSH':'dragonfly::drawing::Brush','HINSTANCE':'dragonfly::drawing::Module',
        'HGLRC':'dragonfly::drawing::GlContext','BITMAPFILEHEADER':'dragonfly::drawing::BitmapFileHeader',
        'BITMAPINFOHEADER':'dragonfly::drawing::BitmapInfoHeader','RGBTRIPLE':'dragonfly::drawing::RgbTriple'}
    constants={'PS_SOLID':'SolidPen','PS_NULL':'NullPen','HS_BDIAGONAL':'BackwardDiagonal',
        'TA_CENTER':'AlignCenter','TA_LEFT':'AlignLeft','TA_RIGHT':'AlignRight','OPAQUE':'Opaque','TRANSPARENT':'Transparent',
        'FW_NORMAL':'NormalWeight','ANSI_CHARSET':'AnsiCharset','OUT_RASTER_PRECIS':'RasterPrecision',
        'CLIP_DEFAULT_PRECIS':'DefaultClipPrecision','PROOF_QUALITY':'ProofQuality','DEFAULT_PITCH':'DefaultPitch','SRCCOPY':'CopyPixels'}
    functions={name:name for name in ('CreateCompatibleDC','CreateCompatibleBitmap','SelectObject','DeleteObject','DeleteDC',
        'CreatePen','CreateSolidBrush','CreateHatchBrush','CreateFont','LoadBitmap','SetTextColor','SetBkColor','SetBkMode',
        'SetTextAlign','TextOut','LineTo','MoveToEx','Rectangle','Ellipse','Arc','Pie','Polygon','BitBlt')}
    functions.update(RGB='Color',MAKEINTRESOURCE='Resource',oapiGetDC='GetContext',oapiReleaseDC='ReleaseContext',
        oapiCreateSurface='CreateSurface',oapiDestroySurface='DestroySurface',oapiRegisterPanelBackground='RegisterPanelBackground',
        oapiBlt='Blt',_R='Bounds',fopen='OpenResource')
    for before,after in {**types,**{k:'dragonfly::drawing::'+v for k,v in constants.items()}}.items():
        source=re.sub(r'\b'+before+r'\b',after,source)
    for before,after in functions.items():
        source=re.sub(r'(?<![\w:.>])\b'+before+r'\s*(?=\()', 'dragonfly::drawing::'+after,source)
    source=source.replace('WglContextRestore','InstrumentContextRestore').replace('WglBitmapTarget','InstrumentTarget')
    source=re.sub(r'\bstrnicmp\b','orbiter::production::ComparePrefix',source)
    # Platform handles have explicit empty ownership before first use. Physical
    # state fields, their original initialization and every update stay intact.
    def initialize(match):
        variables=match[2]
        if not all(re.fullmatch(r'\s*[A-Za-z_]\w*\s*',v) for v in variables.split(',')):return match[0]
        return match[1]+','.join(v.strip()+'=nullptr' for v in variables.split(','))+';'
    source=re.sub(r'(?m)^(\s*dragonfly::drawing::(?:Context|Bitmap|Font|Pen|Brush|Module|GlContext)\s+)([^;\n]+);',initialize,source)
    if name=='Dragonfly.cpp':source+='\n#include "NativeDragonflyFactory.inc"\n'
    return source.encode('cp1252')


def original_paths():return git('ls-tree','-r','--name-only',BASE,'--',PREFIX).decode().splitlines()


def resources():
    definitions={name:int(number) for name,number in re.findall(r'^#define\s+(IDB_BITMAP\d+)\s+(\d+)',
        (ROOT/PREFIX/'resource.h').read_text(),re.M)}
    entries=re.findall(r'^\s*(IDB_BITMAP\d+)\s+BITMAP\s+DISCARDABLE\s+"([^"\n]+)"',
        (ROOT/PREFIX/'panel.rc').read_text(),re.M)
    if len(entries)!=28 or {name for name,_ in entries}!=set(definitions):raise ValueError('Original 28 bitmap resource IDs differ')
    return [(definitions[name],filename) for name,filename in entries]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=lambda value:Path(value).resolve(),required=True)
    p.add_argument('--verify-output',action='store_true')
    a=p.parse_args()
    if a.output.exists()!=a.verify_output:raise ValueError('Fresh source output or explicit read-only verification required; replacement forbidden')
    verify();producer=git('rev-parse','HEAD').decode().strip();paths=original_paths()
    names={Path(name).name.casefold():Path(name).name for name in paths if Path(name).parent.as_posix()==PREFIX.rstrip('/')}
    inputs={name:(ROOT/name).read_bytes() for name in paths}
    extra=[HERE/'prepare_native.py',HERE/'source_audit.py',HERE/'native_source_audit.py',*(ROOT/PREFIX/'Native').glob('*')]
    for path in extra:
        if path.is_file():inputs[path.relative_to(ROOT).as_posix()]=path.read_bytes()
    for name,body in inputs.items():
        if canonical(body)!=canonical(git('show',producer+':'+name)):
            raise ValueError('Native module source differs from immutable producer: '+name)
    if not a.verify_output:a.output.mkdir(parents=True)
    generated={};original={}
    for name in paths:
        body=inputs[name];relative=name.removeprefix(PREFIX);original[name]=sha(body)
        if Path(name).suffix.lower() in ('.cpp','.h'):body=adapt(relative,body,names)
        target=a.output/relative
        if a.verify_output:
            if target.read_bytes()!=body:raise ValueError('Generated native source bytes changed: '+relative)
        else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        generated[relative]=sha(body)
    table='// Original panel.rc resource IDs and byte-exact installed BMP filenames.\n'
    for number,filename in resources():table+='{'+str(number)+',"'+filename+'"},\n'
    if a.verify_output:
        if (a.output/'NativeResourceTable.inc').read_bytes()!=table.encode():raise ValueError('Original bitmap resource table changed')
    else:(a.output/'NativeResourceTable.inc').write_text(table)
    generated['NativeResourceTable.inc']=sha(table.encode())
    if {p.relative_to(a.output).as_posix():sha(p.read_bytes()) for p in a.output.rglob('*') if p.is_file() and p!=a.output/'native-source.json'}!=generated:
        raise ValueError('Generated native source tree differs')
    verify_generated(a.output)
    report=dict(status='prepared-awaiting-build-and-runtime',original_source=BASE,producer_commit=producer,
        source_sha256_lf={name:sha(canonical(body)) for name,body in inputs.items()},original_files_sha256=original,
        generated_files_sha256=generated,bitmap_resources=resources(),native_admission_qualified=False,phase6_complete=False,
        scope='Complete original module; mechanical SDK/drawing/resource/path/case bindings, concrete polymorphic teardown, empty platform-handle ownership '
              'and checked native factory. Every physical/internal-system/attitude/GL drawing body retained. No class admission.')
    if a.verify_output:
        if json.loads((a.output/'native-source.json').read_text())!=report:raise ValueError('Native module source provenance changed')
    else:(a.output/'native-source.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Prepared complete original Dragonfly native source with all 28 exact bitmap resources; runtime qualification pending')


if __name__=='__main__':main()
