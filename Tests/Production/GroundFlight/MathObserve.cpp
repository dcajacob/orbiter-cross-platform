// Licensed under the MIT License
// Additional read-only module; the frozen control driver remains unchanged.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "../../../Src/Orbiter/Production/MathObservation.h"
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <locale>
namespace {
class Observer final:public oapi::Module {
    std::ofstream trace;unsigned tick=0;
public:
    explicit Observer(HINSTANCE instance):Module(instance),trace("ground-math.csv",std::ios::binary) {
        trace.imbue(std::locale::classic());trace<<std::setprecision(17);
        orbiter::production::math_observation::Header(trace);
    }
    void clbkPreStep(double seconds,double,double) override {
        auto* vessel=oapiGetVesselInterface(oapiGetVesselByName(const_cast<char*>("PB")));
        auto earth=oapiGetObjectByName(const_cast<char*>("Earth"));VECTOR3 p{};MATRIX3 er{},ob{};
        if(!vessel || !earth)std::exit(1);
        oapiGetGlobalPos(earth,&p);oapiGetRotationMatrix(earth,&er);oapiGetPlanetObliquityMatrix(earth,&ob);
        orbiter::production::math_observation::Row(trace,tick++,seconds,*vessel,p,er,ob,oapiGetPlanetCurrentRotation(earth));
        if(!trace)std::exit(1);
    }
};
Observer* observer=nullptr;
}
DLLCLBK void InitModule(HINSTANCE instance) {observer=new Observer(instance);oapiRegisterModule(observer);}
DLLCLBK void ExitModule(HINSTANCE) {delete observer;observer=nullptr;}
