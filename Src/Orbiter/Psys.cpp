// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// Implementation of class PlanetarySystem

#include "AstroMath.h"
#include "Production/SurfaceNavigation.h"
#include "Production/SurfaceServices.h"
#include "Production/WorldVesselServices.h"
#include "Production/Text.h"
#include "Production/CelestialServices.h"
#include "Production/RigidBodyServices.h"
#include <fstream>
#include <stdio.h>
#include <string.h>
#include <algorithm>

#include "Config.h"
#include "PsysCore.h"
#include "Base.h"
#include "Star.h"
#include "Planet.h"
#include "PhysicsCore.h"
#include "TimeData.h"
#include "Element.h"

using namespace std;
using namespace orbiter::production;


PlanetarySystem::PlanetarySystem (char *fname, const Config* config, OutputLoadStatusCallback outputLoadStatus, void* callbackContext)
{
	try {
		Read (fname, config, outputLoadStatus, callbackContext);
	} catch (...) {
		Clear();
		throw;
	}
}

PlanetarySystem::~PlanetarySystem ()
{
	Clear ();
}

void PlanetarySystem::Clear ()
{
	DestroyDeviceObjects ();
	m_Name.clear();

	//Vessel destructor broadcasts messages to every other vessel in 'vessels'.
	//We remove it from the collection as soon as we deleted it to prevent the next Vessel to broadcast to the free'd one.
	while (vessels.size()) {
		DelBody(&GetWorldVesselServices().State(*vessels.back()));
		vessels.pop_back();
	}

	//Every element in vessels, stars, planets and celestials is also present in bodies.
	//By deallocating all bodies we can then just clear all the other collections.
	//NOTE: vessels are a special case! See comment above.
	for (size_t i = 0; i < bodies.size(); ++i)
		delete bodies[i];

	bodies    .clear();
	stars     .clear();
	planets   .clear();
	celestials.clear();

	GetWorldVesselServices().ForceUpdate();

	//Supervessels are not stored in 'bodies' so we have to take care of them manually
	for (size_t i = 0; i < supervessels.size(); ++i) {
		GetWorldVesselServices().DeleteStructure(supervessels[i]);
	}
	supervessels.clear();
}

void PlanetarySystem::InitState (const char *fname)
{
	char cbuf[256], *pc, *pd;
	ifstream ifs (fname);
	if (!ifs) return;
	if (FindLine (ifs, "BEGIN_SHIPS")) {
		for (;;) {
			if (!ifs.getline (cbuf, 256)) break;
			pc = trim_string (cbuf);
			if (!CompareText (pc, "END_SHIPS")) break;
			for (pd = pc; *pd != '\0' && *pd != ':'; pd++);
			if (*pd) *pd++ = '\0';
			else pd = 0;
			AddVessel (GetWorldVesselServices().Create(*this,pc,pd,ifs)); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
		}
	}
}

void PlanetarySystem::PostCreation ()
{
	for (size_t i = 0; i < vessels.size(); ++i) GetWorldVesselServices().PostCreation(*vessels[i]);
	for (size_t i = 0; i < vessels.size(); ++i) GetWorldVesselServices().InitSupervessel(*vessels[i]);
	for (size_t i = 0; i < vessels.size(); ++i) GetWorldVesselServices().ModulePostCreation(*vessels[i]);
}

void PlanetarySystem::Write (ostream &os)
{
	os << "BEGIN_SHIPS" << endl;
	for (size_t i = 0; i < vessels.size(); ++i)
		GetWorldVesselServices().Write(*vessels[i],os);
	os << "END_SHIPS" << endl;
}

Body *PlanetarySystem::GetObj (const char *name, bool ignorecase)
{
	for (UInt32 i = 0; i < bodies.size(); i++)
		if (!StrComp (bodies[i]->Name(), name, ignorecase)) return bodies[i];
	return 0;
}

CelestialBody *PlanetarySystem::GetGravObj (const char *name, bool ignorecase) const
{
	for (UInt32 i = 0; i < celestials.size(); i++)
		if (!StrComp (celestials[i]->Name(), name, ignorecase)) return celestials[i];
	return 0;
}

