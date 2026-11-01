// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// =============================================================
// class State
// Defines a simulation state at a given time (e.g. for load/save)
// Contains solar system environment, time, focus vessel, scenario help page
// =============================================================

#include <fstream>
#include <iomanip>
#include <string>
#include <stdio.h>
#include "State.h"
#include "AstroMath.h"
#include "ConfigFile.h"
#include "Production/ScenarioColor.h"
#include "Production/Text.h"
#include <cstring>

using namespace std;

// =============================================================

State::State (double defaultMjd)
{
	mjd = mjd0 = defaultMjd;
	solsys = "Sol";         // default name
}

void State::Update (double currentMjd, const char* focusName)
{
	mjd  = currentMjd;
	focus = focusName;
}

bool State::Read (const std::filesystem::path& path, double defaultMjd)
{
	ifstream ifs (path, ios::in);
	if (!ifs) return false;
	return Read(ifs,path,defaultMjd);
}

bool State::Read (std::istream& ifs, const std::filesystem::path& path, double defaultMjd)
{
	if (!ifs) return false;
	const std::string filename = path.string();
	const char* fname = filename.c_str();
	int i;
	scenario = fname;
	for (i = strlen(fname); i >= 0; i--)
		if (fname[i] == '.') break;
	if (i >= 0 && i < 256) scenario[i] = '\0';

	char cbuf[256], *pc;
	double t;
	mjd0 = defaultMjd; // supplied by the host, including its UTC/CT policy
	mjd = mjd0;
	solsys.clear();           // no scenario solsys by default
	context.clear();          // no scenario context by default
	splashscreen.clear();     // no scplashscreen by default
	script.clear();           // no scenario script by default
	scnhelp.clear();          // no scenario help by default
	playback.clear();         // no scenario playback by default
	focus.clear();            // no scenario focus by default

	if (FindLine (ifs, "BEGIN_ENVIRONMENT")) {
		for (;;) {
			if (!ifs.getline (cbuf, 256)) break;
			pc = trim_string (cbuf);
			if (!orbiter::production::ComparePrefix (pc, "END_ENVIRONMENT", sizeof("END_ENVIRONMENT"))) break;
			if (!orbiter::production::ComparePrefix (pc, "Date", 4)) {
				pc = trim_string (pc+4);
				if (!orbiter::production::ComparePrefix (pc, "MJD", 3) && sscanf (pc+3, "%lf", &t) == 1)
					mjd = mjd0 = t;
				else if (!orbiter::production::ComparePrefix (pc, "JD", 2) && sscanf (pc+2, "%lf", &t) == 1)
					mjd = mjd0 = t-2400000.5;
				else if (!orbiter::production::ComparePrefix (pc, "JE", 2) && sscanf (pc+2, "%lf", &t) == 1)
					mjd = mjd0 = Jepoch2MJD (t);
			} else if (!orbiter::production::ComparePrefix (pc, "System", 6)) {
				solsys = trim_string (pc+6);
			} else if (!orbiter::production::ComparePrefix (pc, "Context", 7)) {
				context = trim_string (pc+7);
			} else if (!orbiter::production::ComparePrefix (pc, "SplashScreen", 12)) {
				char color[256];
				int nChar = 0;
				if(sscanf(pc+12, "%255s %n", color, &nChar)==1) {
					splashcolor = GetCSSColor(color);
					splashscreen = trim_string (pc+12+nChar);
				}
			} else if (!orbiter::production::ComparePrefix (pc, "Script", 6)) {
				script = trim_string (pc+6);
			} else if (!orbiter::production::ComparePrefix (pc, "Help", 4)) {
				scnhelp = trim_string (pc+4);
			} else if (!orbiter::production::ComparePrefix (pc, "Playback", 8)) {
				playback = trim_string (pc+8);
			}
		}
	}
	if (FindLine (ifs, "BEGIN_FOCUS")) {
		for (;;) {
			if (!ifs.getline (cbuf, 256)) break;
			pc = trim_string (cbuf);
			if (!orbiter::production::ComparePrefix (pc, "END_FOCUS", sizeof("END_FOCUS"))) break;
			if (!orbiter::production::ComparePrefix (pc, "Ship", 4)) {
				focus = trim_string (pc+4);
			}
		}
	}
	return true;
}

void State::Write (ostream &ofs, const char *desc, int desc_fmt, const char *help) const
{
	const std::string descTypeStr[3] = { "DESC", "HYPERDESC", "URLDESC" };

	ofs.setf (ios::fixed, ios::floatfield);
	ofs.precision (10); // need very high precision MJD output
	if (desc) {
		if (desc_fmt < 0 || desc_fmt > 2) desc_fmt = 0;
		ofs << "BEGIN_" << descTypeStr[desc_fmt] << std::endl;
		for (const char* c = desc; *c; c++)
			if (*c != '\r') ofs << *c; // DOS madness! Get rid of CR so output stream can add it again ... 
		ofs << endl;
		ofs << "END_" << descTypeStr[desc_fmt] << endl << endl;
	}
	ofs << "BEGIN_ENVIRONMENT" << endl;
	ofs << "  System " << solsys << endl;
	ofs << "  Date MJD " << mjd << endl;
	if (context.length())
		ofs << "  Context " << context << endl;
	if (splashscreen.length())
		ofs << "  SplashScreen " << splashscreen << endl;
	if (script.length())
		ofs << "  Script " << script << endl;
	if (scnhelp.length())
		ofs << "  Help " << scnhelp << endl;
	else if (help)
		ofs << "  Help " << help << endl;
	if (playback.length())
		ofs << "  Playback " << playback << endl;
	ofs << "END_ENVIRONMENT" << endl << endl;

	ofs << "BEGIN_FOCUS" << endl;
	ofs << "  Ship " << focus << endl;
	ofs << "END_FOCUS" << endl << endl;
}
