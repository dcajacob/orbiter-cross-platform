// Licensed under the MIT License
// Actual production CelestialBody tests. Controlled module callbacks are unit
// fixtures, not native SPICE modules or a substitute stock Solar System.
#include "Celbody.h"
#include "Star.h"
#include "Element.h"
#include "Production/RigidBodyServices.h"
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace orbiter::production;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void close(const Vector& actual, const Vector& expected, double tolerance, const char* message)
{ require(std::isfinite(actual.length()) && (actual-expected).length()<=tolerance,message); }
struct Environment : BodyServices, RigidBodyServices {
    CFG_PHYSICSPRM physics{};
    TimeData time;
    bool updating = false;
    bool IsUpdating() const override { return updating; }
    std::filesystem::path directory;
    std::filesystem::path ConfigPath(const char* name) override { return directory/(std::string(name)+".cfg"); }
    void LoadStatus(const char*, int) override {}
    void SizeChanged(Body*) override { throw std::logic_error("Unexpected size notification"); }
    void VisualEvent(Body*, BodyVisual, BodyParameter, BodyContent) override { throw std::logic_error("No renderer in inertial test"); }
    void CheckUpdateState(bool valid) override { require(valid, "Unavailable body update state"); }
    TimeData& Time() override { return time; }
    const CFG_PHYSICSPRM& Physics() const override { return physics; }
    PlanetarySystem* World() const override { return nullptr; }
    const Body& Reference(const CelestialBody* body) const override { return *body; }
    Vector ReferencePosition(const CelestialBody*, double) const override { throw std::logic_error("No ephemeris in inertial test"); }
    double GravityContribution(const CelestialBody*, const Vector&) const override { throw std::logic_error("No primary in inertial test"); }
    void ScanGravity(const PlanetarySystem* world, const Vector&, const Body*, GFieldData* data, bool) const override
    { require(!world, "Unexpected world identity"); data->ngrav = 0; }
    Vector Acceleration(const Vector&, double, const Body*, GFieldData*) const override { throw std::logic_error("No force integration in celestial class fixture"); }
    Vector PerturbedAcceleration(const CelestialBody*, const Vector&, double, const Body*, GFieldData*) const override
    { throw std::logic_error("No perturbation field in inertial test"); }
    Vector RelativeAcceleration(const Vector&, const CelestialBody*, double, const CelestialBody*, GFieldData*) const override
    { throw std::logic_error("No relative field in inertial test"); }
    Vector NonsphericalAcceleration(const Vector&, const CelestialBody*) const override
    { throw std::logic_error("No nonspherical field in inertial test"); }
    void TraceAllocation(const char*, int) override {} // no diagnostic logger requested by this test
};

