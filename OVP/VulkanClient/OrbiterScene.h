// Licensed under the MIT License
#pragma once

#include "RunwayTerrain.h"
#include "VesselPose.h"

#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <fstream>

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

    using BaseMeshes = std::function<void(OBJHANDLE, MESHHANDLE*&, unsigned&)>;
    void Open(SDL_Window* window, BaseMeshes baseMeshes, bool baseShadows);
    void CaptureFocus(std::filesystem::path archive);
    void CaptureFrame(std::filesystem::path path) { scene_.Capture(std::move(path)); }
    void ClearFocus() noexcept;
    bool Present(unsigned width, unsigned height);
    std::string FlightTitle() const;
    void Close() noexcept;

private:
    SURFHANDLE Add(TextureData);
    void LoadBase();
    void RefreshExterior(const VESSEL&);
    void AppendMesh(MESHHANDLE, SceneMesh&, std::vector<VertexRange>&,
        std::map<SURFHANDLE, unsigned>& textureSlots) const;
    Scene scene_;
    BaseMeshes baseMeshes_;
    bool baseShadows_ = true;
    std::filesystem::path captureDirectory_;
    long long lastCapture_ = -1;
    OBJHANDLE kennedy_ = nullptr;
    SceneFrame baseFrame_{};
    bool baseLoaded_ = false;
    RunwayTerrain terrain_;
    VesselPose pose_;
    std::vector<Vertex> shadowVertices_;
    std::optional<double> shadowTime_;
    bool loggedLiftoff_ = false;
    std::ofstream frameTrace_;
    Uint64 previousFrame_ = 0;
    OBJHANDLE focus_ = nullptr;
    std::filesystem::path archivePath_;
    // An engaged null handle denotes an exterior, load-on-demand mesh.
    std::vector<std::optional<MESHHANDLE>> exteriorSlots_;
    std::map<SURFHANDLE, std::unique_ptr<TextureData>> surfaces_;
};

} // namespace orbiter::vulkan
