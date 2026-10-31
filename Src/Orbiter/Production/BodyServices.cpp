// Licensed under the MIT License
#include "BodyServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace { BodyServices* current = nullptr; }
BodyServices* BindBodyServices(BodyServices* services)
{
    auto* previous = current;
    current = services;
    return previous;
}
BodyServices& GetBodyServices()
{
    if (!current) throw std::logic_error("Production Body services are not bound to a world");
    return *current;
}
}
