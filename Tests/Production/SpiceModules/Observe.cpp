// Licensed under the MIT License. Test-only driver for actual production modules.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include <array>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <locale>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
class Observer final : public oapi::Module {
public:
    explicit Observer(HINSTANCE instance):Module(instance) {}
    void clbkSimulationStart(RenderMode) override {
        try {
            std::ifstream input("spice-epochs.txt");input.imbue(std::locale::classic());
            std::vector<double> epochs;double epoch;
            while (input>>epoch) epochs.push_back(epoch);
            if (!input.eof() || epochs.empty()) throw std::runtime_error("Invalid explicit SPICE epochs");
            std::ifstream names("spice-bodies.txt");
            std::vector<std::string> bodies;std::string name;
            while (std::getline(names,name)) if (!name.empty()) bodies.push_back(name);
            if (bodies.empty() || bodies.size()!=oapiGetGbodyCount()) throw std::runtime_error("Expected exact production Sol body list");
            std::ofstream out("spice-modules.csv",std::ios::binary);
            out.imbue(std::locale::classic());out<<std::setprecision(17);
            out<<"body,mode,request,index,time,response,p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11\n";
            auto sample=[&](const std::string& body,CELBODY* module,const char* mode,int request,int index,double time,bool fast,bool record) {
                std::array<double,12> values{};
                const int response=fast?module->clbkFastEphemeris(time,request,values.data()):module->clbkEphemeris(time,request,values.data());
                if (!response && !(body=="Sun" && request==(EPHEM_BARYPOS|EPHEM_BARYVEL)))
                    throw std::runtime_error("Production SPICE query returned no ephemeris: "+body+"/"+mode+"/"+std::to_string(request));
                // Unreturned blocks have no API meaning. Record explicit zeros
                // rather than cached/uninitialized contents of unused slots.
                for (int block=0;block<4;++block)
                    if (!(response&(1<<block))) for (int j=0;j<3;++j) values[3*block+j]=0;
                for (double value:values) if (!std::isfinite(value)) throw std::runtime_error("Nonfinite production SPICE state");
                if (record) {
                    out<<body<<','<<mode<<','<<request<<','<<index<<','<<time<<','<<response;
                    for (double value:values) out<<','<<value;
                    out<<'\n';
                }
            };
            for (const auto& body:bodies) {
                OBJHANDLE handle=oapiGetGbodyByName(const_cast<char*>(body.c_str()));
                CELBODY* module=handle?oapiGetCelbodyInterface(handle):nullptr;
                if (!module || !module->bEphemeris()) throw std::runtime_error("Actual production celestial module missing");
                for (int request:{EPHEM_TRUEPOS|EPHEM_TRUEVEL,EPHEM_BARYPOS|EPHEM_BARYVEL,
                    EPHEM_TRUEPOS|EPHEM_TRUEVEL|EPHEM_BARYPOS|EPHEM_BARYVEL}) {
                    for (std::size_t i=0;i<epochs.size();++i) sample(body,module,"slow",request,static_cast<int>(i),epochs[i],false,true);
                    // Production keeps one request mask per interpolation
                    // stream. Reset outside the prior time bracket before
                    // probing another mask; the cache is not keyed by mask.
                    sample(body,module,"reset",request,0,-1000000.0,true,true);
                    for (int i=0;i<=6000;++i) sample(body,module,"forward",request,i,static_cast<double>(i),true,i%100==0);
                    int index=0;
                    for (double time:{6000.0,6000.5,6030.0,0.0,-1.0,120.0,60.0,61.0,3600.0,10.0,0.0,0.125,7200.0})
                        sample(body,module,"jump",request,index++,time,true,true);
                }
            }
            out.close();if (!out) throw std::runtime_error("SPICE observation write failed");
            // This direct callback probe is isolated from world propagation and
            // is not a session teardown/lifecycle acceptance test.
            std::exit(0);
        } catch (const std::exception& error) {oapiWriteLog(const_cast<char*>(error.what()));std::exit(1);}
    }
};
Observer* observer=nullptr;
}
DLLCLBK void InitModule(HINSTANCE instance) {observer=new Observer(instance);oapiRegisterModule(observer);}
DLLCLBK void ExitModule(HINSTANCE) {delete observer;observer=nullptr;}
