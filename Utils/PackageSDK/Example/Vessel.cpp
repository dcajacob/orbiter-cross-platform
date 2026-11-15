// Licensed under the MIT License.
#include "Orbitersdk.h"
#include <fstream>

namespace {
void record(const char* event)
{
    std::ofstream("sdk-vessel.txt", std::ios::app) << event << '\n';
}

class ExampleVessel final : public VESSEL4 {
public:
    ExampleVessel(OBJHANDLE vessel, int model) : VESSEL4(vessel, model) { record("created"); }
    ~ExampleVessel() { record("destroyed"); }

    void clbkSetClassCaps(FILEHANDLE) override
    {
        SetSize(2.0);
        SetEmptyMass(735.0);
        record("configured");
    }

    void clbkPostCreation() override
    {
        if (GetEmptyMass() == 735.0) record("read-back-mass");
    }
};

VESSEL* createVessel(OBJHANDLE handle, int model) { return new ExampleVessel(handle, model); }
void destroyVessel(VESSEL* vessel) { delete static_cast<ExampleVessel*>(vessel); }
}

DLLCLBK VESSEL* ovcInit(OBJHANDLE handle, int model) { return createVessel(handle, model); }
DLLCLBK void ovcExit(VESSEL* vessel) { destroyVessel(vessel); }
