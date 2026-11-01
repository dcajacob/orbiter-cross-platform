// Licensed under the MIT License
#include "RigidBodyServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace { RigidBodyServices* current = nullptr; }
RigidBodyServices* BindRigidBodyServices(RigidBodyServices* services)
{
    auto* previous = current;
    current = services;
    return previous;
}
RigidBodyServices& GetRigidBodyServices()
{
    if (!current) throw std::logic_error("Production RigidBody services are not bound to a world");
    return *current;
}
}
