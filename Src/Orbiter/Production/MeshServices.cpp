// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "MeshServices.h"
#include <stdexcept>
namespace orbiter::production {
namespace { MeshServices current; }
MeshServices BindMeshServices(MeshServices services)
{
    if (services.path && (!services.loadTexture || !services.releaseTexture || !services.error || !services.allocation))
        throw std::invalid_argument("Incomplete production mesh services");
    const auto previous=current;
    current=services;
    return previous;
}
const MeshServices& GetMeshServices()
{
    if (!current.path) throw std::logic_error("Production mesh services are not bound to a world");
    return current;
}
}
orbiter::production::UInt64 Str2Crc(const char* str)
{
    orbiter::production::UInt64 crc = 0;
    for (const char* c = str; *c; c++)
        crc += (orbiter::production::UInt64)*c;
    return crc;
}
