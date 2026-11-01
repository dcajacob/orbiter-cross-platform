// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// Implementation of class PlanetarySystem

#include "Astro.h"
#include <fstream>
#include <stdio.h>
#include <string.h>
#include <algorithm>

#include "Config.h"
#include "Psys.h"
#include "Base.h"
#include "Star.h"
#include "Planet.h"
#include "PhysicsCore.h"
#include "TimeData.h"
#include "Element.h"
#include "Vessel.h"
#include "SuperVessel.h"
#include "Log.h"

using namespace std;

extern TimeData td;
extern bool g_bForceUpdate;
extern char DBG_MSG[256];

PlanetarySystem::PlanetarySystem (char *fname, const Config* config, OutputLoadStatusCallback outputLoadStatus, void* callbackContext)
{
	Read (fname, config, outputLoadStatus, callbackContext);
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
		DelBody(vessels.back());
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

	g_bForceUpdate = true;

	//Supervessels are not stored in 'bodies' so we have to take care of them manually
	for (size_t i = 0; i < supervessels.size(); ++i) {
		delete supervessels[i];
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
			if (!_stricmp (pc, "END_SHIPS")) break;
			for (pd = pc; *pd != '\0' && *pd != ':'; pd++);
			if (*pd) *pd++ = '\0';
			else pd = 0;
			AddVessel (new Vessel (this, pc, pd, ifs)); TRACENEW
		}
	}
}

void PlanetarySystem::PostCreation ()
{
	for (size_t i = 0; i < vessels.size(); ++i) vessels[i]->PostCreation();
	for (size_t i = 0; i < vessels.size(); ++i) vessels[i]->InitSupervessel();
	for (size_t i = 0; i < vessels.size(); ++i) vessels[i]->ModulePostCreation();
}

void PlanetarySystem::Write (ostream &os)
{
	os << "BEGIN_SHIPS" << endl;
	for (size_t i = 0; i < vessels.size(); ++i)
		vessels[i]->Write (os);
	os << "END_SHIPS" << endl;
}

Body *PlanetarySystem::GetObj (const char *name, bool ignorecase)
{
	for (DWORD i = 0; i < bodies.size(); i++)
		if (!StrComp (bodies[i]->Name(), name, ignorecase)) return bodies[i];
	return 0;
}

CelestialBody *PlanetarySystem::GetGravObj (const char *name, bool ignorecase) const
{
	for (DWORD i = 0; i < celestials.size(); i++)
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
	for (DWORD i = 0; i < vessels.size(); i++)
		if (!StrComp (vessels[i]->Name(), name, ignorecase)) return vessels[i];
	return 0;
}

bool PlanetarySystem::isObject (const Body *obj) const
{
	for (DWORD i = 0; i < bodies.size(); i++)
		if (bodies[i] == obj) return true;
	return false;
}

bool PlanetarySystem::isVessel (const Vessel *v) const
{
	for (DWORD i = 0; i < vessels.size(); i++)
		if (vessels[i] == v) return true;
	return false;
}

orbiter::production::UInt32 PlanetarySystem::nBase(const Planet *planet) const { return planet->nBase(); }
Base *PlanetarySystem::GetBase (const Planet *planet, orbiter::production::UInt32 i) { return planet->GetBase(i); }

Base *PlanetarySystem::GetBase (const Planet *planet, const char *name, bool ignorecase)
{
	for (DWORD i = 0; i < planet->nBase(); i++)
		if (!StrComp (planet->GetBase(i)->Name(), name, ignorecase))
			return planet->GetBase(i);
	return 0;
}

Base *PlanetarySystem::GetBase (const char *name, bool ignorecase)
{
	for (DWORD i = 0; i < celestials.size(); i++) {
		if (celestials[i]->Type() != OBJTP_PLANET) continue;
		Planet *planet = (Planet*)celestials[i];
		Base *base = GetBase (planet, name, ignorecase);
		if (base) return base;
	}
	return 0;
}

void PlanetarySystem::OptionChanged(DWORD cat, DWORD item)
{
	for (size_t i = 0; i < vessels.size(); i++)
		vessels[i]->OptionChanged(cat, item);
}

