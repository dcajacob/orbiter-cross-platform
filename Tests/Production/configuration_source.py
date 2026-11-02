#!/usr/bin/env python3
"""Conserve production configuration behavior and public visual declarations."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PRIOR = 'b165fc21a036aa6bde2343c35ac9ca7992441a82'

def original(name):
    return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n')

def current(name):
    return (ROOT/name).read_bytes().replace(b'\r\n',b'\n')

def verify():
    name = 'Src/Orbiter/Config.cpp'
    source = current(name).split(b'using namespace std;',1)[1]
    for before, after in [
        (b'orbiter::production::ConfigurationRectangle', b'RECT'),
        (b'orbiter::production::ConfigurationWriteResult', b'BOOL'),
        (b'orbiter::production::UInt32', b'DWORD'),
        (b'orbiter::production::CompareText', b'_stricmp'),
        (b'orbiter::production::ComparePrefix', b'_strnicmp'),
        (b'new char[strlen(fname)+1];\n#ifdef _WIN32\n\tTRACENEW\n#endif', b'new char[strlen(fname)+1]; TRACENEW'),
        (b'#ifdef _WIN32\n\tRECT r;', b'\tRECT r;'),
        (b'\n#endif\n\t// Native window selection supplies monitor dimensions in its window adapter.', b''),
        (b'if (!fname) return 0;', b'if (!fname) return FALSE;'),
        (b'if (!ofs) return 0;', b'if (!ofs) return FALSE;'),
        (b'\tofs << flush;\n\treturn 1;', b'\tofs << flush;\n\treturn TRUE;'),
        (b'''if (is.getline (c, chunk)) {
			// Match Windows text streams when reading stock CRLF files on POSIX.
			const size_t length = strlen(cbuf);
			if (length && cbuf[length-1] == '\\r') cbuf[length-1] = '\\0';
			return cbuf;
		}''', b'if (is.getline (c, chunk)) return cbuf;'),
        (b"\t// Windows text streams remove CR; POSIX text streams retain it.\n\tif (i && cbuf[i-1] == '\\r') cbuf[i-1] = '\\0';\n", b'')]:
        source = source.replace(before,after)
    if source != original(name).split(b'using namespace std;',1)[1]:
        raise ValueError('production Config defaults, parsing or persistence changed beyond declared platform/CRLF adapters')
    source = current('Src/Orbiter/Config.h').split(b'private:',1)[1]
    if source != original('Src/Orbiter/Config.h').split(b'private:',1)[1].replace(
            b'#endif // !__CONFIG_H',
            b'// Defaults used by the existing Windows settings dialogs.\n'
            b'extern ORBITER_PRODUCTION_API CFG_PHYSICSPRM CfgPhysicsPrm_default;\n'
            b'extern ORBITER_PRODUCTION_API CFG_INSTRUMENTPRM CfgInstrumentPrm_default;\n'
            b'extern ORBITER_PRODUCTION_API CFG_DEBUGPRM CfgDebugPrm_default;\n\n#endif // !__CONFIG_H'):
        raise ValueError('production Config private storage changed')
    name = 'Orbitersdk/include/GraphicsAPI.h'
    sdk = original(name)
    start = sdk.index(b'/// \\defgroup cfgprm ')
    end = sdk.index(b'const UINT TEXIDX_MFD0',start)
    flags = sdk[start:end]
    star = re.search(rb'struct StarRenderPrm \{.*?\n\};',sdk,re.S)[0]
    values = current('Orbitersdk/include/OrbiterVisualData.h')
    if values.count(flags) != 1 or values.count(star) != 1:
        raise ValueError('public visual values were not extracted verbatim')
    sdk = (sdk[:start]+b'#include "OrbiterVisualData.h"\n\n'+sdk[end:]).replace(star+b'\n',b'')
    for record in (b'SurftileSpec',b'FogParam'):
        block = re.search(rb'struct '+record+rb' \{.*?\n\};',sdk,re.S)[0]
        if values.count(block)!=1:
            raise ValueError('public surface/fog record was not extracted verbatim')
        sdk=sdk.replace(block+b'\n',b'')
    if sdk != current(name):
        raise ValueError('Windows graphics SDK changed beyond verbatim value extraction')
    name = 'Src/Orbiter/VectorMap.h'
    actual_map=current(name)
    if (ROOT/'Src/Orbiter/Production/CockpitGraphics.h').exists():
        # Verify the later cockpit binding first, then let this earlier audit
        # inspect its exact predecessor. No map flags or calculations escape
        # conservation through a type-name substitution.
        from cockpit_source import verify as verify_cockpit,BASE as cockpit_base
        verify_cockpit()
        actual_map=subprocess.check_output(['git','-C',str(ROOT),'show',cockpit_base+':'+name]).replace(b'\r\n',b'\n')
    source = original(name)
    start = source.index(b'#define DISP_GRIDLINE')
    end = source.index(b'// flag values for RedrawFlag',start)
    if current('Src/Orbiter/Production/MapFlags.h').count(source[start:end]) != 1 or (
            source[:start]+b'#include "Production/MapFlags.h"\n\n'+source[end:]) != actual_map:
        raise ValueError('map flags changed beyond verbatim value extraction')
    print('Production Config behavior and Windows graphics SDK conserved after explicit platform/CRLF adapters')

if __name__ == '__main__': verify()