Planet *PlanetarySystem::GetPlanet (const char *name, bool ignorecase)
{
	for (size_t i = 0; i < planets.size(); i++)
		if (!StrComp (planets[i]->Name(), name, ignorecase)) return planets[i];
	return 0;
}

Vessel *PlanetarySystem::GetVessel (const char *name, bool ignorecase) const
{
	for (UInt32 i = 0; i < vessels.size(); i++)
		if (!StrComp (GetWorldVesselServices().Name(*vessels[i]), name, ignorecase)) return vessels[i];
	return 0;
}

bool PlanetarySystem::isObject (const Body *obj) const
{
	for (UInt32 i = 0; i < bodies.size(); i++)
		if (bodies[i] == obj) return true;
	return false;
}

bool PlanetarySystem::isVessel (const Vessel *v) const
{
	for (UInt32 i = 0; i < vessels.size(); i++)
		if (vessels[i] == v) return true;
	return false;
}

orbiter::production::UInt32 PlanetarySystem::nBase(const Planet *planet) const { return planet->nBase(); }
Base *PlanetarySystem::GetBase (const Planet *planet, orbiter::production::UInt32 i) { return planet->GetBase(i); }

Base *PlanetarySystem::GetBase (const Planet *planet, const char *name, bool ignorecase)
{
	for (UInt32 i = 0; i < planet->nBase(); i++)
		if (!StrComp (planet->GetBase(i)->Name(), name, ignorecase))
			return planet->GetBase(i);
	return 0;
}

Base *PlanetarySystem::GetBase (const char *name, bool ignorecase)
{
	for (UInt32 i = 0; i < celestials.size(); i++) {
		if (celestials[i]->Type() != OBJTP_PLANET) continue;
		Planet *planet = (Planet*)celestials[i];
		Base *base = GetBase (planet, name, ignorecase);
		if (base) return base;
	}
	return 0;
}

void PlanetarySystem::OptionChanged(UInt32 cat, UInt32 item)
{
	for (size_t i = 0; i < vessels.size(); i++)
		GetWorldVesselServices().OptionChanged(*vessels[i],cat,item);
}

bool PlanetarySystem::Read (char *fname, const Config* config, OutputLoadStatusCallback outputLoadStatus, void* callbackContext)
{
	int i;
	UInt32 j;
	char cbuf[256], label[128];
	
	ifstream ifs (GetBodyServices().ConfigPath(fname));
	if (!ifs) return false;
	Clear();
	if (GetItemString (ifs, "Name", cbuf)) {
		m_Name = cbuf;
	}

	// read stars
	for (;;) {
		sprintf (label, "Star%zd", stars.size() + 1);
		if (!GetItemString (ifs, label, cbuf)) break;
		OutputLoadStatus (cbuf, outputLoadStatus, callbackContext);
		AddStar (new Star (cbuf)); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	}

	// read planets
	for (i = 0;; i++) {
		sprintf (label, "Planet%d", i+1);
		if (!GetItemString (ifs, label, cbuf)) break;
		OutputLoadStatus (cbuf, outputLoadStatus, callbackContext);
		Planet *planet = new Planet (cbuf); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
		AddPlanet (planet, stars[0]);
		ScanMoons (ifs, planet, planet->Name());
	}

	for (j = 0; j < stars.size(); j++) stars[j]->RelTrueAndBaryState();
	for (j = 0; j < stars.size(); j++) stars[j]->AbsTrueState();

	if (GetItemString (ifs, "MarkerPath", cbuf)) {
		m_labelPath = cbuf;
		if (m_labelPath.back() != '\\')
			m_labelPath.push_back('\\');
	}
	else {
		m_labelPath = std::string(config->CfgDirPrm.ConfigDir) + m_Name + std::string("\\Marker\\");
	}
	m_labelList.clear();
	ScanLabelLists(ifs, true);

	return true;
}

