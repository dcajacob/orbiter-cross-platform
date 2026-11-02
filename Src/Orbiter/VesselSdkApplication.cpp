// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#define OAPI_IMPLEMENTATION

#include "Astro.h"
#include "Orbiter.h"
#include "Vessel.h"
#include "SuperVessel.h"
#include "Config.h"
#include "Camera.h"
#include "Pane.h"
#include "Production/CockpitServices.h"
#include "Panel2D.h"
#include "Element.h"
#include "Psys.h"
#include "Base.h"
#include "Mfd.h"
#include "Keymap.h"
#include "Log.h"
#include "Dialogs.h"
#include "State.h"
#include "Util.h"
#include "Planet.h"
#include "Mesh.h"
#include "CollisionCore.h"
#include "elevmgr.h"
#include <fstream>
#include <iomanip>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <functional>
#include <stdio.h>
#include <stdlib.h>
#include <string>

using namespace std;

extern Orbiter *g_pOrbiter;
extern Vessel *g_focusobj;
extern Camera *g_camera;
extern Pane *g_pane;
extern Select *g_select;
extern InputBox *g_input;
extern TimeData td;
extern PlanetarySystem *g_psys;
extern bool g_bStateUpdate;

extern char DBG_MSG[256];

#include "Production/CockpitCameraMethods.inc"

DEVMESHHANDLE VESSEL::GetDevMesh (VISHANDLE vis, UINT idx) const
{
	oapi::GraphicsClient *gc = g_pOrbiter->GetGraphicsClient();
	return (gc ? (DEVMESHHANDLE)gc->clbkGetMesh (vis, idx) : NULL);
}

void VESSEL2::clbkDrawHUD (int mode, const HUDPAINTSPEC *hps, HDC hDC)
{
	if (vessel->hudskp && vessel->hudskp->GetDC() == hDC)
		g_pane->DrawDefaultHUD (vessel->hudskp);
}

#include "Production/CockpitPanelMethods.inc"
