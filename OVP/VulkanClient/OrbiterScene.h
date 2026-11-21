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

// Orbiter registers these surfaces against vessel-local mesh and group indices.
struct CockpitDisplay {
    unsigned mesh, group;
    SURFHANDLE surface;
    bool hud;
    bool operator==(const CockpitDisplay& b) const {
        return mesh == b.mesh && group == b.group && surface == b.surface && hud == b.hud;
    }
};

template<class Hud, class Mfd>
std::vector<CockpitDisplay> PilotDisplays(bool worldReady, Hud hud, Mfd mfd)
{
    std::vector<CockpitDisplay> displays;
    if (!worldReady || !oapiCameraInternal() || oapiCockpitMode() != COCKPIT_VIRTUAL) return displays;
    const VCHUDSPEC* h = nullptr;
    if (auto surface = hud(&h); surface && h)
        displays.push_back({h->nmesh, h->ngroup, surface, true});
    for (int i = 0; i < MAXMFD; ++i) {
        const VCMFDSPEC* m = nullptr;
        if (auto surface = mfd(i, &m); surface && m)
            displays.push_back({m->nmesh, m->ngroup, surface, false});
    }
    return displays;
}

class OrbiterScene {
public:
    ~OrbiterScene();
    SURFHANDLE Load(const std::filesystem::path&);
    SURFHANDLE Create(unsigned width, unsigned height);
    const TextureData* Lookup(SURFHANDLE) const;
    TextureData* Writable(SURFHANDLE);
    void BeginPanelFrame() { scene_.BeginPanelFrame(); }
    void Panel(SURFHANDLE*, MESHHANDLE, const MATRIX3&, float alpha, bool additive,
        const std::function<SURFHANDLE(int)>& mfd);
    void Retain(SURFHANDLE);
    bool Release(SURFHANDLE);
    bool Size(SURFHANDLE, unsigned&, unsigned&) const;
    bool Fill(SURFHANDLE, unsigned, unsigned, unsigned, unsigned, std::uint32_t);
    bool Blit(SURFHANDLE, unsigned, unsigned, SURFHANDLE, unsigned, unsigned, unsigned, unsigned);

    struct BaseGeometry {
        const SurftileSpec* tiles = nullptr;
        MESHHANDLE* surfaces = nullptr;
        MESHHANDLE* buildings = nullptr;
        unsigned tileCount = 0, surfaceCount = 0, buildingCount = 0;
    };
    using BaseMeshes = std::function<BaseGeometry(OBJHANDLE)>;
    void Open(SDL_Window* window, BaseMeshes baseMeshes, bool baseShadows);
    void OpenWorld(std::filesystem::path archive);
    void CaptureFrame(std::filesystem::path path) { scene_.Capture(std::move(path)); }
    void CloseWorld() noexcept;
    using RegisterPilot = std::function<void(OBJHANDLE,VISHANDLE)>;
    void SetPilotRegistration(RegisterPilot callback) { registerPilot_ = std::move(callback); }
    MESHHANDLE DeviceMesh(VISHANDLE, unsigned);
    int ReadGroup(DEVMESHHANDLE, unsigned, GROUPREQUESTSPEC*);
    int EditGroup(DEVMESHHANDLE, unsigned, GROUPEDITSPEC*);
    int SetMaterial(DEVMESHHANDLE, unsigned, const MATERIAL*);
    bool SetTexture(DEVMESHHANDLE, unsigned, SURFHANDLE);
    void RemoveVessel(OBJHANDLE) noexcept;
    bool Present(unsigned width, unsigned height, const std::vector<CockpitDisplay>&);
    std::string FlightTitle() const;
    void Close() noexcept;

private:
    SURFHANDLE Add(TextureData);
    bool ReplaceTextureSlot(MESHHANDLE, unsigned slot, SURFHANDLE);
    struct EarthBase {
        unsigned index;
        OBJHANDLE handle;
        VECTOR3 position;
        double longitude, latitude;
        bool loaded = false;
    };
    void LoadBase(const EarthBase&, const SceneFrame&);
    bool UpdateBases(const VECTOR3& eye);
    struct VesselVisual {
        VesselPose pose;
        // An engaged null handle denotes an exterior, load-on-demand mesh.
        std::vector<std::optional<MESHHANDLE>> meshSlots;
        std::vector<CockpitDisplay> displays;
        std::map<SURFHANDLE, unsigned> displaySlots;
        std::map<unsigned, std::uint64_t> revisions;
        bool pilotSeat = false;
        std::vector<Vertex> shadow;
        std::optional<double> shadowTime;
        bool retained = false;
        bool awaitingLiftoff = false;
    };
    struct VesselUpdate {
        bool poseUploaded = false, shadowDrawn = false;
    };
    VesselUpdate UpdateVessels(const SceneFrame& camera, const SceneFrame& ground,
        const EarthView& earth, unsigned height, bool refreshShadow, bool terrainRecentered,
        const std::vector<CockpitDisplay>& displays);
    void RefreshMeshes(const VESSEL&, VesselVisual&, bool internal, const std::vector<CockpitDisplay>&);
    void AppendMesh(MESHHANDLE, SceneMesh&, std::vector<VertexRange>&,
        std::map<SURFHANDLE, unsigned>& textureSlots, std::optional<DrawPass> pass = {},
        SURFHANDLE surfaceTexture = nullptr,
        unsigned meshIndex = ~0u, const std::vector<CockpitDisplay>& displays = {},
        bool dgCockpit = false) const;
    struct PilotMesh {
        MESHHANDLE mesh = nullptr;
        std::set<unsigned> changed;
        bool rebuild = false;
    };
    RegisterPilot registerPilot_;
    OBJHANDLE pilot_ = nullptr;
    std::array<PilotMesh,2> pilotMeshes_{};
    void SetPilot(OBJHANDLE);
    PilotMesh* FindDevice(DEVMESHHANDLE);
    Scene scene_;
    BaseMeshes baseMeshes_;
    bool baseShadows_ = true;
    std::filesystem::path captureDirectory_;
    unsigned captureFps_ = 10;
    long long lastCapture_ = -1;
    std::vector<EarthBase> bases_;
    RunwayTerrain terrain_;
    std::map<OBJHANDLE, VesselVisual> vessels_;
    std::vector<VesselDraw> draws_;
    std::ofstream frameTrace_;
    Uint64 previousFrame_ = 0;
    OBJHANDLE focus_ = nullptr;
    bool worldOpen_ = false;
    std::map<SURFHANDLE, std::unique_ptr<TextureData>> surfaces_;
};

} // namespace orbiter::vulkan