void PlanetarySystem::OutputLoadStatus (const char *bname, OutputLoadStatusCallback outputLoadStatus, void* callbackContext)
{
	char cbuf[256];
	sprintf (cbuf, "%s: %s", m_Name.c_str(), bname);
	outputLoadStatus(cbuf, 0, callbackContext);
}

void PlanetarySystem::ScanLabelLists (ifstream &cfg, bool bScanHeaders)
{
	int i;
	char cbuf[256];
	SceneLabelList* ll;
	int idx = 0;
	ForEach(FILETYPE_MARKER, [&](const fs::directory_entry& entry) {
		// open marker file
		ifstream ulf(entry.path());
		// read label header
		if (bScanHeaders) {
			SceneLabelList list;
			//list.marker.clear();
			list.colour = 1;
			list.shape = 0;
			list.size = 1.0f;
			list.distfac = 1.0f;
			list.active = false;
			list.flag = 0;
			list.name = entry.path().stem().string();
			if (FindLine(ulf, "BEGIN_HEADER")) {
				char item[256], value[256];
				for (;;) {
					if (!ulf.getline(cbuf, 256) || !ComparePrefix(cbuf, "END_HEADER", 10)) break;
					sscanf(cbuf, "%s %s", item, value);
					if (!CompareText(item, "InitialState")) {
						if (!CompareText(value, "on")) list.active = true;
					}
					else if (!CompareText(item, "ColourIdx")) {
						int col;
						sscanf(value, "%d", &col);
						list.colour = max(0, min(5, col));
					}
					else if (!CompareText(item, "ShapeIdx")) {
						int shape;
						sscanf(value, "%d", &shape);
						list.shape = max(0, min(6, shape));
					}
					else if (!CompareText(item, "Size")) {
						float size;
						sscanf(value, "%f", &size);
						list.size = max(0.1f, min(2.0f, size));
					}
					else if (!CompareText(item, "DistanceFactor")) {
						float distfac;
						sscanf(value, "%f", &distfac);
						list.distfac = max(1e-5f, min(1e3f, distfac));
					}
					else if (!CompareText(item, "Frame")) {
						if (CompareText(value, "Ecliptic"))
							list.flag = 1; // flag for celestial position data
					}
				}
			}
			m_labelList.push_back(list);
			ll = &m_labelList.back();
		}
		else {
			ll = &m_labelList[idx++];
		}

		// check if positions are in celestial or ecliptic frame
		bool celestialpos = ((ll->flag & 1) != 0);

		// read label list for active labels, if not already present
		if (ll->active && !ll->marker.size()) {
			double lng, lat;
			int nl;
			char* pc;
			FindLine(ulf, "BEGIN_DATA");
			for (nl = 0;; nl++) {
				if (!ulf.getline(cbuf, 256)) break;
				pc = strtok(cbuf, ":");
				if (!pc || sscanf(pc, "%lf%lf", &lng, &lat) != 2) continue;
				lng = Rad(lng);
				lat = Rad(lat);
				if (celestialpos) {
					static double eps = 0.4092797095927;
					static double coseps = cos(eps), sineps = sin(eps);
					double ra = lng, dc = lat;
					Equ2Ecl(coseps, sineps, ra, dc, lng, lat);
				}
				SceneLabel ls;
				double xz = cos(lat);
				ls.pos.y = sin(lat);
				ls.pos.x = xz * cos(lng);
				ls.pos.z = xz * sin(lng);
				for (i = 0; i < 2; i++) {
					if (pc = strtok(NULL, ":")) {
						ls.label[i] = trim_string(pc);
					}
				}
				ll->marker.push_back(ls);
			}
		}
	});
}

void PlanetarySystem::ActivatePlanetLabels(bool activate)
{
	for (size_t i = 0; i < planets.size(); i++)
		planets[i]->ActivateLabels(activate);
}

void PlanetarySystem::AddBody (Body *_body)
{
	bodies.emplace_back(_body);
}

