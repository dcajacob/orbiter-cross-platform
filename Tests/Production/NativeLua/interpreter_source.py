"""Conserve the original interpreter registration tables, method bodies and annotation drawing."""
import re
import subprocess
from pathlib import Path
from camera_source import windows
from vessel_runtime_source import aliases, equal, raw

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS = 'e6c948a6'


def previous(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', PREVIOUS + ':' + path]).decode('cp1252')


def verify():
    path='Src/Module/LuaScript/LuaInterpreter/Interpreter.cpp'
    source=windows(raw(path)).replace('static std::list<NOTEHANDLE *> g_notehandles;', 'std::list<NOTEHANDLE *> g_notehandles;')
    source=source.replace('#include <iterator>','').replace('#include <cstdint>','')
    source=source.replace('#include "../../../Orbiter/Production/CameraModeOwner.h"','')
    # CameraMode has no virtual destructor. Conserve the command's calculations
    # while checking the one explicit concrete-type lifetime adaptation.
    camera_delete='orbiter::production::DeleteCameraMode{}(cm);'
    if source.count(camera_delete)!=1:
        raise ValueError('Missing or ambiguous Lua camera concrete-type destruction')
    source=source.replace(camera_delete,'delete cm;')
    source=source.replace('static int CompareScriptText(const char *a, const char *b) { return _stricmp(a,b); }','')
    source=aliases(source).replace('CompareScriptText(', '_stricmp(').replace('std::uint8_t','BYTE')
    source=source.replace('std::size_t i = 0; i < std::size(glob)', 'int i = 0; i < ARRAYSIZE(glob)')
    source=source.replace('(size & 0xffffu)','LOWORD(size)').replace('(size >> 16)','HIWORD(size)')
    source=re.sub(r'#ifdef LUA_RELEASE\s*(.*?)\s*#else\s*.*?#endif',r'\1',source,flags=re.S)
    for name in ('FVECTOR4 c =', 'Sketchpad::RenderParam', 'IVECTOR2 ctr', 'IVECTOR2 *pctr',
                 'IVECTOR2 trl', 'IVECTOR2 *ptrl'):
        source=source.replace('oapi::'+name,name)
    equal(aliases(windows(previous(path))),source,'Original interpreter methods and Lua registrations')
    path='Src/Orbiter/GraphicsAPI.cpp'
    shared=raw('Src/Orbiter/Production/ScreenAnnotationMethods.inc')
    source=raw(path).replace('using AnnotationClient = GraphicsClient;\n#include "Production/ScreenAnnotationMethods.inc"',
                             shared.replace('AnnotationClient *_gc','GraphicsClient *_gc'))
    equal(previous(path),source,'Original screen annotation text, colors, layout and drawing')
    print('Full original interpreter registration/method bodies and shared annotation rendering conserved')
