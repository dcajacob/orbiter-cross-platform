// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_MESH_DATA_H
#define ORBITER_PRODUCTION_MESH_DATA_H
#include "Export.h"
#include <cstdint>
#include <istream>
#include <string>
#include <vector>

namespace orbiter::production {
struct MeshVertex { float x, y, z, nx, ny, nz, tu, tv; };
struct MeshColour { float r, g, b, a; };
struct MeshMaterial {
    MeshColour diffuse, ambient, specular, emissive;
    float power;
};
struct MeshGroup {
    std::vector<MeshVertex> vertices;
    std::vector<std::uint16_t> indices;
    std::uint32_t material, texture, userFlags;
    std::uint16_t zBias, flags;
};
struct MeshTexture {
    std::string name;
    std::uint32_t loadFlags = 0;
};
// CPU data only: stable source group indices, materials, UVs, inheritance flags
// and texture identities. There are no device resources or graphics handles.
struct MeshData {
    std::vector<MeshGroup> groups;
    std::vector<MeshMaterial> materials;
    std::vector<MeshTexture> textures;
};
ORBITER_PRODUCTION_API MeshData LoadMeshData(std::istream& input);
}
#endif
