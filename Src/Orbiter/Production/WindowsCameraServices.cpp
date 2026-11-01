// Licensed under the MIT License
#include "WindowsCameraServices.h"
#include "Orbiter.h"
#include "Pane.h"
extern Orbiter* g_pOrbiter;extern Pane* g_pane;extern Vessel* g_focusobj;
namespace orbiter::production {
namespace {
class WindowsCameraServices final:public CameraServices {
public:
    Vessel* Focus() const override {return g_focusobj;}
    Config& Configuration() const override {return *g_pOrbiter->Cfg();}
    void SetFocus(Vessel* vessel) override {g_pOrbiter->SetFocusObject(vessel);}
    void SetFOV(double value) override {g_pOrbiter->SetFOV(value);}
    bool SetPanelMode(int mode) override {return g_pane->SetPanelMode(mode);}
    void SelectPanel(int index) override {g_pane->SelectPanel(index);}
    void SelectVC(int index) override {g_pane->SelectVC(index);}
    std::filesystem::path ScenarioPath(const char* name) const override {return g_pOrbiter->ScnPath(name);}
};
}
CameraServices& GetWindowsCameraServices() {static WindowsCameraServices services;return services;}
}