struct Host final : Environment, CelestialServices {
    std::map<const CelestialBody*,std::string> modules;
    mutable std::vector<std::string> events;
    int registrations=0, shutdowns=0;
    void RegisterModule(CelestialBody& body,const char* name) override {
        if (std::string(name)!="fixture") throw std::runtime_error("Unsupported fixture module");
        modules.emplace(&body,body.Name()); ++registrations; events.push_back("register:"+std::string(body.Name()));
    }
    void ClearModule(CelestialBody& body) override { if (modules.erase(&body)) ++shutdowns; }
    bool HasModule(const CelestialBody& body) const override { return modules.count(&body)!=0; }
    void InitializeModule(CelestialBody& body,std::ifstream&) override { events.push_back("init:"+modules.at(&body)); }
    bool HasEphemeris(const CelestialBody& body) const override { events.push_back("has:"+modules.at(&body));return true; }
    int Ephemeris(const CelestialBody& body,double mjd,int,double* result) const override {
        const auto name=modules.at(&body); events.push_back("ephemeris:"+name);
        const double seconds=(mjd-time.MJD_ref)*86400.;
        if (name=="Polar") {
            result[0]=result[1]=result[3]=result[4]=0;result[2]=1/AU;result[5]=1/AU;
            return EPHEM_TRUEPOS|EPHEM_TRUEVEL|EPHEM_BARYISTRUE|EPHEM_POLAR;
        }
        std::fill(result,result+12,0);
        const bool root=name=="Root";
        result[0]=(root?100:20)+(root?1:2)*seconds;result[3]=root?1:2;
        return EPHEM_TRUEPOS|EPHEM_TRUEVEL|(root?0:EPHEM_BARYISTRUE);
    }
    int FastEphemeris(const CelestialBody& body,double,int,double*) const override {
        events.push_back("fast:"+modules.at(&body));return 0; // Exercise the actual fallback order.
    }
    std::filesystem::path GravityModelPath(const char* name) const override { return directory/name; }
    void ConfigFailure(const std::filesystem::path&) override { throw std::runtime_error("Missing celestial configuration"); }
    bool RequireGravityModel() const override { return true; }
    void Log(const std::string&) override {}
};
struct Binding {
    BodyServices* body;RigidBodyServices* rigid;CelestialServices* celestial;
    explicit Binding(Host& host):body(BindBodyServices(&host)),rigid(BindRigidBodyServices(&host)),celestial(BindCelestialServices(&host)) {}
    ~Binding(){BindCelestialServices(celestial);BindRigidBodyServices(rigid);BindBodyServices(body);}
};
struct TestBody final : CelestialBody {
    explicit TestBody(char* filename):CelestialBody(filename) {}
    void Prime() { ExternPosition(); }
};
void configuration(Host& host,const char* name,const std::string& fields)
{
    std::ofstream file(host.ConfigPath(name));file.exceptions(std::ios::badbit|std::ios::failbit);
    file<<"Name = "<<name<<"\nInitPos = 0 0 0\nInitVel = 0 0 0\n"<<fields;
}
int main(int argc,char** argv)
{
    try {
        require(argc==2,"Expected scratch directory");
        Host host;host.directory=std::filesystem::path(argv[1])/"celestial-class-fixture";
        std::filesystem::create_directories(host.directory);
        host.time.Reset(MJD2000);Binding binding(host);
        {
            std::istringstream input("Epoch = 2010\nSemiMajorAxis = 10000000\nEccentricity = 0.2\nInclination = 0.3\nLongAscNode = 0.4\nLongPerihelion = 0.5\nMeanLongitude = 0.6\n");
            Elements parsed(input,MJD2000+10),expected(10000000,.2,.3,.4,.5,.6,Jepoch2MJD(2010),MJD2000+10);
            parsed.Setup(1000,5.972e24,MJD2000+10,MJD2000+10);
            expected.Setup(1000,5.972e24,MJD2000+10,MJD2000+10);
            Vector p,v,ep,ev;parsed.PosVel(p,v,1000);expected.PosVel(ep,ev,1000);
            close(p,ep,1e-6,"Configuration element epoch/position mapping");close(v,ev,1e-8,"Configuration element velocity mapping");
        }
        configuration(host,"Primary","Mass = 5.972e24\nSize = 6378000\nSidRotPeriod = 1000\n");
        configuration(host,"Orbiter","Mass = 1000\nSize = 1\nHasElements = TRUE\nEllipticOrbit = TRUE\nSemiMajorAxis = 7000000\n");
        {
            char p[]="Primary",o[]="Orbiter";Star primary(p);TestBody orbiter(o);
            orbiter.Setup();orbiter.Attach(&primary);
            require(primary.Type()==OBJTP_STAR,"Production star type changed");
            require(primary.nSecondary()==1 && primary.Secondary(0)==&orbiter && orbiter.Primary()==&primary,
                    "Production hierarchy did not retain its authoritative objects");
            Vector pos,vel;require(orbiter.PosVelAtTime(1000,&pos,&vel),"Configured conic was unavailable");
            const double rate=std::sqrt(Ggrav*(primary.Mass()+orbiter.Mass())/std::pow(7000000.,3));
            close(pos,Vector(7000000*std::cos(rate*1000),0,7000000*std::sin(rate*1000)),.01,"Circular celestial position");
            close(vel,Vector(-7000000*rate*std::sin(rate*1000),0,7000000*rate*std::cos(rate*1000)),1e-5,"Circular celestial velocity");
            Matrix rotation;primary.GetRotation(250,rotation);
            close(mul(rotation,Vector(1,0,0)),Vector(0,0,1),1e-12,"Sidereal rotation convention changed");
        }
        configuration(host,"Root","Mass = 10\nSize = 1\nModule = fixture\n");
        configuration(host,"Child","Mass = 1\nSize = 1\nModule = fixture\n");
        {
            char r[]="Root",c[]="Child";Star root(r);TestBody child(c);
            child.Setup();child.Attach(&root);
            require(host.events==std::vector<std::string>{"register:Root","init:Root","has:Root","fast:Root","ephemeris:Root","register:Child","init:Child","has:Child","fast:Child","ephemeris:Child"} && host.registrations==2,
                    "Unexpected module initialization");
            host.events.clear();host.time.SetFixedStep(1);host.time.BeginStep(1,true);host.updating=true;
            root.BeginStateUpdate();child.BeginStateUpdate();root.RelTrueAndBaryState();root.AbsTrueState();
            require(host.events==std::vector<std::string>{"fast:Child","ephemeris:Child","fast:Root","ephemeris:Root"},
                    "Ephemeris recursion/fallback order changed");
            root.Update(false);child.Update(false);
            const auto intermediate=child.InterpolateState(.5);
            close(intermediate.pos,Vector(121.5,0,0),.01,"Production hierarchical state interpolation");
            root.EndStateUpdate();child.EndStateUpdate();host.time.EndStep(true);host.updating=false;
            close(root.GPos(),Vector(101,0,0),.01,"Root true state");close(child.GPos(),Vector(123,0,0),.01,"Child global true state");
            close(root.Barycentre(),Vector(103,0,0),.01,"Production barycentre calculation");
            close(child.GVel(),Vector(3,0,0),1e-5,"Child global velocity");
        }
        configuration(host,"Polar","Mass = 1\nSize = 1\nModule = fixture\n");
        {
            char p[]="Polar";TestBody polar(p);polar.Setup();polar.Prime();
            close(polar.GPos(),Vector(1,0,0),1e-12,"Polar AU/SI conversion");close(polar.GVel(),Vector(1,0,0),1e-12,"Polar radial velocity conversion");
        }
        configuration(host,"BadGravity","Mass = 1\nSize = 1\nModule = fixture\nGravModelPath = missing.tab\nGravCoeffCutoff = 32\n");
        bool rejected=false;try {char bad[]="BadGravity";TestBody invalid(bad);}catch(const std::exception&){rejected=true;}
        require(rejected && host.modules.empty() && host.registrations==host.shutdowns,"Failed initialization leaked a registered module");
        rejected=false;try{char missing[]="Missing";TestBody invalid(missing);}catch(const std::exception&){rejected=true;}
        require(rejected,"Missing celestial configuration was accepted");
        std::cout<<"Actual CelestialBody: conic/rotation, hierarchy/barycentre, ephemeris order/conversion and failure cleanup passed\n";
        return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
