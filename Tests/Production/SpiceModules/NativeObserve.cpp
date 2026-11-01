// Licensed under the MIT License
// Direct real-module verification, not a replacement production world/session.
#include "Celbody.h"
#include "Production/BodyServices.h"
#include "Production/RigidBodyServices.h"
#include "Production/NativeCelestialServices.h"
#include "ConfigFile.h"
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <locale>
#include <memory>
#include <stdexcept>
#include <vector>
using namespace orbiter::production;
namespace {
struct Environment final : BodyServices,RigidBodyServices {
    const ResourceResolver& config;
    TimeData time;
    CFG_PHYSICSPRM physics{};
    explicit Environment(const ResourceResolver& c):config(c) {time.Reset(51982.5);}
    bool IsUpdating() const override {return false;}
    std::filesystem::path ConfigPath(const char* name) override {
        std::string path=name;if (std::filesystem::path(path).extension().empty()) path+=".cfg";
        return config.Resolve(path);
    }
    void LoadStatus(const char* path,int) override {std::clog<<"Loading production celestial config: "<<path<<'\n';}
    void SizeChanged(Body*) override {++sizeNotifications;}
    void VisualEvent(Body*,BodyVisual,BodyParameter,BodyContent) override {throw std::logic_error("No renderer in direct module probe");}
    void CheckUpdateState(bool valid) override {if (!valid) throw std::logic_error("Invalid production update state");}
    TimeData& Time() override {return time;}
    const CFG_PHYSICSPRM& Physics() const override {return physics;}
    PlanetarySystem* World() const override {return nullptr;}
    const Body& Reference(const CelestialBody* body) const override {return *body;}
    Vector ReferencePosition(const CelestialBody*,double) const override {throw std::logic_error("No world propagation in direct module probe");}
    double GravityContribution(const CelestialBody*,const Vector&) const override {throw std::logic_error("No world gravity in direct module probe");}
    void ScanGravity(const PlanetarySystem*,const Vector&,const Body*,GFieldData*,bool) const override {throw std::logic_error("No world gravity in direct module probe");}
    Vector Acceleration(const Vector&,double,const Body*,GFieldData*) const override {throw std::logic_error("No world gravity in direct module probe");}
    Vector PerturbedAcceleration(const CelestialBody*,const Vector&,double,const Body*,GFieldData*) const override {throw std::logic_error("No world gravity in direct module probe");}
    Vector RelativeAcceleration(const Vector&,const CelestialBody*,double,const CelestialBody*,GFieldData*) const override {throw std::logic_error("No world gravity in direct module probe");}
    Vector NonsphericalAcceleration(const Vector&,const CelestialBody*) const override {throw std::logic_error("No world gravity in direct module probe");}
    void TraceAllocation(const char*,int) override {++allocations;}
    unsigned sizeNotifications=0,allocations=0;
};
struct Binding {
    BodyServices* oldBody;
    RigidBodyServices* oldRigid;
    CelestialServices* oldCelestial;
    Binding(Environment& environment,NativeCelestialServices& celestial):oldBody(BindBodyServices(&environment)),
        oldRigid(BindRigidBodyServices(&environment)),oldCelestial(BindCelestialServices(&celestial)) {}
    ~Binding() {BindCelestialServices(oldCelestial);BindRigidBodyServices(oldRigid);BindBodyServices(oldBody);}
};
}
int main(int argc,char** argv)
{
    try {
        if (argc!=7) throw std::runtime_error("Expected config root, data root, native module root, body list, epochs and CSV output");
        ResourceResolver config(argv[1]),data(argv[2]),modules(argv[3]);
        NativeCelestialServices services(config,data,modules);Environment environment(config);Binding bound(environment,services);
        std::ifstream input(argv[5]);input.imbue(std::locale::classic());
        std::vector<double> epochs;double epoch;
        while (input>>epoch) epochs.push_back(epoch);
        if (!input.eof() || epochs.empty()) throw std::runtime_error("Invalid explicit epochs");
        std::ifstream names(argv[4]);std::vector<std::string> bodies;std::string name;
        while (std::getline(names,name)) {if (!name.empty() && name.back()=='\r') name.pop_back();if (!name.empty()) bodies.push_back(name);}
        if (bodies.size()!=41) throw std::runtime_error("Expected full stock Sol celestial module list");
        std::vector<std::unique_ptr<CelestialBody>> objects;
        for (auto& body:bodies) objects.push_back(std::make_unique<CelestialBody>(body.data()));
        std::ofstream out(argv[6],std::ios::binary);out.imbue(std::locale::classic());out<<std::setprecision(17);
        if (!out) throw std::runtime_error("Cannot open module CSV");
        out<<"body,mode,request,index,time,response,p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11\n";
        auto sample=[&](std::size_t object,const char* mode,int request,int index,double time,bool fast,bool record) {
            auto& module=services.Interface(*objects[object]);std::array<double,12> values{};
            const int response=fast?module.clbkFastEphemeris(time,request,values.data()):module.clbkEphemeris(time,request,values.data());
            if (!response && !(bodies[object]=="Sun" && request==12)) throw std::runtime_error("Native production SPICE returned no ephemeris");
            for (int block=0;block<4;++block) if (!(response&(1<<block))) for (int j=0;j<3;++j) values[3*block+j]=0;
            for (double value:values) if (!std::isfinite(value)) throw std::runtime_error("Nonfinite native SPICE result");
            if (record) {
                out<<bodies[object]<<','<<mode<<','<<request<<','<<index<<','<<time<<','<<response;
                for (double value:values) out<<','<<value;
                out<<'\n';
            }
        };
        for (std::size_t object=0;object<objects.size();++object) for (int request:{3,12,15}) {
            for (std::size_t i=0;i<epochs.size();++i) sample(object,"slow",request,static_cast<int>(i),epochs[i],false,true);
            sample(object,"reset",request,0,-1000000.,true,true);
            for (int i=0;i<=6000;++i) sample(object,"forward",request,i,static_cast<double>(i),true,i%100==0);
            int index=0;
            for (double time:{6000.,6000.5,6030.,0.,-1.,120.,60.,61.,3600.,10.,0.,0.125,7200.})
                sample(object,"jump",request,index++,time,true,true);
        }
        out.close();if (!out) throw std::runtime_error("Module CSV write failed");
        std::clog<<"Observed all 41 actual native SPICE module instances; no replacement ephemeris or world used\n";
        return 0;
    } catch (const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
