// Licensed under the MIT License
#include "Production/WorldOwner.h"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <cstdlib>
using namespace orbiter::production;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
// Opaque lifetime tokens test only the ownership contract. These are not
// simulation objects and cannot satisfy any native production-world gate.
struct Token { int id; };
struct Factory final : WorldFactory {
    int liveCameras=0, liveSystems=0, next=0;
    bool empty=false, failCamera=false, failSystem=false, nullCamera=false, nullSystem=false;
    WorldOwner* owner=nullptr;
    std::vector<std::string> events;
    Camera* CreateCamera() override {
        events.emplace_back("camera.create");
        if (failCamera) throw std::runtime_error("camera allocation failed");
        if (nullCamera) return nullptr;
        ++liveCameras;return reinterpret_cast<Camera*>(new Token{++next});
    }
    PlanetarySystem* CreateSystem(const char* name) override {
        require(name && std::string(name)=="Sol", "World name changed");
        require(liveCameras==1 && owner->Observer(), "World created without its camera");
        events.emplace_back("world.create");
        if (failSystem) throw std::runtime_error("required world asset missing");
        if (nullSystem) return nullptr;
        ++liveSystems;return reinterpret_cast<PlanetarySystem*>(new Token{++next});
    }
    bool HasObjects(const PlanetarySystem* system) const override {
        require(system==owner->System(), "Unpublished world checked");return !empty;
    }
    void DestroyCamera(Camera* camera) noexcept override {
        if (!camera || camera!=owner->Observer() || liveCameras!=1) std::abort();
        events.emplace_back("camera.destroy");--liveCameras;delete reinterpret_cast<Token*>(camera);
    }
    void DestroySystem(PlanetarySystem* system) noexcept override {
        if (!system || system!=owner->System() || liveSystems!=1) std::abort();
        events.emplace_back("world.destroy");--liveSystems;delete reinterpret_cast<Token*>(system);
    }
};
int main()
{
    try {
        Factory factory;
        {
            WorldOwner owner(factory);factory.owner=&owner;
            for (int i=0;i<20;++i) {
                require(owner.Initialize("Sol"), "World initialization failed");
                owner.Reset();owner.Reset();
                require(!owner.System() && !owner.Observer() && !factory.liveSystems && !factory.liveCameras,
                    "World resources survived explicit teardown");
            }
            require(factory.events.size()==80,"Missing lifecycle operation");
            for (std::size_t i=0;i<factory.events.size();i+=4)
                require(std::vector<std::string>(factory.events.begin()+i,factory.events.begin()+i+4)==
                    std::vector<std::string>{"camera.create","world.create","camera.destroy","world.destroy"},
                    "Original world lifetime ordering changed");
            factory.events.clear();
            require(owner.Initialize("Sol") && owner.Initialize("Sol"), "World replacement failed");
            require(factory.events==std::vector<std::string>{"camera.create","world.create","camera.destroy",
                "camera.create","world.destroy","world.create"}, "Original replacement order changed");
            owner.Reset();
            factory.empty=true;require(!owner.Initialize("Sol"),"Empty world was accepted");factory.empty=false;
            for (bool* failure : {&factory.failCamera,&factory.failSystem,&factory.nullCamera,&factory.nullSystem}) {
                require(owner.Initialize("Sol"), "Valid world fixture failed");
                *failure=true;bool rejected=false;
                try { owner.Initialize("Sol"); } catch (const std::exception&) { rejected=true; }
                *failure=false;
                require(rejected && !owner.System() && !owner.Observer() && !factory.liveCameras && !factory.liveSystems,
                    "Partial world initialization leaked resources or hid a failure");
            }
            require(owner.Initialize("Sol"), "Final world fixture failed");
        }
        require(!factory.liveCameras && !factory.liveSystems,"Owner destruction leaked resources");
        std::cout<<"World ownership ordering, replacement, twenty token lifetimes, failure cleanup and teardown passed; no native world was constructed\n";
        return 0;
    } catch (const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
