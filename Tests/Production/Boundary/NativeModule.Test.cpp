// Licensed under the MIT License
#include "Production/NativeModule.h"
#include "Body.h"
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace orbiter::production;
void require(bool condition,const char* message) { if (!condition) throw std::runtime_error(message); }
struct Services final : BodyServices {
    mutable int creations=0;
    int changes=0;
    bool IsUpdating() const override { ++creations;return false; }
    std::filesystem::path ConfigPath(const char*) override { throw std::runtime_error("Fixture must not load a configuration"); }
    void LoadStatus(const char*,int) override { throw std::runtime_error("Unexpected file load"); }
    void SizeChanged(Body*) override { ++changes; }
    void VisualEvent(Body*,BodyVisual,BodyParameter,BodyContent) override { throw std::runtime_error("Unexpected visual"); }
    void CheckUpdateState(bool valid) override { require(valid,"Invalid fixture state update"); }
};
int main(int argc,char** argv)
{
    try {
        require(argc==10,"Expected valid module, seven invalid fixtures and non-module core library");
        Services services;
        struct Binding { BodyServices* previous;Binding(BodyServices& service):previous(BindBodyServices(&service)) {} ~Binding(){BindBodyServices(previous);} } binding(services);
        Body body(1000,10);
        for (int i=0;i<20;++i) {
            {
                NativeModule module(std::filesystem::absolute(argv[1]),ORBITER_NATIVE_PLUGIN,&body);
                require(module.Info().name=="ProductionBodyBoundaryFixture" && body.Size()==20,
                    "Native module failed explicit initialization against the actual shared Body");
                auto mass=reinterpret_cast<double(ORBITER_NATIVE_CALL*)(void*) noexcept>(module.Symbol("NativeFixtureMass"));
                require(mass(module.Instance())==250,"Module did not construct its production Body");
                bool missing=false;try { module.Symbol("MissingRequiredNativeEntry"); } catch (const std::exception&) {missing=true;}
                require(missing,"Missing module symbol was concealed");
            }
            require(body.Size()==10,"Native shutdown did not run before unloading its library");
        }
        require(services.changes==40 && services.creations>=21,"Native module used a separate engine/service instance");
        for (int i=2;i<argc;++i) {
            const auto changes=services.changes;
            bool rejected=false;
            try { NativeModule invalid(std::filesystem::absolute(argv[i]),ORBITER_NATIVE_PLUGIN,&body); }
            catch (const std::exception& error) { rejected=true;std::cout<<"Rejected fixture "<<i<<": "<<error.what()<<'\n'; }
            require(rejected && body.Size()==10 && changes==services.changes,"Incompatible module initialized or hid its error");
        }
        bool missing=false;
        try {NativeModule invalid(std::filesystem::absolute(argv[1]).parent_path()/"MissingRequiredNativeModule",ORBITER_NATIVE_PLUGIN,&body);}
        catch (const std::exception&) {missing=true;}
        require(missing,"Missing native library was accepted");
        std::cout<<"Native bootstrap: twenty actual module/Body lifetimes, shared services, ABI/build/toolchain/kind checks and explicit failures passed\n";
        return 0;
    } catch (const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
