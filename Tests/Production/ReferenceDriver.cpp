// Copyright (c) Orbiter contributors. Licensed under the MIT License.
// Test-only SDK plugin. It observes S0 at PreStep, before any control is applied.
// It does not replace or reimplement production propagation or vessel callbacks.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <locale>
#include <stdexcept>
#include <string>

namespace {
class Driver final : public oapi::Module {
public:
    explicit Driver(HINSTANCE instance) : Module(instance) { std::srand(0); }
    void clbkSimulationStart(RenderMode) override {
        try {
            samples.open("production-state.csv", std::ios::binary);
            events.open("production-events.csv", std::ios::binary);
            samples.imbue(std::locale::classic()); events.imbue(std::locale::classic());
            samples << std::setprecision(17);
            samples << "step,seconds,mjd,object,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,ground\n";
            events << "step,callback,group,level\n";
            VESSEL *pb = oapiGetVesselInterface(oapiGetVesselByName(const_cast<char *>("PB")));
            if (!pb || std::string(pb->GetClassName()) != "ShuttlePB" || pb->GetPropellantCount() != 1 ||
                pb->GetThrusterCount() == 0 || !oapiGetVesselByName(const_cast<char *>("ISS")))
                throw std::runtime_error("actual ShuttlePB module and ISS are required");
            std::ofstream identity("production-objects.txt", std::ios::binary);
            for (DWORD i = 0; i < oapiGetVesselCount(); ++i) {
                VESSEL *v = oapiGetVesselInterface(oapiGetVesselByIndex(i));
                identity << v->GetName() << ',' << v->GetClassName() << ',' << v->GetMeshCount()
                         << ',' << v->GetThrusterCount() << ',' << v->GetPropellantCount() << '\n';
            }
            identity.close();
            if (!identity) throw std::runtime_error("write production object identities");
            completed = 0;
        } catch (const std::exception &error) { fail(error); }
    }
    void clbkPreStep(double simt, double dt, double mjd) override {
        try {
            if (dt != 1.0 || simt != static_cast<double>(completed) || completed > 6000)
                throw std::runtime_error("production driver requires 6001 one-second application frames");
            events << completed << ",pre,,\n";
            if (completed % 10 == 0) {
                // ModulePreStep sees the preceding fully finalized S0. PostStep
                // runs before FinaliseUpdate and must not be used as a sample.
                for (const char *name : {"Sun", "Earth", "Moon", "ISS", "PB"}) sample(name, simt, mjd);
                samples.flush();
            }
            VESSEL *pb = oapiGetVesselInterface(oapiGetVesselByName(const_cast<char *>("PB")));
            double main = 0, right = 0, pitch = 0;
            std::ifstream mode("production-controls.enabled");
            if (mode.good()) {
                main = completed >= 100 && completed < 160 ? 0.5 : 0;
                right = completed >= 200 && completed < 220 ? 0.25 : 0;
                pitch = completed >= 300 && completed < 305 ? 0.1 : 0;
            }
            pb->SetThrusterGroupLevel(THGROUP_MAIN, main);
            pb->SetThrusterGroupLevel(THGROUP_ATT_RIGHT, right);
            pb->SetThrusterGroupLevel(THGROUP_ATT_PITCHUP, pitch);
            events << completed << ",control,main," << main << '\n'
                   << completed << ",control,right," << right << '\n'
                   << completed << ",control,pitchup," << pitch << '\n';
            if (!samples || !events) throw std::runtime_error("production trace write failure");
        } catch (const std::exception &error) { fail(error); }
    }
    void clbkPostStep(double, double, double) override {
        events << completed << ",post,,\n";
        ++completed;
    }
    void clbkSimulationEnd() override {
        // Stock normal shutdown destroys world objects before this notification.
        // Never dereference a vessel here.
        events << completed << ",end,,\n";
        samples.close(); events.close();
        if (completed != 6001 || samples.fail() || events.fail()) std::exit(1);
    }
private:
    unsigned completed = 0;
    std::ofstream samples, events;
    [[noreturn]] void fail(const std::exception &error) {
        oapiWriteLog(const_cast<char *>(error.what()));
        std::exit(1);
    }
    void sample(const char *name, double simt, double mjd) {
        OBJHANDLE handle = oapiGetObjectByName(const_cast<char *>(name));
        if (!handle) throw std::runtime_error(std::string("missing production object: ") + name);
        VECTOR3 position{}, velocity{}, omega{};
        MATRIX3 rotation{};
        oapiGetGlobalPos(handle, &position); oapiGetGlobalVel(handle, &velocity);
        oapiGetRotationMatrix(handle, &rotation);
        VESSEL *vessel = oapiGetVesselByName(const_cast<char *>(name)) ? oapiGetVesselInterface(handle) : nullptr;
        if (vessel) vessel->GetAngularVel(omega);
        const double values[] = {position.x, position.y, position.z, velocity.x, velocity.y, velocity.z,
            rotation.m11, rotation.m12, rotation.m13, rotation.m21, rotation.m22, rotation.m23,
            rotation.m31, rotation.m32, rotation.m33, omega.x, omega.y, omega.z,
            oapiGetMass(handle), vessel ? vessel->GetFuelMass() : 0};
        samples << completed << ',' << simt << ',' << mjd << ',' << name;
        for (double value : values) {
            if (!std::isfinite(value)) throw std::runtime_error("nonfinite production sample");
            samples << ',' << value;
        }
        samples << ',' << (vessel && vessel->GroundContact() ? 1 : 0) << '\n';
    }
};
Driver *driver = nullptr;
}
DLLCLBK void InitModule(HINSTANCE instance) {
    driver = new Driver(instance);
    oapiRegisterModule(driver);
}
DLLCLBK void ExitModule(HINSTANCE) { delete driver; driver = nullptr; }
