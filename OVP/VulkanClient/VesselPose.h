// Licensed under the MIT License
#pragma once

#include "SceneFrame.h"
#include "VulkanScene.h"

namespace orbiter::vulkan {

struct VertexRange {
    std::size_t first = 0;
    std::size_t count = 0;
};

struct MeshGroups {
    std::size_t first = 0;
    std::size_t count = 0;
    VECTOR3 offset{};
};

class VesselPose {
public:
    void Reset(std::vector<Vertex> mesh, std::vector<VertexRange> groups, std::vector<MeshGroups> meshes);
    bool Update(const VESSEL&);
    const std::vector<Vertex>& Vertices() const { return posed_; }

private:
    std::vector<Vertex> mesh_;
    std::vector<Vertex> posed_;
    std::vector<VertexRange> groups_;
    std::vector<MeshGroups> meshes_;
    std::vector<double> states_;
    bool initialized_ = false;
};

} // namespace orbiter::vulkan
