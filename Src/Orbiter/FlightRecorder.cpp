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
#include "Production/SystemPlayback.h"

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
	if (!FRsys_stream) return;
	orbiter::production::PlaySystemEvents(*FRsys_stream,frec_sys_simt,td,*g_camera,
		[this](Vessel* v){SetFocusObject(v);},
		[this](double mjd){Timejump(mjd,PROP_ORBITAL_FIXEDSURF);},
		[this]{if(hRenderWnd) PostMessage(hRenderWnd,WM_CLOSE,0,0);});
	if (!FRsys_stream->good()) FRecorder_SuspendPlayback();
}

void Orbiter::FRecorder_ToggleEditor ()
{	
	DlgPlaybackEditor *m_DlgPlaybackEditor = g_pOrbiter->DlgMgr()->EnsureEntry<DlgPlaybackEditor>();
	const char *playbackdir = pState->PlaybackDir();
	m_DlgPlaybackEditor->Load(playbackdir);
}

// ================================================================
// helper functions
