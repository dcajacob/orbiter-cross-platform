#!/usr/bin/env python3
"""Exercise actual map constructors/destructors with deterministic owner-address reuse."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tests/Production'))
from camera_source import windows
from source_audit import FIELDS, cleanup_block, declaration, restore_world_cache


def function(text, name):
    start = text.index(name)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'


PREFIX = r'''
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
#include <set>
#include <stdexcept>
using namespace std;
namespace oapi { using UInt32=unsigned; struct CockpitClient { void clbkReleasePen(void*) {} }; }
enum { DISP_GRIDLINE=1, DISP_COASTLINE=2, DISP_CONTOURS=4, DISP_HORIZONLINE=8,
       DISP_VESSEL=16, DISP_BASE=32, DISP_GROUNDTRACK=64, DISP_TERMINATOR=128,
       DISP_ORBITFOCUS=256, DISP_ORBITSEL=512 };
struct Planet { bool live=true; const char *Name() const { return "Earth"; } };
struct Vessel { const Planet *planet; const Planet *ProxyPlanet() { return planet; } };
struct Pane {};
struct CustomMkrSet { struct Entry { bool active=false; }; int nset=2; Entry set[2]; };
struct RetiredWorld : logic_error { RetiredWorld():logic_error("retired world reference restored"){} };
struct VectorMap {
    struct OBJTYPE { int type; void *obj; };
    static set<VectorMap*> allocated;
    const Planet *body=nullptr; OBJTYPE selection{}; CustomMkrSet markers;
    double lng=0,lat=0;
    VectorMap() { allocated.insert(this); }
    ~VectorMap() { allocated.erase(this); }
    void SetLabelSize(int) {}
    void SetCBody(const Planet *value) { if(value && !value->live) throw RetiredWorld(); body=value; }
    void SetCenterMode(int) {}
    void SetSelection(OBJTYPE value) { selection=value; }
    void SetZoom(int) {}
    void SetDisplayFlags(unsigned) {}
    CustomMkrSet &GetCustomMarkerSet() { return markers; }
    void SetCenter(double x,double y) { lng=x;lat=y; }
    OBJTYPE GetSelection() { return selection; }
    double CntLng() { return lng; } double CntLat() { return lat; }
};
set<VectorMap*> VectorMap::allocated;
constexpr int MAXPEN=6, MAXDEFCOL=5;
int DeleteObject(void*) { return 1; }
struct Instrument {
    struct Spec {};
    struct Draw { void *solidpen=nullptr,*dashpen=nullptr; };
    static Draw draw[MAXDEFCOL][2]; static void *hdefpen[MAXPEN];
    Vessel *vessel; int IH=200;
    Instrument(Pane*,intptr_t,const Spec&,Vessel *value):vessel(value){}
    static void GlobalExit(oapi::CockpitClient*);
};
Instrument::Draw Instrument::draw[MAXDEFCOL][2]; void *Instrument::hdefpen[MAXPEN]{};
struct OtherCache { void *usr=nullptr,*elref=nullptr,*tgt=nullptr,*ref=nullptr,*btgt=nullptr,*otgt=nullptr,*Legacy_ref=nullptr,*src=nullptr; int preference=79; };
'''
MAP = r'''
struct Instrument_Map : Instrument {
    struct SavePrm { Vessel *usr; const Planet *ref; VectorMap::OBJTYPE sel; int zoom; bool track;
                     double lng,lat; unsigned dispflag,mkrflag; };
    static SavePrm saveprm;
    @RESET@
    VectorMap *map; const Planet *refplanet; int zoom; bool track; char title[50]; unsigned dispflag;
    int disp_mode,ndispprm,dispprm_top;
    Instrument_Map(Pane*,intptr_t,const Spec&,Vessel*);
    ~Instrument_Map();
    void SetSize(const Spec&) {}
};
Instrument_Map::SavePrm Instrument_Map::saveprm={0,0,{0,0},1,true,0,0,0,0};
'''
MAIN = r'''
int main() {
    Planet retired, current;
    alignas(Vessel) unsigned char storage[sizeof(Vessel)];
    auto *vessel=new(storage) Vessel{&retired};
    Instrument::Spec spec;
    {
        Instrument_Map first(nullptr,0,spec,vessel);
        first.zoom=8; first.track=true; first.map->SetCenter(.25,.5);
        first.map->SetSelection({DISP_VESSEL,&retired});
    }
    { // Normal restore within the same live world must remain unchanged.
        Instrument_Map reopened(nullptr,0,spec,vessel);
        assert(reopened.zoom==8 && reopened.track && reopened.refplanet==&retired);
        assert(reopened.map->GetSelection().obj==&retired);
    }
    vessel->~Vessel(); retired.live=false;
    auto *replacement=new(storage) Vessel{&current};
    bool rejected=false;
    try { Instrument_Map inherited(nullptr,0,spec,replacement); }
    catch(const RetiredWorld&) { rejected=true; }
    assert(rejected); // The original guard mistakes this reused address for its old owner.
    while(!VectorMap::allocated.empty()) delete *VectorMap::allocated.begin();
    @SEED@
    Instrument::GlobalExit(nullptr);
    @CHECK@
    assert(Instrument_Map::saveprm.usr==nullptr && Instrument_Map::saveprm.ref==nullptr && Instrument_Map::saveprm.sel.obj==nullptr);
    {
        Instrument_Map fresh(nullptr,0,spec,replacement);
        assert(fresh.refplanet==&current && fresh.zoom==1 && !fresh.track);
        assert(fresh.map->GetSelection().obj==nullptr);
    }
    assert(VectorMap::allocated.empty());
    replacement->~Vessel();
    cout << "same-world restore retained; reused owner rejects retired world; world cleanup clears all handles and retains scalar preferences\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    mfd = (ROOT / 'Src/Orbiter/Mfd.cpp').read_text()
    map_source = (ROOT / 'Src/Orbiter/MfdMap.cpp').read_text()
    global_exit = windows(function(mfd, 'void Instrument::GlobalExit'))
    definitions = ''
    seed, check = '', ''
    hashes = {}
    for name, (kind, fields) in FIELDS.items():
        path = ROOT / 'Src/Orbiter' / name
        body = path.read_text()
        restore_world_cache(body, name)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        method = function(body, 'static void InvalidateWorldCache()')
        if name == 'MfdMap.h':
            definitions += MAP.replace('@RESET@', method)
        else:
            definitions += 'struct ' + kind + ' { static OtherCache saveprm; ' + method + ' };\nOtherCache ' + kind + '::saveprm;\n'
            for field in fields:
                seed += kind + '::saveprm.' + field + '=&retired;\n'
                check += 'assert(' + kind + '::saveprm.' + field + '==nullptr);\n'
            check += 'assert(' + kind + '::saveprm.preference==79);\n'
    declaration_source = next(line for line in map_source.splitlines() if line.startswith('oapi::UInt32 dispflag_default'))
    program = PREFIX + definitions + declaration_source + '\n' + function(map_source, 'Instrument_Map::Instrument_Map') + function(map_source, 'Instrument_Map::~Instrument_Map')
    main_body = MAIN.replace('@SEED@', seed).replace('@CHECK@', check)
    compiler = shutil.which('c++')
    assert compiler
    report = dict(status='running', source_files_sha256=hashes, controls={})
    for label, operation, expected in (
        ('actual-world-cleanup', global_exit, True),
        ('missing-map-retirement', global_exit.replace('\tInstrument_Map::InvalidateWorldCache();\n', ''), False),
        ('missing-all-retirements', windows(function(restore_world_cache(mfd, 'Mfd.cpp'), 'void Instrument::GlobalExit')), False)):
        cpp = args.output / (label + '.cpp')
        binary = args.output / label
        cpp.write_text(program + operation + main_body)
        built = subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror',str(cpp.resolve()),'-o',str(binary.resolve())], capture_output=True, text=True)
        (args.output / (label + '-build.log')).write_text(built.stdout + built.stderr)
        assert built.returncode == 0, built.stderr
        run = subprocess.run([str(binary.resolve())], capture_output=True, text=True)
        (args.output / (label + '-run.log')).write_text(run.stdout + run.stderr)
        assert (run.returncode == 0) == expected, label
        report['controls'][label] = dict(actual_returncode=run.returncode, expected_success=expected)
    # Placement and precise-field controls for the independent source allowance.
    for name, damaged in (
        ('moved-cleanup', mfd.replace(cleanup_block(), '').replace('void Instrument::GlobalInit', cleanup_block() + 'void Instrument::GlobalInit', 1)),
        ('omitted-handle', mfd.replace('Instrument_Map::InvalidateWorldCache();', '/* omitted */', 1))):
        try:
            restore_world_cache(damaged, 'Mfd.cpp')
        except ValueError as error:
            report['controls'][name] = str(error)
        else:
            raise AssertionError('Damaged source allowance accepted: ' + name)
    report.update(status='passed', actual_map_constructor_and_destructor_used=True, actual_global_exit_and_nine_cleanup_methods_used=True,
                  scope='Controlled source-method fixture: same-world restore, deterministic reused owner address and retired-world handle rejection. It executes no simulator, dereferences no freed object and earns no runtime or SDK-layout qualification.')
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=report['status'], controls=report['controls']), indent=2))


if __name__ == '__main__':
    main()
