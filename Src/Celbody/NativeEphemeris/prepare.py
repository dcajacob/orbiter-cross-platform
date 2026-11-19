from pathlib import Path
import sys

source = Path(sys.argv[1])
dest = Path(sys.argv[2])


def patch(relative, changes, trim_at=None, append=""):
    result = (source / relative).read_text()
    if trim_at:
        result = result[:result.index(trim_at)]
    for before, after in changes:
        if before not in result:
            raise ValueError(f"{relative}: missing expected text {before!r}")
        result = result.replace(before, after)
    (dest / Path(relative).name).write_text(result + append)


factory = '\n#include "native-ephemeris-factory.inc"\n'
patch('Vsop87/Vsop87.h', [
    ('#include "OrbiterAPI.h"\n#include "CelbodyAPI.h"', '#include "native-ephemeris-base.h"'),
    ('class DLLEXPORT VSOPOBJ: public CELBODY2', 'class VSOPOBJ: public NativeEphemerisBase'),
    ('OBJHANDLE hCBody', 'const orbiter::native::CelestialInit& context'),
    ('FILEHANDLE cfg', 'std::ifstream* cfg'),
])
patch('Vsop87/Vsop87.cpp', [
    ('#define DLLCLBK extern "C" __declspec(dllexport)\n', ''),
    ('OBJHANDLE hCBody): CELBODY2 (hCBody)', 'const orbiter::native::CelestialInit& context): NativeEphemerisBase(context)'),
    ('double interval = 10.0;', 'interval = 10.0;'),
    ('FILEHANDLE cfg', 'std::ifstream* cfg'),
    ('CELBODY2::clbkInit', 'NativeEphemerisBase::clbkInit'),
    ('oapiReadItem_float (cfg, (char*)', 'GetItemReal (*cfg, '),
    ('ifstream ifs (cbuf);', 'ifstream ifs(Host().Resource(cbuf));'),
    ('oapiWriteLogError("VSOP87 %s: Data file not found: %s", name, cbuf);\n\t\treturn false;', 'throw std::runtime_error(std::string("Cannot read VSOP87 data: ") + cbuf);'),
    ('oapiWriteLogV("VSOP87(%c) %s: Precision %0.1le, Terms %d/%d", sid, name, prec, nused, ntot);', 'std::snprintf(cbuf, sizeof(cbuf), "VSOP87(%c) %s: Precision %0.1le, Terms %d/%d", sid, name, prec, nused, ntot);\n\tHost().Log(cbuf);'),
    ('oapiTime2MJD', 'Host().TimeToMJD'),
])
patch('Vsop87/Earth/Earth.h', [
    ('OBJHANDLE hCBody', 'const orbiter::native::CelestialInit& context'),
    ('FILEHANDLE cfg', 'std::ifstream* cfg'),
])
patch('Vsop87/Earth/Earth.cpp', [
    ('OBJHANDLE hCBody): VSOPOBJ (hCBody)', 'const orbiter::native::CelestialInit& context): VSOPOBJ(context)'),
    ('FILEHANDLE cfg', 'std::ifstream* cfg'),
], 'DLLCLBK void InitModule', '\nusing EphemerisProvider = Earth;\nconstexpr auto ephemerisName = "Legacy Earth VSOP87";\n' + factory)
patch('Moon/ELP82.cpp', [
    ('#include "OrbiterAPI.h"', '#include "native-ephemeris-base.h"'),
    ('int ELP82_read (double prec)', 'int ELP82_read(double prec, orbiter::native::CelestialHost& host)'),
    ('int ELP82 (double mjd, double *r)', 'int ELP82(double mjd, double *r, orbiter::native::CelestialHost& host)'),
    ('ELP82_read (def_prec);', 'ELP82_read(def_prec, host);'),
    ('ifstream ifs (datf);', 'ifstream ifs(host.Resource(datf));'),
    ('oapiWriteLogError("ELP82: Data file not found: %s", datf);\n\t\treturn -1;', 'throw std::runtime_error(std::string("Cannot read ELP82 data: ") + datf);'),
    ('oapiWriteLogV("ELP82: Precision %0.1le, Terms %d/%d", prec, ntot, mtot);', 'char info[128];\n\tstd::snprintf(info, sizeof(info), "ELP82: Precision %0.1le, Terms %d/%d", prec, ntot, mtot);\n\thost.Log(info);'),
])
patch('Moon/Moon.cpp', [
    ('#include "OrbiterAPI.h"\n#include "CelbodyAPI.h"', '#include "native-ephemeris-base.h"'),
    ('int  ELP82_read (double prec);', 'int ELP82_read(double prec, orbiter::native::CelestialHost& host);'),
    ('int  ELP82 (double mjd, double *r);', 'int ELP82(double mjd, double *r, orbiter::native::CelestialHost& host);'),
    ('ELP82 (mjd, ret);', 'ELP82(mjd, ret, Host());'),
    (', sp[0].param);', ', sp[0].param, Host());'),
    (', sp[1].param);', ', sp[1].param, Host());'),
    (', s0->param);', ', s0->param, Host());'),
    (', s1->param);', ', s1->param, Host());'),
    ('class Moon: public CELBODY2', 'class Moon: public NativeEphemerisBase'),
    ('Moon (OBJHANDLE hObj);', 'Moon(const orbiter::native::CelestialInit& context);\n\t~Moon() override { ELP82_exit(); }'),
    ('FILEHANDLE cfg', 'std::ifstream* cfg'),
    ('Moon::Moon (OBJHANDLE hObj): CELBODY2 (hObj)\n{', 'Moon::Moon(const orbiter::native::CelestialInit& context): NativeEphemerisBase(context)\n{\n\tELP82_init();'),
    ('oapiReadItem_float (cfg, (char*)"ErrorLimit", prec);', 'GetItemReal(*cfg, "ErrorLimit", prec);'),
    ('ELP82_read (prec);', 'ELP82_read(prec, Host());'),
    ('CELBODY2::clbkInit', 'NativeEphemerisBase::clbkInit'),
    ('oapiTime2MJD', 'Host().TimeToMJD'),
], 'DLLCLBK void InitModule', '\nusing EphemerisProvider = Moon;\nconstexpr auto ephemerisName = "Legacy Moon ELP82";\n' + factory)
