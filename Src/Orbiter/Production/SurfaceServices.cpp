// Licensed under the MIT License
#include "SurfaceServices.h"
#include "MeshServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace { SurfaceServices* bound=nullptr; }
SurfaceServices* BindSurfaceServices(SurfaceServices* services)
{auto* previous=bound;bound=services;return previous;}
SurfaceServices& GetSurfaceServices()
{
    if (!bound) throw std::logic_error("Production surface services are not bound to a world");
    return *bound;
}
void TraceSurfaceAllocation(const char* file,int line)
{
    const auto& services=GetMeshServices();
    if (services.allocation) services.allocation(services.context,file,line);
}
}
