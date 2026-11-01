// Licensed under the MIT License
#include "WindowsRigidBodyServices.h"
#include "Orbiter.h"
#include "Psys.h"
#include "Celbody.h"
#include "Log.h"
extern Orbiter* g_pOrbiter;
extern PlanetarySystem* g_psys;
extern TimeData td;
namespace orbiter::production {
namespace {
class WindowsRigidBodyServices final : public RigidBodyServices {
public:
    TimeData& Time() override { return td; }
    const CFG_PHYSICSPRM& Physics() const override { return g_pOrbiter->Cfg()->CfgPhysicsPrm; }
    PlanetarySystem* World() const override { return g_psys; }
    const Body& Reference(const CelestialBody* body) const override { return *body; }
    Vector ReferencePosition(const CelestialBody* body, double fraction) const override
    { return body->InterpolatePosition(fraction); }
    double GravityContribution(const CelestialBody* body, const Vector& position) const override
    { return g_psys->GetGravityContribution(body, position); }
    void ScanGravity(const PlanetarySystem* world, const Vector& position,
        const Body* exclude, GFieldData* data, bool update) const override
    {
        if (update) world->UpdateGFieldSources(&position, exclude, data);
        else world->ScanGFieldSources(&position, exclude, data);
    }
    Vector Acceleration(const Vector& position, double fraction, const Body* exclude, GFieldData* data) const override
    { return g_psys->Gacc_intermediate(position, fraction, exclude, data); }
    Vector PerturbedAcceleration(const CelestialBody* reference, const Vector& position,
        double fraction, const Body* exclude, GFieldData* data) const override
    { return g_psys->Gacc_intermediate_pert(reference, position, fraction, exclude, data); }
    Vector RelativeAcceleration(const Vector& position, const CelestialBody* reference,
        double fraction, const CelestialBody* exclude, GFieldData* data) const override
    { return g_psys->GaccRel(position, reference, fraction, exclude, data); }
    Vector NonsphericalAcceleration(const Vector& position, const CelestialBody* reference) const override
    { return SingleGacc_perturbation(position, reference); }
    void TraceAllocation(const char* file, int line) override
    {
#ifdef TRACE_MEMALLOC
        tracenew(const_cast<char*>(file), line);
#endif
    }
};
}
RigidBodyServices& GetWindowsRigidBodyServices()
{
    static WindowsRigidBodyServices services;
    return services;
}
}
