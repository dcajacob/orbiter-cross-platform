// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_RIGID_BODY_SERVICES_H
#define ORBITER_PRODUCTION_RIGID_BODY_SERVICES_H
#include "Rigidbody.h"
#include "TimeData.h"
namespace orbiter::production {
// Queries always address the authoritative production world/reference objects.
// The numerical class has no window, configuration-file or SDK dependency.
class RigidBodyServices {
public:
    virtual ~RigidBodyServices() = default;
    virtual TimeData& Time() = 0;
    virtual const CFG_PHYSICSPRM& Physics() const = 0;
    virtual PlanetarySystem* World() const = 0;
    virtual const Body& Reference(const CelestialBody* body) const = 0;
    virtual Vector ReferencePosition(const CelestialBody* body, double fraction) const = 0;
    virtual double GravityContribution(const CelestialBody* body, const Vector& position) const = 0;
    virtual void ScanGravity(const PlanetarySystem* world, const Vector& position,
        const Body* exclude, GFieldData* data, bool update) const = 0;
    virtual Vector Acceleration(const Vector& position, double fraction,
        const Body* exclude, GFieldData* data) const = 0;
    virtual Vector PerturbedAcceleration(const CelestialBody* reference, const Vector& position,
        double fraction, const Body* exclude, GFieldData* data) const = 0;
    virtual Vector RelativeAcceleration(const Vector& position, const CelestialBody* reference,
        double fraction, const CelestialBody* exclude, GFieldData* data) const = 0;
    virtual Vector NonsphericalAcceleration(const Vector& position, const CelestialBody* reference) const = 0;
    virtual void TraceAllocation(const char* file, int line) = 0;
};
ORBITER_PRODUCTION_API RigidBodyServices* BindRigidBodyServices(RigidBodyServices* services);
ORBITER_PRODUCTION_API RigidBodyServices& GetRigidBodyServices();
}
#endif