bool PlanetarySystem::DelBody (Body *_body)
{
	size_t i;
	for (i = 0; i < bodies.size(); i++)
		if (bodies[i] == _body)
			break;

	if (i == bodies.size())
		return false; // bodies not found in list

	//if (bodies[i]->s0) bodies[i]->s0 = NULL; // s0 is used in vessels destructor due to undocking of
	//if (bodies[i]->s1) bodies[i]->s1 = NULL; // vessels before deletion.
	
	delete bodies[i]; // delete actual bodies/vessels

	std::iter_swap(bodies.begin() + i, bodies.end() - 1);
	bodies.pop_back();

	return true;
}

size_t PlanetarySystem::AddStar (Star *_star)
{
	stars.emplace_back(_star);
	AddGrav (_star); // register in list of massive objects
	AddBody (_star); // register in general list
	return stars.size();
}

size_t PlanetarySystem::AddPlanet (Planet *_planet, CelestialBody *cbody)
{
	planets.emplace_back(_planet);
	AddGrav (_planet); // register in list of massive objects
	AddBody (_planet); // register in general list
	_planet->SetPsys (this);
	_planet->Attach (cbody);
	return planets.size();
}

void PlanetarySystem::ScanMoons (istream &is, CelestialBody *cbody, const char *id)
{
	char cbuf[256], name[256];
	for (int i = 0;; i++) {
		sprintf (cbuf, "%s:Moon%d", id, i+1);
		if (!GetItemString (is, cbuf, name)) return;
		Planet *moon = new Planet (name); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
		AddPlanet (moon, cbody);
		ScanMoons (is, moon, cbuf); // recursion
	}
}

void PlanetarySystem::AddGrav (CelestialBody *newBody)
{
	//(alektron) The old method sorted by mass directly while inserting into the newly allocated list.
	//While the sorting was technically more efficient this way (since most of the list was already sorted anyways),
	//it doesn't really matter much since this function is not called very often.
	//And this is just so much more readable.
	celestials.emplace_back(newBody);
	std::sort(celestials.begin(), celestials.end(), [](CelestialBody* a, CelestialBody* b) { return a->Mass() > b->Mass(); });
}

size_t PlanetarySystem::AddVessel (Vessel *_vessel)
{
	vessels.emplace_back(_vessel);
	AddBody (&GetWorldVesselServices().State(*_vessel)); // register in general list
	GetWorldVesselServices().ForceUpdate();
	return vessels.size();
}

bool PlanetarySystem::DelVessel (Vessel *_vessel)
{
	size_t i;
	for (i = 0; i < vessels.size(); i++) {
		if (vessels[i] == _vessel)
			break;
	}

	if (i == vessels.size())
		return false; // vessels not found in list

	DelBody (&GetWorldVesselServices().State(*_vessel)); //DelBody takes care of freeing the vessel
	std::iter_swap(vessels.begin() + i, vessels.end() - 1);
	vessels.pop_back();

	GetWorldVesselServices().ForceUpdate();
	return true;
}

void PlanetarySystem::AddSuperVessel (SuperVessel *sv)
{
	supervessels.emplace_back(sv);
}

bool PlanetarySystem::DelSuperVessel (SuperVessel *sv)
{
	size_t i;
	for (i = 0; i < supervessels.size(); i++) {
		if (supervessels[i] == sv)
			break;
	}

	if (i == supervessels.size())
		return false; // vessels not found in list

	GetWorldVesselServices().DeleteStructure(supervessels[i]);

	//Note that supervesslels unlike other bodies are NOT also present in the 'bodies'
	std::iter_swap(supervessels.begin() + i, supervessels.end() - 1);
	supervessels.pop_back();

	return false;
}

