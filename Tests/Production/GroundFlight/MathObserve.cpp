// Licensed under the MIT License
// Additional read-only module; the frozen control driver remains unchanged.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#ifdef ORBITER_INTERNAL_CONTACT_OBSERVATION
#include "Vessel.h"
#include "../../../Src/Orbiter/Production/ContactObservation.h"
#include "../ContactStages/Scheduling.h"
#endif
#include "../../../Src/Orbiter/Production/MathObservation.h"
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <locale>
namespace {
class Observer final:public oapi::Module {
    std::ofstream trace;unsigned tick=0;
#ifdef ORBITER_INTERNAL_CONTACT_OBSERVATION
    std::ofstream contact;
    std::ofstream scheduling;
#endif
public:
    explicit Observer(HINSTANCE instance):Module(instance),trace("ground-math.csv",std::ios::binary) {
        trace.imbue(std::locale::classic());trace<<std::setprecision(17);
        orbiter::production::math_observation::Header(trace);
#ifdef ORBITER_INTERNAL_CONTACT_OBSERVATION
        contact.open("ground-contact.csv",std::ios::binary);contact.imbue(std::locale::classic());contact<<std::setprecision(17);
        orbiter::production::contact_observation::Header(contact);
        scheduling.open("ground-scheduling.csv",std::ios::binary);scheduling.imbue(std::locale::classic());scheduling<<std::setprecision(17);
        contact_scheduling::Header(scheduling);
#endif
    }
    void clbkPreStep(double seconds,double,double) override {
        auto* vessel=oapiGetVesselInterface(oapiGetVesselByName(const_cast<char*>("PB")));
        auto earth=oapiGetObjectByName(const_cast<char*>("Earth"));VECTOR3 p{};MATRIX3 er{},ob{};
        if(!vessel || !earth)std::exit(1);
        oapiGetGlobalPos(earth,&p);oapiGetRotationMatrix(earth,&er);oapiGetPlanetObliquityMatrix(earth,&ob);
        orbiter::production::math_observation::Row(trace,tick,seconds,*vessel,p,er,ob,oapiGetPlanetCurrentRotation(earth));
#ifdef ORBITER_INTERNAL_CONTACT_OBSERVATION
        orbiter::production::contact_observation::Row(contact,tick,seconds,*vessel);
        if(!contact)std::exit(1);
        for(const char* name:{"ISS","PB"}) {
            auto* current=oapiGetVesselInterface(oapiGetVesselByName(const_cast<char*>(name)));
            if(!current)std::exit(1);
            contact_scheduling::Row(scheduling,tick,seconds,*current);
        }
        if(!scheduling)std::exit(1);
#endif
        ++tick;
        if(!trace)std::exit(1);
    }
};
Observer* observer=nullptr;
}
DLLCLBK void InitModule(HINSTANCE instance) {observer=new Observer(instance);oapiRegisterModule(observer);}
DLLCLBK void ExitModule(HINSTANCE) {delete observer;observer=nullptr;}
