// Licensed under the MIT License
#pragma once

#include "RunwayTerrain.h"

#include <map>
#include <memory>

namespace orbiter::vulkan {

class OrbiterScene {
public:
    ~OrbiterScene();
    SURFHANDLE Load(const std::filesystem::path&);
    SURFHANDLE Create(unsigned width, unsigned height);
    const TextureData* Lookup(SURFHANDLE) const;
    void Retain(SURFHANDLE);
    bool Release(SURFHANDLE);
    bool Size(SURFHANDLE, unsigned&, unsigned&) const;
    bool Fill(SURFHANDLE, unsigned, unsigned, unsigned, unsigned, std::uint32_t);
    bool Blit(SURFHANDLE, unsigned, unsigned, SURFHANDLE, unsigned, unsigned, unsigned, unsigned);

    void Open(SDL_Window* window);
    void CaptureFocus(const std::filesystem::path& archive);
    void CaptureFrame(std::filesystem::path path) { scene_.Capture(std::move(path)); }
    void ClearFocus() noexcept;
    bool Present(unsigned width, unsigned height);
    void Close() noexcept;

private:
    SURFHANDLE Add(TextureData);
    SceneFrame ShipFrame() const;
    Scene scene_;
    RunwayTerrain terrain_;
    OBJHANDLE focus_ = nullptr;
    VECTOR3 offset_{};
    std::map<SURFHANDLE, std::unique_ptr<TextureData>> surfaces_;
};

} // namespace orbiter::vulkan
