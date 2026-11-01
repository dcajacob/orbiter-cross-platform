// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "MeshData.h"
#include "MeshReader.h"
#include "MeshNormals.h"
#include <memory>
#include <stdexcept>

namespace orbiter::production {
namespace {
class CpuMeshSink {
public:
    using Vertex = MeshVertex;
    using Index = std::uint16_t;
    using Material = MeshMaterial;
    MeshData data;
    void Clear() { data = {}; }
    void AddGroup(Vertex* vertices, int nv, Index* indices, int ni,
        std::uint32_t material, std::uint32_t texture, std::uint16_t bias)
    {
        std::unique_ptr<Vertex[]> ownedVertices(vertices);
        std::unique_ptr<Index[]> ownedIndices(indices);
        MeshGroup group;
        group.vertices.assign(vertices, vertices + nv);
        group.indices.assign(indices, indices + ni);
        group.material = material;
        group.texture = texture;
        group.zBias = bias;
        data.groups.push_back(std::move(group));
    }
    void SetGroupFlags(int group, std::uint16_t flags, std::uint32_t user)
    {
        data.groups.at(group).flags = flags;
        data.groups.at(group).userFlags = user;
    }
    void CalcNormals(int group, bool missingOnly)
    {
        auto& g = data.groups.at(group);
        CalculateMeshNormals(g.vertices.data(), g.indices.data(),
            static_cast<int>(g.vertices.size()), static_cast<int>(g.indices.size()/3), missingOnly);
    }
    void AddMaterial(const Material& material) { data.materials.push_back(material); }
    void ReleaseTextures() { data.textures.clear(); }
    void CreateTextures(int count) { data.textures.resize(count); }
    void LoadTexture(int index, const char* name, std::uint32_t flags)
    {
        data.textures.at(index) = {name, flags};
    }
    void Setup()
    {
        for (auto& g : data.groups) {
            if (g.material != std::uint32_t(-2) && g.material >= data.materials.size())
                g.material = std::uint32_t(-1);
            if (g.texture != std::uint32_t(-2) && g.texture >= data.textures.size())
                g.texture = std::uint32_t(-1);
        }
    }
};
}
MeshData LoadMeshData(std::istream& input)
{
    CpuMeshSink sink;
    ReadMesh(input, sink);
    if (!input || sink.data.groups.empty()) throw std::runtime_error("Invalid or empty MSHX1 mesh");
    return std::move(sink.data);
}
}