void PlanetarySystem::DockVessels (Vessel *vessel1, Vessel *vessel2, int port1, int port2, bool mixmoments)
{
	// if the vessels are already complex structures, store a reference to
	// the superstructures so we can remove them after merging
	SuperVessel *sv1 = GetWorldVesselServices().Structure(*vessel1);
	SuperVessel *sv2 = GetWorldVesselServices().Structure(*vessel2);

	if (!sv1 && !sv2) {    // create a new super-structure
		AddSuperVessel (GetWorldVesselServices().CreateStructure(*vessel1,*vessel2,port1,port2,mixmoments)); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	} else if (sv1 && sv2) { // merge sv2 into sv1
		GetWorldVesselServices().Merge(*sv1,*vessel1,port1,*vessel2,port2);
		DelSuperVessel (sv2);
	} else if (sv1) {        // add vessel2 into sv1
		GetWorldVesselServices().Add(*sv1,*vessel1,port1,*vessel2,port2,mixmoments);
	} else {                 // add vessel1 into sv2
		GetWorldVesselServices().Add(*sv2,*vessel2,port2,*vessel1,port1,mixmoments);
	}
}

void PlanetarySystem::UndockVessel (SuperVessel *sv, Vessel *_vessel, int port, double vsep)
{
	GetWorldVesselServices().Detach(*sv,*_vessel,port,vsep);
	if (GetWorldVesselServices().Empty(*sv)) {
		DelSuperVessel(sv);
	}
}

void PlanetarySystem::Update (bool force)
{
	UInt32 i;
	for (i = 0; i < bodies      .size(); i++) bodies      [i]->BeginStateUpdate ();
	for (i = 0; i < stars       .size(); i++) stars       [i]->RelTrueAndBaryState();
	for (i = 0; i < stars       .size(); i++) stars       [i]->AbsTrueState();
	for (i = 0; i < celestials  .size(); i++) celestials  [i]->Update (force);
	for (i = 0; i < vessels     .size(); i++) GetWorldVesselServices().UpdateBodyForces(*vessels[i]);
	for (i = 0; i < supervessels.size(); i++) GetWorldVesselServices().Update(*supervessels[i],force);
	for (i = 0; i < vessels     .size(); i++) GetWorldVesselServices().Update(*vessels[i],force);
}

void PlanetarySystem::FinaliseUpdate ()
{
	UInt32 i;
	for (i = 0; i < bodies.size(); i++) bodies[i]->EndStateUpdate ();
	for (i = 0; i < supervessels.size(); i++) GetWorldVesselServices().PostUpdate(*supervessels[i]);
	for (i = 0; i < vessels.size(); i++) GetWorldVesselServices().PostUpdate(*vessels[i]);
}

void PlanetarySystem::Timejump (const TimeJumpData& jump)
{
	UInt32 i;
	for (i = 0; i < bodies.size(); i++) bodies[i]->BeginStateUpdate ();
	for (i = 0; i < stars.size(); i++) stars[i]->RelTrueAndBaryState();
	for (i = 0; i < stars.size(); i++) stars[i]->AbsTrueState();
	for (i = 0; i < celestials.size(); i++) celestials[i]->Update (true);
	for (i = 0; i < bodies.size(); i++) bodies[i]->EndStateUpdate ();

	for (i = 0; i < vessels.size(); i++)
		GetWorldVesselServices().Timejump(*vessels[i],jump.dt,jump.mode);
}

void PlanetarySystem::InitDeviceObjects ()
{
	for (UInt32 i = 0; i < bodies.size(); i++)
		bodies[i]->InitDeviceObjects();
}

void PlanetarySystem::DestroyDeviceObjects ()
{
	for (UInt32 i = 0; i < bodies.size(); i++)
		bodies[i]->DestroyDeviceObjects();
}

void PlanetarySystem::BroadcastVessel (UInt32 msg, void *data)
{
	for (UInt32 i = 0; i < vessels.size(); i++)
		GetWorldVesselServices().ProcessMessage(*vessels[i],msg,data);
}
void PlanetarySystem::ForEach(int type, std::function<void(const std::filesystem::directory_entry&)> callback) {
    std::error_code ec;
    const auto path=GetSurfaceServices().MarkerDirectory(m_Name.c_str(),m_labelPath.c_str());
    for (const auto& entry:std::filesystem::directory_iterator(path,ec)) {
        if (entry.path().extension().string()==".mkr") callback(entry);
    }
}
