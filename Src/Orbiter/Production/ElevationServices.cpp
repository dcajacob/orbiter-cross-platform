// Licensed under the MIT License
#include "ElevationServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace { ElevationServices* current=nullptr; }
ElevationServices* BindElevationServices(ElevationServices* services)
{auto* previous=current;current=services;return previous;}
ElevationServices& GetElevationServices()
{
    if (!current) throw std::logic_error("Production elevation services are not bound to a world");
    return *current;
}
}
