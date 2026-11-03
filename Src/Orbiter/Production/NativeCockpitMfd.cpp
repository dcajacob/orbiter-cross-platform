// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "CockpitServices.h"
#include "Vessel.h"
#include "Pane.h"
#include "Mfd.h"
using namespace orbiter::production;

void oapiOpenMFD (int mode, int mfd)
{
	if (auto* pane = GetNativeRenderContext().cockpitPane) pane->OpenMFD (mfd, mode);
}

void oapiToggleMFD_on (int mfd)
{
	if (auto* pane = GetNativeRenderContext().cockpitPane) pane->ToggleMFD_on (mfd);
}

int oapiRegisterMFDMode (MFDMODESPECEX &spec)
{
	return Instrument::RegisterUserMode (&spec);
}

bool oapiUnregisterMFDMode (int mode)
{
	return Instrument::UnregisterUserMode (mode);
}

int oapiGetMFDMode (int mfd)
{
	return (CockpitPane()->MFD(mfd) ? CockpitPane()->MFD(mfd)->Type() : MFD_NONE);
}

double oapiSetMFDRefreshIntervalMultiplier (int mfd, double multiplier)
{
	return CockpitPane()->SetMFDRefreshIntervalMultiplier (mfd, multiplier);
}

int oapiBroadcastMFDMessage (int mfdmode, int msg, void *data)
{
	return CockpitPane()->BroadcastMFDMessage (mfdmode, msg, data);
}

int oapiSendMFDKey (int mfd, oapi::UInt32 key)
{
	return CockpitPane()->MFDConsumeKeyBuffered (mfd, key);
}

void oapiRefreshMFDButtons (int mfd, OBJHANDLE hVessel)
{
	if (!hVessel || (Vessel*)hVessel == CockpitFocus())
		CockpitFocus()->MFDchanged (mfd, MFD_REFRESHBUTTONS);
}

bool oapiProcessMFDButton (int mfd, int bt, int event)
{
	Instrument *MFD = CockpitPane()->MFD(mfd);
	if (MFD) return MFD->ConsumeButton (bt, event);
	else     return false;
}

const char *oapiMFDButtonLabel (int mfd, int bt)
{
	return (CockpitPane()->MFD(mfd) ? CockpitPane()->MFD(mfd)->ButtonLabel(bt) : 0);
}

void oapiRegisterMFD (int mfd, const MFDSPEC &spec)
{
	CockpitPane()->RegisterMFD (mfd, spec);
}

void oapiDisableMFDMode (int mode)
{
	Instrument::DisableMode (mode);
	if (auto* pane = GetNativeRenderContext().cockpitPane)
		pane->MFDModeDisabled (mode);
}

int oapiGetMFDModeSpecEx (char *name, MFDMODESPECEX **spec)
{
	return Instrument::ModeFromName (name, spec);
}

void oapiVCRegisterMFD (int mfd, const VCMFDSPEC *spec)
{
	CockpitPane()->RegisterVCMFD (mfd, spec);
}

void oapiVCRegisterHUD (const VCHUDSPEC *spec)
{
	if (auto* pane = GetNativeRenderContext().cockpitPane)
		pane->RegisterVCHUD (spec);
}
