#!/usr/bin/env python3
"""Keep the original system loader, ownership and simulation loop ordering."""
from surface_source import old,now,equal

def verify():
    name='Src/Orbiter/Psys.cpp'
    original=old(name);actual=now(name)
    original=original[original.index('PlanetarySystem::PlanetarySystem'):]
    actual=actual[actual.index('PlanetarySystem::PlanetarySystem'):actual.index('void PlanetarySystem::ForEach')]
    actual=actual.replace('\ttry {\n\t\tRead (fname, config, outputLoadStatus, callbackContext);\n\t} catch (...) {\n\t\tClear();\n\t\tthrow;\n\t}', '\tRead (fname, config, outputLoadStatus, callbackContext);')
    replacements=[
        ('GetWorldVesselServices().ForceUpdate();','g_bForceUpdate = true;'),
        ('DelBody(&GetWorldVesselServices().State(*vessels.back()))','DelBody(vessels.back())'),
        ('GetWorldVesselServices().DeleteStructure(supervessels[i]);','delete supervessels[i];'),
        ('GetWorldVesselServices().Create(*this,pc,pd,ifs)','new Vessel (this, pc, pd, ifs)'),
        ('GetWorldVesselServices().Name(*vessels[i])','vessels[i]->Name()'),
        ('GetWorldVesselServices().Write(*vessels[i],os)','vessels[i]->Write (os)'),
        ('GetWorldVesselServices().OptionChanged(*vessels[i],cat,item)','vessels[i]->OptionChanged(cat, item)'),
        ('GetBodyServices().ConfigPath(fname)','config->ConfigPath(fname)'),
        ('AddBody (&GetWorldVesselServices().State(*_vessel))','AddBody (_vessel)'),
        ('DelBody (&GetWorldVesselServices().State(*_vessel))','DelBody (_vessel)'),
        ('GetWorldVesselServices().Structure(*vessel1)','vessel1->SuperStruct()'),
        ('GetWorldVesselServices().Structure(*vessel2)','vessel2->SuperStruct()'),
        ('GetWorldVesselServices().CreateStructure(*vessel1,*vessel2,port1,port2,mixmoments)','new SuperVessel (vessel1, vessel2, port1, port2, mixmoments)'),
        ('GetWorldVesselServices().Merge(*sv1,*vessel1,port1,*vessel2,port2)','sv1->Merge (vessel1, port1, vessel2, port2)'),
        ('GetWorldVesselServices().Add(*sv1,*vessel1,port1,*vessel2,port2,mixmoments)','sv1->Add (vessel1, port1, vessel2, port2, mixmoments)'),
        ('GetWorldVesselServices().Add(*sv2,*vessel2,port2,*vessel1,port1,mixmoments)','sv2->Add (vessel2, port2, vessel1, port1, mixmoments)'),
        ('GetWorldVesselServices().Detach(*sv,*_vessel,port,vsep)','sv->Detach (_vessel, port, vsep)'),
        ('GetWorldVesselServices().Empty(*sv)','!sv->nVessel()'),
        ('GetWorldVesselServices().Update(*supervessels[i],force)','supervessels[i]->Update (force)'),
        ('GetWorldVesselServices().Update(*vessels[i],force)','vessels[i]->Update (force)'),
        ('GetWorldVesselServices().PostUpdate(*supervessels[i])','supervessels[i]->PostUpdate ()'),
        ('GetWorldVesselServices().Timejump(*vessels[i],jump.dt,jump.mode)','vessels[i]->Timejump(jump.dt, jump.mode)'),
        ('GetWorldVesselServices().ProcessMessage(*vessels[i],msg,data)','vessels[i]->ProcessMessage (msg, data)'),
        ('SceneLabelList','oapi::GraphicsClient::LABELLIST'),('SceneLabel','oapi::GraphicsClient::LABELSPEC')]
    for method in ('PostCreation','InitSupervessel','ModulePostCreation','UpdateBodyForces','PostUpdate'):
        replacements.append((f'GetWorldVesselServices().{method}(*vessels[i])',f'vessels[i]->{method}()'))
    for source,target in replacements:actual=actual.replace(source,target)
    equal(original,actual,'Complete production PlanetarySystem loader/ownership/update ordering')
    a=old('Src/Orbiter/Astro.cpp');start=a.index('void Equ2Ecl (');end=a.index('void Orthodome (',start)
    if a[start:end].rstrip() not in now('Src/Orbiter/Production/SurfaceNavigation.cpp'):
        raise ValueError('Original equatorial/ecliptic conversion changed')
    print('Original system loading, ownership, docking and update ordering conserved through real-vessel adapters')

if __name__=='__main__':verify()
