// Licensed under the MIT License
#include "NavigationServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace { NavigationServices* current=nullptr; }
NavigationServices* BindNavigationServices(NavigationServices* services)
{
    auto* previous=current;current=services;return previous;
}
NavigationServices& GetNavigationServices()
{
    if (!current) throw std::logic_error("Production navigation queries are not bound to a world");
    return *current;
}
}
