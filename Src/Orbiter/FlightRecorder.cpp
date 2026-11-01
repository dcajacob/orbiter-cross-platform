// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#define OAPI_IMPLEMENTATION

#include "Orbiter.h"
#include "Vessel.h"
#include "SuperVessel.h"
#include "Celbody.h"
#include "Psys.h"
#include "Camera.h"
#include "Vecmat.h"
#include "PlaybackEd.h"
#include "Log.h"
#include "Pane.h"
#include "State.h"
#include "MenuInfoBar.h"
#include "DlgMgr.h"
#include <fstream>
#include <string>
#include <filesystem>
namespace fs = std::filesystem;

using namespace std;

extern Orbiter *g_pOrbiter;
extern Pane *g_pane;
extern TimeData td;
extern PlanetarySystem *g_psys;
extern Camera *g_camera;
extern char DBG_MSG[256];

#include "Production/VesselRecorderState.h"

// ================================================================
// System event recording/playback
// (implemented in class Orbiter)
// ================================================================

void Orbiter::FRecorder_Reset ()
{
	FRsysname = 0;
	FRsys_stream = 0;
	FReditor = 0;
	frec_sys_simt = -1e10;
	bRecord = bPlayback = false;
}

bool Orbiter::FRecorder_PrepareDir (const char *fname, bool force)
{
	fs::path dir = fs::path("Flights") / fname;
	std::error_code ec;
	auto status = fs::status(dir, ec);

	// don't overwrite existing recording
	if (!ec) {
		if(fs::is_directory(status) && !force) return false;
		fs::remove_all(dir);
	}
	fs::create_directory(dir);

	return true;
}

void Orbiter::FRecorder_Activate (bool active, const char *fname, bool append)
{
	if (bRecord == active) return; // nothing to do
	if (active) {
		if (!append) FRecorder_Reset();
		bRecord = true;
		char cbuf[256];
		sprintf (cbuf, "Flights\\%s\\system.dat", fname);
		if (FRsysname) delete []FRsysname;
		FRsysname = new char[strlen(cbuf)+1]; TRACENEW
		strcpy (FRsysname, cbuf);
	} else {
		bRecord = false;
	}
}

// Save a system event
void Orbiter::FRecorder_SaveEvent (const char *event_type, const char *event)
{
	if (!bRecord) return;
	ofstream ofs(FRsysname, ios::app);
	ofs << setprecision(10) << (td.SimT1-Tofs) << ' ' << event_type << ' ' << event << endl;
}

void Orbiter::FRecorder_OpenPlayback (const char *scname)
{
	int i;
	char cbuf[256];

	if (FRsys_stream) delete FRsys_stream;

	for (i = strlen(scname)-1; i > 0; i--)
		if (scname[i-1] == '\\') break;
	sprintf (cbuf, "Flights\\%s\\system.dat", scname+i);
	if (FRsysname) delete []FRsysname;
	FRsysname = new char[strlen(cbuf)+1]; TRACENEW
	strcpy (FRsysname, cbuf);

	FRsys_stream = new ifstream (cbuf); TRACENEW
	*FRsys_stream >> frec_sys_simt;
	if (!FRsys_stream->good()) {
		delete FRsys_stream;
		FRsys_stream = 0;
	}
}

void Orbiter::FRecorder_SuspendPlayback ()
{
	if (FRsys_stream) {
		delete FRsys_stream;
		FRsys_stream = 0;
	}
}

void Orbiter::FRecorder_RescanPlayback ()
{
	oapi::ScreenAnnotation *sa = SNotePB();
	if (sa) sa->Reset();
	FRsys_stream = new ifstream (FRsysname); TRACENEW
	*FRsys_stream >> frec_sys_simt;
	FRecorder_Play(); // read up to current playback time
}

void Orbiter::FRecorder_ClosePlayback ()
{
	if (FRsys_stream) {
		delete FRsys_stream;
		FRsys_stream = 0;
	}
	if (FReditor) {
		delete FReditor;
		FReditor = 0;
	}
}

void Orbiter::FRecorder_Play ()
{
	// scan system event stream
	while (FRsys_stream && td.SimT1 > frec_sys_simt) {
		char cbuf[1024], *s;
		int i;
		FRsys_stream->getline (cbuf, 1024);
		s = strtok (cbuf, " \t");
		if (s) {
			if (!_strnicmp (s, "TACC", 4)) {
				if (sscanf (s+5, "%lf%lf", &RecordingSpeed, &WarpDelay) < 2)
					WarpDelay = 0.0;
				if (Cfg()->CfgRecPlayPrm.bReplayWarp)
						SetWarpFactor (RecordingSpeed, true, WarpDelay);
			} else if (!_strnicmp (s, "CAMERA", 6)) {
				s = strtok (NULL, " \t\n");
				if (!_strnicmp (s, "PRESET", 6)) {
					sscanf (s+7, "%d", &i);
					g_camera->RecallPreset (i);
				} else if (!_strnicmp (s, "SET", 3)) {
					CameraMode *cm = CameraMode::Create (s+4);
					if (cm) g_camera->SetCMode (cm);
					delete cm;
				}
			} else if (!_strnicmp (s, "FOCUS", 5)) {
				s = strtok (NULL, " \t\n");
				vfocus = g_psys->GetVessel (s, true);
				if (vfocus && Cfg()->CfgRecPlayPrm.bReplayFocus)
					g_pOrbiter->SetFocusObject (vfocus);
			} else if (!_strnicmp (s, "NOTE", 4)) {
				oapi::ScreenAnnotation *sa = SNotePB();
				if (sa) {
					if (!strcmp (s+4, "COL")) {
						double r, g, b;
						sscanf (s+8, "%lf%lf%lf", &r, &g, &b);
						VECTOR3 col = {r,g,b};
						sa->SetColour (col);
					} else if (!strcmp (s+4, "SIZE")) {
						double scale;
						sscanf (s+9, "%lf", &scale);
						sa->SetSize (scale);
					} else if (!strcmp (s+4, "POS")) {
						double x1, y1, x2, y2;
						sscanf (s+8, "%lf%lf%lf%lf", &x1, &y1, &x2, &y2);
						sa->SetPosition (x1, y1, x2, y2);
					} else if (!strcmp (s+4, "OFF")) {
						sa->ClearText();
					} else {
						sa->SetText (s+5);
					}
				}
			} else if (!_strnicmp (s, "JUMPTOTIME", 10)) {
				double jumptime;
				if (sscanf (s+11, "%lf", &jumptime) && jumptime > td.SimT0) {
					double tgtmjd = td.MJD0 + (jumptime-td.SimT0)/86400.0;
					g_pOrbiter->Timejump(tgtmjd, PROP_ORBITAL_FIXEDSURF);
				}
			} else if (!_strnicmp (s, "ENDSESSION", 10)) {
				if (hRenderWnd) PostMessage (hRenderWnd, WM_CLOSE, 0, 0);
			}
		}
		*FRsys_stream >> frec_sys_simt; // read time for next event
		if (!FRsys_stream->good()) {    // end of stream
			delete FRsys_stream;
			FRsys_stream = 0;
		}
	}
}

void Orbiter::FRecorder_ToggleEditor ()
{	
	DlgPlaybackEditor *m_DlgPlaybackEditor = g_pOrbiter->DlgMgr()->EnsureEntry<DlgPlaybackEditor>();
	const char *playbackdir = pState->PlaybackDir();
	m_DlgPlaybackEditor->Load(playbackdir);
}

// ================================================================
// helper functions
