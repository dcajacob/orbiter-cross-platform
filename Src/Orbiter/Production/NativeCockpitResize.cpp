// Licensed under the MIT License
// Native window resizing uses the existing cockpit layout and vessel callbacks.
#include "CockpitServices.h"
#include "Pane.h"
#include "Panel2D.h"
#include "Panel.h"
#include "Defpanel.h"
#include "VCockpit.h"
#include "hud.h"
#include "Camera.h"
#include <fstream>
using namespace orbiter::production;

void Pane::ResizeViewport(int width, int height)
{
    if (width <= 0 || height <= 0 || (W == width && H == height)) return;
    auto* camera = CockpitCamera();
    // SelectPanel uses the original internal-camera callbacks. Defer an
    // inactive cockpit until it is visible again, without changing that view.
    if (camera->IsExternal()) return;
    const double phi = camera->Phi(), theta = camera->Theta();
    W = width;
    H = height;
    FreeResources();
    InitResources();
    if (defpanel) {
        const int navmode = defpanel->navdispmode;
        const int rcsmode = defpanel->rcsdispmode;
        delete defpanel;
        defpanel = new DefaultPanel(this, colidx);
        defpanel->SetNavDisplayMode(navmode);
        defpanel->SetRCSDisplayMode(rcsmode);
        for (int i = 0; i < MAXMFD; ++i) RefreshMFD(i);
    } else if (panel2d || panel) {
        // The original vessel callback derives its panel scale from the new
        // viewport and re-registers its own areas and MFD geometry.
        SelectPanel(panel2d ? panel2d->GetId() : panel->GetId());
        camera->SetCockpitDir(phi, theta);
    }
    if (hud) hud->Resize(vcockpit && vcockpit->GetHUDSurf());
    SetHUDColour(colidx, hudIntens, true);
    const auto& evidence = GetNativeRenderContext().evidence;
    if (!evidence.empty()) {
        std::ofstream out(evidence / "cockpit-viewport.json");
        out << "{\"width\":" << W << ",\"height\":" << H << "}\n";
    }
}
