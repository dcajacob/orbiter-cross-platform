// Licensed under the MIT License
#pragma once

#include "SceneFrame.h"
#include "VulkanScene.h"

#include <deque>

namespace orbiter::vulkan {

class RunwayTerrain {
public:
    void Append(const std::filesystem::path& archive, const SceneFrame& ship, SceneMesh&);
    SceneFrame Frame() const;

private:
    OBJHANDLE earth_ = nullptr;
    SceneFrame local_{};
    std::deque<TextureData> textures_;
};

} // namespace orbiter::vulkan
