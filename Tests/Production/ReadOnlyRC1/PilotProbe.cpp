// Hosted test module. Use Orbiter's scenario writer and verify the running focus vessel.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include <fstream>
#include <cstdlib>
#include <cstring>
class PilotProbe final : public oapi::Module {
public:
    using Module::Module;
    unsigned frames=0;
    void clbkPostStep(double, double, double) override {
        ++frames;
        const char *path=std::getenv("ORBITER_GUI_RECEIPT");
        const char *phase=std::getenv("ORBITER_GUI_PHASE");
        auto vessel=oapiGetFocusInterface();
        if (!path || !phase || !vessel) return;
        if (frames>36 && frames%8==0 && std::ifstream(std::string(path)+".close")) {
            if (HWND hwnd=FindWindowA("Orbiter Render Window",nullptr)) PostMessageW(hwnd,WM_CLOSE,0,0);
            return;
        }
        if (frames!=36) return;
        std::ofstream output(std::string(path)+".window.txt");
        output << vessel->GetName() << ":" << vessel->GetClassName() << "\n";
        if (!std::strcmp(phase,"first"))
            output << "saved=" << oapiSaveScenario("Quicksave\\Pilot read-only flight","Saved by the installed Orbiter engine") << "\n";
    }
};
PilotProbe *probe;
DLLCLBK void InitModule(HINSTANCE instance) {probe=new PilotProbe(instance);oapiRegisterModule(probe);}
DLLCLBK void ExitModule(HINSTANCE) {delete probe;}
