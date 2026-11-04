#!/usr/bin/env python3
"""Independently invert only declared native bindings in every original source.

This reader deliberately does not import the native source generator. Its token
comparison retains literals, calculations, branches and GL command ordering.
It is a source-conservation check, not a raster or runtime parity certificate.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
PREFIX='Src/Vessel/Dragonfly/'
LEX=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|\d+(?:\.\d*)?(?:[Ee][+-]?\d+)?|[^\s]',re.S)
INCLUDE=re.compile(r'^\s*#include\s*[<"]([^>"\n]+)[>"][^\n]*',re.M)


def tokens(source):
    return [m.group() for m in LEX.finditer(source) if not m.group().startswith(('//','/*'))]


def remove_dispatch(source,name,expected):
    # Pin the entire removed Windows-only body, including its original module
    # initialization/resource callbacks. Native factory ownership is separate.
    match=re.search(r'^[^\n]*\b'+name+r'\s*\(',source,re.M)
    if match is None:raise ValueError('Original dispatcher absent: '+name)
    depth=0;opened=False
    for token in LEX.finditer(source,match.end()):
        if token.group()=='{':depth+=1;opened=True
        elif token.group()=='}':
            depth-=1
            if opened and depth==0:
                body=source[match.start():token.end()]
                if hashlib.sha256(body.encode('cp1252')).hexdigest()!=expected:
                    raise ValueError('Original platform dispatcher changed: '+name)
                return source[:match.start()]+source[token.end():]
    raise ValueError('Original dispatcher unclosed: '+name)


def inverse(source):
    aliases={
        'oapi::UInt32':'DWORD','oapi::UInt':'UINT','std::uint8_t':'byte',
        'dragonfly::drawing::Point':'POINT','dragonfly::drawing::Context':'HDC',
        'dragonfly::drawing::Bitmap':'HBITMAP','dragonfly::drawing::Font':'HFONT',
        'dragonfly::drawing::Pen':'HPEN','dragonfly::drawing::Brush':'HBRUSH',
        'dragonfly::drawing::Module':'HINSTANCE','dragonfly::drawing::GlContext':'HGLRC',
        'dragonfly::drawing::BitmapFileHeader':'BITMAPFILEHEADER',
        'dragonfly::drawing::BitmapInfoHeader':'BITMAPINFOHEADER','dragonfly::drawing::RgbTriple':'RGBTRIPLE',
        'dragonfly::InstrumentContextRestore':'dragonfly::WglContextRestore',
        'dragonfly::InstrumentTarget':'dragonfly::WglBitmapTarget',
        'InstrumentTarget':'WglBitmapTarget','InstrumentContextRestore':'WglContextRestore',
        'orbiter::production::ComparePrefix':'strnicmp'}
    constants={'SolidPen':'PS_SOLID','NullPen':'PS_NULL','BackwardDiagonal':'HS_BDIAGONAL',
        'AlignCenter':'TA_CENTER','AlignLeft':'TA_LEFT','AlignRight':'TA_RIGHT','Opaque':'OPAQUE',
        'Transparent':'TRANSPARENT','NormalWeight':'FW_NORMAL','AnsiCharset':'ANSI_CHARSET',
        'RasterPrecision':'OUT_RASTER_PRECIS','DefaultClipPrecision':'CLIP_DEFAULT_PRECIS',
        'ProofQuality':'PROOF_QUALITY','DefaultPitch':'DEFAULT_PITCH','CopyPixels':'SRCCOPY'}
    calls='CreateCompatibleDC CreateCompatibleBitmap SelectObject DeleteObject DeleteDC CreatePen CreateSolidBrush CreateHatchBrush CreateFont LoadBitmap SetTextColor SetBkColor SetBkMode SetTextAlign TextOut LineTo MoveToEx Rectangle Ellipse Arc Pie Polygon BitBlt'.split()
    functions={name:name for name in calls}
    functions.update(Color='RGB',Resource='MAKEINTRESOURCE',GetContext='oapiGetDC',ReleaseContext='oapiReleaseDC',
        CreateSurface='oapiCreateSurface',DestroySurface='oapiDestroySurface',RegisterPanelBackground='oapiRegisterPanelBackground',
        Blt='oapiBlt',Bounds='_R',OpenResource='fopen')
    aliases.update({'dragonfly::drawing::'+a:b for a,b in {**constants,**functions}.items()})
    # Work on lexical tokens so text/character literals cannot conceal an
    # altered calculation or be rewritten as a platform alias.
    sequences=sorted([(tokens(a),tokens(b)) for a,b in aliases.items()],key=lambda item:-len(item[0]))
    actual=tokens(source);result=[];i=0
    while i<len(actual):
        for before,after in sequences:
            if actual[i:i+len(before)]==before:
                result.extend(after);i+=len(before);break
        else:result.append(actual[i]);i+=1
    # Only bare platform-handle declarations gain empty ownership. Numeric,
    # pointer, array and user state initializers are outside this rule.
    source=' '.join(result)
    declaration=re.compile(r'\b(HDC|HBITMAP|HFONT|HPEN|HBRUSH|HINSTANCE|HGLRC)\s+([A-Za-z_]\w*\s*=\s*nullptr(?:\s*,\s*[A-Za-z_]\w*\s*=\s*nullptr)*)\s*;')
    source=declaration.sub(lambda m:m[1]+' '+re.sub(r'\s*=\s*nullptr','',m[2])+' ;',source)
    return tokens(source)


def verify_text(name,original,generated,names):
    if name=='Dragonfly.cpp':
        original=remove_dispatch(original,'DllMain','1378b675a41700dc508446010d5d3a1d524652c41c38f1bc35c4d6e724cd2e01')
        suffix='\n#include "NativeDragonflyFactory.inc"\n'
        if not generated.endswith(suffix) or generated.count('"NativeDragonflyFactory.inc"')!=1:
            raise ValueError('Checked native factory boundary differs')
        generated=generated[:-len(suffix)]
    if name=='panel.cpp':original=remove_dispatch(original,'MsgProc','3792675aee73ad047d4d6df2bc15823f81d905128006d962e3fc34ab1013e8c5')
    expected=[]
    for match in INCLUDE.finditer(original):
        header=match[1].strip()
        if header.casefold()=='windows.h':continue
        if header.casefold()=='orbitersdk.h':header='NativeDrawing.h'
        elif header in ('WglBitmapTarget.h','WglContext.h'):header='NativeInstrument.h'
        elif header.replace('\\','/').casefold() in ('gl/gl.h','gl/glu.h'):header=header.replace('\\','/')
        else:header=names.get(header.casefold(),header)
        expected.append(header)
    if expected!=[m[1].strip() for m in INCLUDE.finditer(generated)]:
        raise ValueError('Native include-only bindings differ: '+name)
    before=tokens(INCLUDE.sub('',original));after=inverse(INCLUDE.sub('',generated))
    if before!=after:
        index=next((i for i,(a,b) in enumerate(zip(before,after)) if a!=b),min(len(before),len(after)))
        raise ValueError('Original Dragonfly tokens changed: '+name+' at token '+str(index)+
            '\noriginal: '+' '.join(before[max(0,index-8):index+12])+ '\nnative: '+' '.join(after[max(0,index-8):index+12]))


def verify(generated):
    from Dragonfly.source_audit import verify as original_check
    original_check()
    paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,'--',PREFIX],text=True).splitlines()
    names={Path(p).name.casefold():Path(p).name for p in paths if Path(p).parent.as_posix()==PREFIX.rstrip('/')}
    sources=[p for p in paths if Path(p).suffix.lower() in ('.cpp','.h')]
    if len(sources)!=22:raise ValueError('Original native source/header closure differs')
    for path in sources:
        name=path.removeprefix(PREFIX)
        original=(ROOT/path).read_bytes().decode('cp1252').replace('\r\n','\n')
        actual=(generated/name).read_bytes().decode('cp1252').replace('\r\n','\n')
        verify_text(name,original,actual,names)
    print('Independently conserved all 22 original Dragonfly C++/header token streams; physical, internal-system, attitude and GL drawing commands retained')
    return sources


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--generated',type=Path,required=True)
    verify(parser.parse_args().generated)
