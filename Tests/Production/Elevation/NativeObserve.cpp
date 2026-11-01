// Licensed under the MIT License
// Actual production elevation manager/body/module/resource verification only.
// No native PlanetarySystem, Vessel, camera or replacement world is created.
#include "Celbody.h"
#include "Star.h"
#include "elevmgr.h"
#include "ConfigFile.h"
#include "Production/BodyServices.h"
#include "Production/RigidBodyServices.h"
#include "Production/NativeCelestialServices.h"
#include "Production/NativeElevationServices.h"
#include <algorithm>
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
        if (argc!=8) throw std::runtime_error("Expected config, celestial data, native modules, texture roots, points, interpolation mode and CSV output");
        ResourceResolver config(argv[1]),data(argv[2]),modules(argv[3]),textures(argv[4]);
        const std::string modeArgument=argv[6];
        if (modeArgument!="1" && modeArgument!="2") throw std::runtime_error("Only original interpolation modes 1 and 2 are supported");
        const int mode=modeArgument=="1" ? 1 : 2;
        NativeCelestialServices celestial(config,data,modules);Environment environment(config);Binding bound(environment,celestial);
        // The real Sun configuration furnishes the shared kernel list. Retain
        // the original Sun-before-planets initialization order and lifetime.
        char sunName[]="Sun";Star sun(sunName);
        const auto settings=[&](const CelestialBody& body) {
            std::ifstream input(config.Resolve(std::string(body.Name())+".cfg"));
            int maximumPatch=0;double resolution=0;
            if (!GetItemInt(input,"MaxPatchResolution",maximumPatch) || !GetItemReal(input,"ElevationResolution",resolution))
                throw std::runtime_error("Required stock planet elevation settings are absent");
            // The immutable original observation fixture uses Config defaults:
            // global patch level 21, both file/archive tile sources. This reads
            // the same original per-body settings outside terrain calculations.
            return ElevationSetup{mode,3,std::min(14,std::min(21,maximumPatch)-7),resolution};
        };
        NativeElevationServices terrain(textures,environment.time,settings,
            {"Earth/Archive/Elev.tree","Earth/Archive/Elev_mod.tree","Moon/Archive/Elev.tree","Mars/Archive/Elev.tree"});
        std::ifstream input(argv[5]);input.imbue(std::locale::classic());std::string header;std::getline(input,header);
        if (!header.empty() && header.back()=='\r') header.pop_back();
        if (header!="longitude_deg,latitude_deg") throw std::runtime_error("Invalid elevation point header");
        struct Point {double longitude,latitude;};std::vector<Point> points;Point p;char comma;
        while (input>>p.longitude>>comma>>p.latitude) {
            if (comma!=',' || !std::isfinite(p.longitude) || !std::isfinite(p.latitude)) throw std::runtime_error("Invalid elevation point");
            points.push_back(p);
        }
        if (!input.eof() || points.size()!=85) throw std::runtime_error("Incomplete original elevation queries");
        std::ofstream output(argv[7],std::ios::binary);output.imbue(std::locale::classic());
        output.exceptions(std::ios::badbit|std::ios::failbit);output<<std::setprecision(17)
            <<"mode,body,requested_level,cache,index,longitude_deg,latitude_deg,elevation_m,nx,ny,nz,loaded_level\n";
        for (std::string name:{"Earth","Moon","Mars"}) {
            CelestialBody body(name.data());ElevationManager manager(&body,settings(body),terrain);
            for (int external:{0,1}) {
                std::vector<ElevationTile> cache(external ? 8 : 0);
                for (int requested:{8,12,16,0}) for (std::size_t i=0;i<points.size();++i) {
                    const auto& point=points[i];Vector normal(0,0,0);int level=-1;
                    const double elevation=manager.Elevation(point.latitude*RAD,point.longitude*RAD,
                        requested,external ? &cache : nullptr,&normal,&level);
                    if (!std::isfinite(elevation) || !std::isfinite(normal.x) || !std::isfinite(normal.y) || !std::isfinite(normal.z))
                        throw std::runtime_error("Nonfinite shared production terrain observation");
                    output<<mode<<','<<name<<','<<requested<<','<<external<<','<<i<<','<<point.longitude<<','<<point.latitude<<','
                        <<elevation<<','<<normal.x<<','<<normal.y<<','<<normal.z<<','<<level<<'\n';
                }
            }
        }
        output.close();std::clog<<"Observed actual production elevation, archives and body configuration; no native world or renderer used\n";
        return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