bool PlanetarySystem::Read (char *fname, const Config* config, OutputLoadStatusCallback outputLoadStatus, void* callbackContext)
{
	int i;
	DWORD j;
	char cbuf[256], label[128];
	
	ifstream ifs (config->ConfigPath(fname));
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
		AddStar (new Star (cbuf)); TRACENEW
	}

	// read planets
	for (i = 0;; i++) {
		sprintf (label, "Planet%d", i+1);
		if (!GetItemString (ifs, label, cbuf)) break;
		OutputLoadStatus (cbuf, outputLoadStatus, callbackContext);
		Planet *planet = new Planet (cbuf); TRACENEW
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
	oapi::GraphicsClient::LABELLIST* ll;
	int idx = 0;
	ForEach(FILETYPE_MARKER, [&](const fs::directory_entry& entry) {
		// open marker file
		ifstream ulf(entry.path());
		// read label header
		if (bScanHeaders) {
			oapi::GraphicsClient::LABELLIST list;
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
					if (!ulf.getline(cbuf, 256) || !_strnicmp(cbuf, "END_HEADER", 10)) break;
					sscanf(cbuf, "%s %s", item, value);
					if (!_stricmp(item, "InitialState")) {
						if (!_stricmp(value, "on")) list.active = true;
					}
					else if (!_stricmp(item, "ColourIdx")) {
						int col;
						sscanf(value, "%d", &col);
						list.colour = max(0, min(5, col));
					}
					else if (!_stricmp(item, "ShapeIdx")) {
						int shape;
						sscanf(value, "%d", &shape);
						list.shape = max(0, min(6, shape));
					}
					else if (!_stricmp(item, "Size")) {
						float size;
						sscanf(value, "%f", &size);
						list.size = max(0.1f, min(2.0f, size));
					}
					else if (!_stricmp(item, "DistanceFactor")) {
						float distfac;
						sscanf(value, "%f", &distfac);
						list.distfac = max(1e-5f, min(1e3f, distfac));
					}
					else if (!_stricmp(item, "Frame")) {
						if (_stricmp(value, "Ecliptic"))
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
				oapi::GraphicsClient::LABELSPEC ls;
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
		Planet *moon = new Planet (name); TRACENEW
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
	AddBody (_vessel); // register in general list
	g_bForceUpdate = true;
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

	DelBody (_vessel); //DelBody takes care of freeing the vessel
	std::iter_swap(vessels.begin() + i, vessels.end() - 1);
	vessels.pop_back();

	g_bForceUpdate = true;
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

	delete supervessels[i];

	//Note that supervesslels unlike other bodies are NOT also present in the 'bodies'
	std::iter_swap(supervessels.begin() + i, supervessels.end() - 1);
	supervessels.pop_back();

	return false;
}

void PlanetarySystem::DockVessels (Vessel *vessel1, Vessel *vessel2, int port1, int port2, bool mixmoments)
{
	// if the vessels are already complex structures, store a reference to
	// the superstructures so we can remove them after merging
	SuperVessel *sv1 = vessel1->SuperStruct();
	SuperVessel *sv2 = vessel2->SuperStruct();

	if (!sv1 && !sv2) {    // create a new super-structure
		AddSuperVessel (new SuperVessel (vessel1, vessel2, port1, port2, mixmoments)); TRACENEW
	} else if (sv1 && sv2) { // merge sv2 into sv1
		sv1->Merge (vessel1, port1, vessel2, port2);
		DelSuperVessel (sv2);
	} else if (sv1) {        // add vessel2 into sv1
		sv1->Add (vessel1, port1, vessel2, port2, mixmoments);
	} else {                 // add vessel1 into sv2
		sv2->Add (vessel2, port2, vessel1, port1, mixmoments);
	}
}

void PlanetarySystem::UndockVessel (SuperVessel *sv, Vessel *_vessel, int port, double vsep)
{
	sv->Detach (_vessel, port, vsep);
	if (!sv->nVessel()) {
		DelSuperVessel(sv);
	}
}

void PlanetarySystem::Update (bool force)
{
	DWORD i;
	for (i = 0; i < bodies      .size(); i++) bodies      [i]->BeginStateUpdate ();
	for (i = 0; i < stars       .size(); i++) stars       [i]->RelTrueAndBaryState();
	for (i = 0; i < stars       .size(); i++) stars       [i]->AbsTrueState();
	for (i = 0; i < celestials  .size(); i++) celestials  [i]->Update (force);
	for (i = 0; i < vessels     .size(); i++) vessels     [i]->UpdateBodyForces ();
	for (i = 0; i < supervessels.size(); i++) supervessels[i]->Update (force);
	for (i = 0; i < vessels     .size(); i++) vessels     [i]->Update (force);
}

void PlanetarySystem::FinaliseUpdate ()
{
	DWORD i;
	for (i = 0; i < bodies.size(); i++) bodies[i]->EndStateUpdate ();
	for (i = 0; i < supervessels.size(); i++) supervessels[i]->PostUpdate ();
	for (i = 0; i < vessels.size(); i++) vessels[i]->PostUpdate ();
}

void PlanetarySystem::Timejump (const TimeJumpData& jump)
{
	DWORD i;
	for (i = 0; i < bodies.size(); i++) bodies[i]->BeginStateUpdate ();
	for (i = 0; i < stars.size(); i++) stars[i]->RelTrueAndBaryState();
	for (i = 0; i < stars.size(); i++) stars[i]->AbsTrueState();
	for (i = 0; i < celestials.size(); i++) celestials[i]->Update (true);
	for (i = 0; i < bodies.size(); i++) bodies[i]->EndStateUpdate ();

	for (i = 0; i < vessels.size(); i++)
		vessels[i]->Timejump(jump.dt, jump.mode);
}

void PlanetarySystem::InitDeviceObjects ()
{
	for (DWORD i = 0; i < bodies.size(); i++)
		bodies[i]->InitDeviceObjects();
}

void PlanetarySystem::DestroyDeviceObjects ()
{
	for (DWORD i = 0; i < bodies.size(); i++)
		bodies[i]->DestroyDeviceObjects();
}

void PlanetarySystem::BroadcastVessel (DWORD msg, void *data)
{
	for (DWORD i = 0; i < vessels.size(); i++)
		vessels[i]->ProcessMessage (msg, data);
}