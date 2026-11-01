#!/usr/bin/env python3
"""Preserve radio math/data while separating production object queries."""
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2]
PRIOR='0a9040fa'
def original(name):return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n')
def current(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n')
def verify():
    name='Src/Orbiter/Nav.cpp'
    source=current(name).split(b'using namespace std;',1)[1].replace(b'\nusing namespace orbiter::production;',b'')
    substitutions=[
        (b'UInt32',b'DWORD'),(b'NavigationData',b'NAVDATA'),(b'CompareText (',b'_stricmp ('),
        (b'ComparePrefix (',b'_strnicmp ('),(b'NavigationText (',b'_snprintf ('),
        (b'GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);',b'TRACENEW'),
        (b'GetNavigationServices().PlanetState(planet).EquatorialToLocal',b'planet->EquatorialToLocal'),
        (b'GetNavigationServices().PlanetState(planet).Size()',b'planet->Size()'),
        (b'GetNavigationServices().TerrainHeight(planet, lng, lat)',b'planet->Elevation (lng, lat)'),
        (b'GetNavigationServices().PlanetState(planet).GRot()',b'planet->GRot()'),
        (b'GetNavigationServices().PlanetState(planet).GPos()',b'planet->GPos()'),
        (b'GetNavigationServices().BasePlanet(_base)',b'_base->RefPlanet()'),
        (b'GetNavigationServices().BaseState(GetBase()).Name()',b'GetBase()->Name()'),
        (b'GetNavigationServices().DockCount(vessel)',b'vessel->nDock()'),
        (b'GetNavigationServices().Dock(vessel, i)',b'vessel->GetDockParams(i)'),
        (b'GetNavigationServices().VesselState(vessel).Name()',b'vessel->Name()'),
        (b'GetNavigationServices().DockPosition(vessel, ps)',b'vessel->GetDockGPos (ps)'),
        (b'(DWORD)(std::int64_t)((freq - NAV_RADIO_FREQ_MIN)*20.0 + 0.5)',b'(DWORD)((freq - NAV_RADIO_FREQ_MIN)*20.0 + 0.5)'),
        (b'\tnav = nullptr;\n',b''),(b'delete nav[i];',b'delete []nav[i];'),
        (b'''void Nav_XPDR::GPos (Vector &gp) const
{
	gp.Set (GetNavigationServices().VesselState(vessel).GPos());
}

''',b'')]
    for before,after in substitutions:source=source.replace(before,after)
    if source!=original(name).split(b'using namespace std;',1)[1]:
        raise ValueError('radio calculations/parsing changed beyond object/text/allocator adapters and defined default-channel conversion')
    source=current('Src/Orbiter/Nav.h')
    old=original('Src/Orbiter/Nav.h')
    # Every existing class field stays in its original order. The private
    # transmitter destructor becomes virtual so scalar-owned derived objects
    # can be released correctly; no public Windows SDK class is changed.
    for before,after in [(b'orbiter::production::UInt32',b'DWORD'),(b'orbiter::production::NavigationData',b'NAVDATA'),
        (b'ORBITER_PRODUCTION_API ',b''),(b'\tvirtual ~Nav() = default;\n',b''),
        (b'\tNavManager(const NavManager&) = delete;\n\tNavManager& operator=(const NavManager&) = delete;\n',b''),
        (b'void GPos (Vector &gp) const;\n\tinline const Vessel *GetVessel () const { return vessel; }\n\tvoid GetData',
         b'inline void GPos (Vector &gp) const { gp.Set (vessel->GPos()); }\n\tinline const Vessel *GetVessel () const { return vessel; }\n\tvoid GetData')]:source=source.replace(before,after)
    source=re.sub(rb'#include <fstream>\n#include "Vecmat.h".*?struct PortSpec;',b'#include <windows.h>\n#include <fstream>\n#include "Vessel.h"',source,flags=re.S)
    if source.rstrip(b'\n')!=old.rstrip(b'\n'):raise ValueError('private production radio declarations/storage changed beyond declared adapters/ownership fix')
    name='Src/Orbiter/Vessel.h';old=original(name)
    start=old.index(b'typedef struct {      // docking port definition');end=old.index(b'} PortSpec;',start)+len(b'} PortSpec;')
    port=current('Src/Orbiter/VesselPorts.h').replace(b'typedef struct PortSpec {',b'typedef struct {').replace(b'orbiter::production::UInt32',b'DWORD')
    actual=current(name)
    if (ROOT/'Src/Orbiter/Production/VesselServices.h').exists():
        from vessel_source import restore_header
        actual=restore_header(actual.decode('cp1252')).encode('cp1252')
    if port.count(old[start:end])!=1 or old[:start]+b'#include "VesselPorts.h"'+old[end:]!=actual:
        raise ValueError('production docking port layout or vessel declarations changed')
    api=original('Orbitersdk/include/OrbiterAPI.h')
    record=re.search(rb'typedef struct \{(?:(?!typedef struct \{).)*?\} NAVDATA;',api,re.S)[0]
    data=current('Src/Orbiter/Production/NavigationData.h').replace(b'UInt32',b'DWORD').replace(b'} NavigationData;',b'} NAVDATA;')
    if data.count(record)!=1:raise ValueError('native radio fields differ from original SDK navigation data')
    print('Original radio calculations/data/layout conserved; explicit world queries and correct scalar ownership')

if __name__=='__main__':verify()
