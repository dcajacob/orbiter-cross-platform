// Licensed under the MIT License
#ifndef ORBITER_WINDOWS_MESH_SERVICES_H
#define ORBITER_WINDOWS_MESH_SERVICES_H
#include "MeshServices.h"
class Orbiter;
namespace orbiter::production {
MeshServices WindowsMeshServices(Orbiter& application);
}
#endif
