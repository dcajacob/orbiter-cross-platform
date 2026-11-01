// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Windows application adapters for the unchanged Elements call forms.
#include "Orbiter.h"
#include "Element.h"
#include "Config.h"
#include <fstream>

using namespace std;
extern Orbiter *g_pOrbiter;
extern TimeData td;

Elements::Elements() : Elements(td.MJD_ref) {}
Elements::Elements(double a, double e, double i, double theta,
    double omegab, double L, double epoch)
    : Elements(a, e, i, theta, omegab, L, epoch, td.MJD_ref) {}
Elements::Elements(const Elements &el) : Elements(el, td.MJD_ref) {}

void Elements::Set(double a, double e, double i, double theta,
    double omegab, double L, double epoch)
{ Set(a, e, i, theta, omegab, L, epoch, td.MJD_ref); }
void Elements::Set(const Elements &el) { Set(el, td.MJD_ref); }
void Elements::Setup(double m, double M, double mjd) { Setup(m, M, mjd, td.MJD_ref); }
void Elements::Reset(double a, double e, double i, double theta,
    double omegab, double L, double epoch)
{ Reset(a, e, i, theta, omegab, L, epoch, td.MJD_ref); }
void Elements::Update(Vector &pos, Vector &vel) { Update(pos, vel, td.SimT1); }

Elements::Elements (char *fname)
{
	ifstream ifs (g_pOrbiter->ConfigPath (fname));
	ReadConfiguration(ifs, td.MJD_ref);
}
