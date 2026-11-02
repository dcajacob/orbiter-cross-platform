// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#pragma once
#include "PsysCore.h"
#include "Vessel.h"
#include "Camera.h"
#include "WorldMessages.h"
namespace orbiter::production {
// Host callbacks surrounding the original object ownership and callback order.
// The Windows SDK and numerical object layouts do not depend on this interface.
class VesselLifetimeServices {
public:
    virtual ~VesselLifetimeServices()=default;
    virtual PlanetarySystem*& LifetimeWorld()=0;
    virtual Camera*& LifetimeCamera()=0;
    virtual Vessel*& CurrentFocus()=0;
    virtual Vessel*& PreviousFocus()=0;
    virtual void SetView(Body*,int)=0;
    virtual void PaneFocusChanged(Vessel*)=0;
    virtual void ModuleFocusChanged(Vessel*,Vessel*)=0;
    virtual void DialogFocusChanged(Vessel*)=0;
    virtual void ModuleNewVessel(Vessel*)=0;
    virtual void GraphicsNewVessel(Vessel*)=0;
    virtual void DialogNewVessel(Vessel*)=0;
    virtual void ModuleDeleteVessel(Vessel*)=0;
    virtual void GraphicsDeleteVessel(Vessel*)=0;
    virtual void PaneDeleteVessel(Vessel*)=0;
    virtual void DialogDeleteVessel(Vessel*)=0;
    virtual void ConsoleDeleteVessel(Vessel*)=0;
};
inline Vessel* SetFocusObject(VesselLifetimeServices& services,Vessel* vessel,bool setview=true)
{
	auto*& g_focusobj=services.CurrentFocus();
	auto*& g_pfocusobj=services.PreviousFocus();
	if (vessel == g_focusobj) return 0; // nothing to do

	g_pfocusobj = g_focusobj;
	g_focusobj = vessel;

	// Inform pane about focus change
	services.PaneFocusChanged(g_focusobj);

	// switch camera
	if (setview) services.SetView (g_focusobj, 2);

	// vessel and plugin callback
	if (g_pfocusobj) g_pfocusobj->FocusChanged (false, g_focusobj, g_pfocusobj);
	g_focusobj->FocusChanged (true, g_focusobj, g_pfocusobj);

	services.ModuleFocusChanged(g_focusobj,g_pfocusobj);

	services.DialogFocusChanged(vessel);

	return g_pfocusobj;
}
inline void InsertVessel(VesselLifetimeServices& services,Vessel* vessel)
{
	auto*& g_psys=services.LifetimeWorld();
	g_psys->AddVessel (vessel);

	// broadcast vessel creation to plugins
	services.ModuleNewVessel(vessel);

	services.GraphicsNewVessel(vessel);

	services.DialogNewVessel(vessel);
	//if (gclient) gclient->clbkDialogBroadcast (MSG_CREATEVESSEL, vessel);

	vessel->PostCreation();
	vessel->InitSupervessel();
	vessel->ModulePostCreation();
}
inline bool KillVessels(VesselLifetimeServices& services)
{
	auto*& g_psys=services.LifetimeWorld();
	auto*& g_focusobj=services.CurrentFocus();
	auto*& g_pfocusobj=services.PreviousFocus();
	auto*& g_camera=services.LifetimeCamera();
	int i, n = g_psys->nVessel();
	UInt32 j;

	for (i = n-1; i >= 0; i--) {
		if (g_psys->GetVessel(i)->KillPending()) {
			Vessel *vessel = g_psys->GetVessel(i);
			// switch to new focus object
			if (vessel == g_focusobj) {
				if (vessel->ProxyVessel() && !vessel->ProxyVessel()->KillPending()) {
					SetFocusObject (services, vessel->ProxyVessel(), false);
				} else {
					double d, dmin = 1e20;
					Vessel *v, *tgt = 0;
					for (j = 0; j < g_psys->nVessel(); j++) {
						v = g_psys->GetVessel(j);
						if (v->KillPending()) continue;
						if (v != vessel && v->GetEnableFocus()) {
							d = vessel->GPos().dist (v->GPos());
							if (d < dmin) dmin = d, tgt = v;
						}
					}
					if (tgt) SetFocusObject (services, tgt, false);
					else return false; // no focus object available - give up
				}
			}
			if (vessel == g_pfocusobj)
				g_pfocusobj = 0; // clear previous focus (for Ctrl-F3 fast-switching)

			// switch to new camera target
			if (g_camera) {
				if (vessel == g_camera->Target())
					services.SetView(g_focusobj, 1); // this should be handled by Camera::BodyDeleted

				g_camera->BodyDeleted(vessel);
			}

			// broadcast vessel destruction to plugins
			services.ModuleDeleteVessel(vessel);

			services.GraphicsDeleteVessel(vessel);
			// broadcast vessel destruction to all vessels
			g_psys->BroadcastVessel (MSG_KILLVESSEL, vessel);
			// broadcast vessel destruction to all MFDs
			services.PaneDeleteVessel(vessel);
			// broadcast vessel destruction to all open dialogs
			//if (gclient) gclient->clbkDialogBroadcast (MSG_KILLVESSEL, vessel);
			services.DialogDeleteVessel(vessel);
			// echo deletion on console window
			services.ConsoleDeleteVessel(vessel);
			// kill the vessel
			g_psys->DelVessel (vessel);
		}
	}
	return true;
}
}
