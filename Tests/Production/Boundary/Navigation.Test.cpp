// Licensed under the MIT License
#include "Nav.h"
#include "Production/NavigationServices.h"
#include "Production/NavigationText.h"
#include "Production/RigidBodyServices.h"
#include <cmath>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool value,const char* message) {if (!value) throw std::runtime_error(message);}
struct Transmitter final : Nav {
    int* destroyed;
    explicit Transmitter(float frequency=108,int* count=nullptr):Nav(frequency,1000),destroyed(count) {}
    ~Transmitter() override {if (destroyed) ++*destroyed;}
    void GPos(Vector& position) const override {position.Set(0,0,0);}
};
// Only allocation diagnostics are needed to test the real radio list. World
// queries deliberately fail; these unit transmitters are not stock objects.
struct AllocationHost final : orbiter::production::RigidBodyServices {
    TimeData& Time() override {throw std::logic_error("No world in radio list test");}
    const CFG_PHYSICSPRM& Physics() const override {throw std::logic_error("No physics in radio list test");}
    PlanetarySystem* World() const override {throw std::logic_error("No world in radio list test");}
    const Body& Reference(const CelestialBody*) const override {throw std::logic_error("No bodies in radio list test");}
    Vector ReferencePosition(const CelestialBody*,double) const override {throw std::logic_error("No bodies in radio list test");}
    double GravityContribution(const CelestialBody*,const Vector&) const override {throw std::logic_error("No gravity in radio list test");}
    void ScanGravity(const PlanetarySystem*,const Vector&,const Body*,GFieldData*,bool) const override {throw std::logic_error("No gravity in radio list test");}
    Vector Acceleration(const Vector&,double,const Body*,GFieldData*) const override {throw std::logic_error("No forces in radio list test");}
    Vector PerturbedAcceleration(const CelestialBody*,const Vector&,double,const Body*,GFieldData*) const override {throw std::logic_error("No forces in radio list test");}
    Vector RelativeAcceleration(const Vector&,const CelestialBody*,double,const CelestialBody*,GFieldData*) const override {throw std::logic_error("No forces in radio list test");}
    Vector NonsphericalAcceleration(const Vector&,const CelestialBody*) const override {throw std::logic_error("No forces in radio list test");}
    void TraceAllocation(const char*,int) override {}
};
}
int main()
{
    try {
        using namespace orbiter::production;
        Transmitter transmitter(110.5f);
        require(transmitter.GetStep()==50,"Production radio frequency/channel conversion differs");
        transmitter.SetStep(99);
        require(transmitter.GetFreq()==112.95f,"Production channel/frequency conversion differs");
        require(transmitter.Dist(Vector(300,400,0))==500 && transmitter.FieldStrength(Vector(500,0,0))==4,
            "Production inverse-square radio field differs");
        require(transmitter.InRange(Vector(999,0,0)) && !transmitter.InRange(Vector(1000,0,0)) &&
            transmitter.FieldStrength(Vector(2000,0,0))==.25,"Production radio range boundary differs");
        NavigationData data{};transmitter.GetData(&data);
        require(data.type==TRANSMITTER_NONE && data.ch==99 && data.power==1000000 && data.descr[0]=='\0',
            "Production radio data differs");
        char text[16];std::memset(text,'?',sizeof(text));
        require(NavigationText(text,4,"%s","abcdef")==-1 && std::memcmp(text,"abcd?",5)==0,
            "Legacy radio description truncation differs");
        require(NavigationText(text,16,"%s-%02d","IDS",3)==6 && std::strcmp(text,"IDS-03")==0,
            "Radio description formatting differs");
        bool rejected=false;try {GetNavigationServices();} catch (const std::logic_error&) {rejected=true;}
        require(rejected,"Unbound production world queries silently succeeded");
        AllocationHost host;auto* previous=BindRigidBodyServices(&host);
        int destroyed=0;
        {
            NavManager manager;
            for (int i=39;i>=0;--i) manager.AddNav(new Transmitter(108+float(i)*.05f,&destroyed));
            require(manager.nNav()==40,"Production transmitter list lost entries while growing");
            for (unsigned i=0;i<40;++i) require(manager.GetNav(i)->GetStep()==i,"Production transmitter sort differs");
            manager.Clear();require(destroyed==40 && manager.nNav()==0 && !manager.GetNavlist(),
                "Production transmitter cleanup did not release derived instances exactly once");
            manager.AddNav(new Transmitter(110,&destroyed));
        }
        BindRigidBodyServices(previous);require(destroyed==41,"Production radio list teardown leaked a transmitter");
        std::cout<<"Production Nav: channel/field/range/data, formatting, sorted ownership and explicit unbound failure pass\n";
        return 0;
    } catch (const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
