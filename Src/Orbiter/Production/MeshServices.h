// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_MESH_SERVICES_H
#define ORBITER_PRODUCTION_MESH_SERVICES_H
#include "Export.h"
#include "CoreTypes.h"
#include <filesystem>

namespace orbiter::production {
using MeshSurface = void*;
// A copied, non-owning callback table: its host/context must outlive all meshes.
// Graphics resources belong to the host; a headless host returns null handles
// while retaining/validating the declared CPU texture sources.
struct MeshServices {
    void* context = nullptr;
    std::filesystem::path (*path)(void*, const char*) = nullptr;
    MeshSurface (*loadTexture)(void*, const char*, UInt32) = nullptr;
    void (*releaseTexture)(void*, MeshSurface) = nullptr;
    void (*error)(void*, const char*) = nullptr;
    void (*allocation)(void*, const char*, int) = nullptr;
};
ORBITER_PRODUCTION_API MeshServices BindMeshServices(MeshServices services);
ORBITER_PRODUCTION_API const MeshServices& GetMeshServices();
}
ORBITER_PRODUCTION_API orbiter::production::UInt64 Str2Crc(const char* name);
#endif
