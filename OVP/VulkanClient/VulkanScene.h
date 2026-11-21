// Licensed under the MIT License
#pragma once

#include <SDL3/SDL.h>
#include "SceneFrame.h"
#include <array>
#include <cstdint>
#include <filesystem>
#include <map>
#include <set>
#include <tuple>
#include <vector>

namespace orbiter::vulkan {

struct Vertex {
    float position[3];
    float normal[3];
    float uv[2];
};

struct TextureData {
    std::filesystem::path path;
    unsigned width = 0;
    unsigned height = 0;
    unsigned levels = 1;
    unsigned blockBytes = 0;
    SDL_GPUTextureFormat format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
    std::vector<std::uint8_t> pixels;
    unsigned references = 1;
    std::uint64_t revision = 0;
};

TextureData ReadDds(const std::filesystem::path& path);
TextureData DecodeDds(const std::vector<std::uint8_t>& bytes, const std::filesystem::path& label);

struct SceneUniform {
    float projection[16];
    float light[4];
    float eye[4];
    std::array<float, 16> shadowTransform{};
};

struct VesselDraw {
    OBJHANDLE handle;
    SceneUniform uniform;
};

struct MaterialUniform {
    std::array<float, 4> diffuse{1, 1, 1, 1};
    std::array<float, 4> emission{};
    std::array<float, 4> ambient{1, 1, 1, 0};
    std::array<float, 4> specular{}; // RGB reflectance and Orbiter specular power
};

enum class DrawPass { Terrain, BaseTile, Pavement, GroundShadow, PavementShadow, Shadow, Opaque, Translucent, ShadowOnly };

struct Group {
    unsigned firstIndex;
    unsigned indexCount;
    unsigned textureIndex;
    MaterialUniform material;
    DrawPass pass;
    bool castsShadow;
};

struct SceneMesh {
    std::vector<Vertex> vertices;
    std::vector<std::uint32_t> indices;
    std::vector<const TextureData*> textures{nullptr};
    std::vector<Group> groups;
};

struct TileKey {
    int level, row, column;

    bool operator<(const TileKey& other) const
    {
        return std::tie(level, row, column) < std::tie(other.level, other.row, other.column);
    }
    bool operator==(const TileKey& other) const
    {
        return level == other.level && row == other.row && column == other.column;
    }
};

struct TerrainMesh {
    VECTOR3 origin{}; // Earth-fixed centre. Vertices are relative to this point.
    TextureData texture;
    std::vector<Vertex> vertices;
    std::vector<std::uint32_t> indices;
};

struct FrameTimings {
    Uint64 acquireNS = 0, fenceNS = 0, encodeNS = 0, submitNS = 0;
    unsigned terrainDraws = 0;
};

struct PanelVertex { float x, y, u, v; };
class Scene {
public:
    Scene() = default;
    ~Scene();
    Scene(const Scene&) = delete;
    Scene& operator=(const Scene&) = delete;

    void Open(SDL_Window*, bool trace);
    void SetShip(OBJHANDLE, const SceneMesh&);
    void AddBase(unsigned index, const SceneMesh&, bool shadows);
    void RemoveBase(unsigned index) noexcept;
    void UpdateDisplay(OBJHANDLE, unsigned slot, const TextureData&);
    void SetShipPose(OBJHANDLE, const std::vector<Vertex>&);
    void StageTile(const TileKey&, const TerrainMesh&);
    void SelectTiles(const std::set<TileKey>& visible, const std::set<TileKey>& pending);
    void SetShadow(OBJHANDLE, const std::vector<Vertex>&);
    void RemoveShip(OBJHANDLE) noexcept;
    bool Present(const std::vector<VesselDraw>& ships, const SceneUniform& ground, const EarthView& earth,
        const std::filesystem::path& sample = {});
    void BeginPanelFrame() { panelBatches_.clear(); panelVertices_.clear(); }
    void PanelGroup(const TextureData*, const MESHGROUP&, const MATRIX3&, float alpha, bool additive);
    void ForgetPanelTexture(const TextureData*);
    void Capture(std::filesystem::path path) { capture_ = std::move(path); }
    const FrameTimings& Timings() const { return timings_; }
    bool ShadowMapUpdated() const { return mapUpdated_; }
    void Close() noexcept;
    void ClearGround() noexcept;
    void ClearMesh() noexcept;

private:
    struct PanelBatch {
        const TextureData* image;
        Uint32 first, count;
        float alpha;
        bool additive;
    };
    struct PanelTexture {
        SDL_GPUTexture* gpu = nullptr;
        std::uint64_t revision = 0;
    };
    void OpenPanel(SDL_GPUShader*, SDL_GPUShader*);
    void PreparePanel();
    void DrawPanel(SDL_GPURenderPass*, SDL_GPUCommandBuffer*, unsigned width, unsigned height);
    void ClearPanel() noexcept;
    std::vector<PanelVertex> panelVertices_;
    std::vector<PanelBatch> panelBatches_;
    std::map<const TextureData*, PanelTexture> panelTextures_;
    TextureData panelWhite_;
    SDL_GPUBuffer* panelBuffer_ = nullptr;
    SDL_GPUGraphicsPipeline* panelPipeline_[2]{};
    struct GpuMesh {
        SDL_GPUBuffer* vertices = nullptr;
        SDL_GPUBuffer* indices = nullptr;
        std::vector<SDL_GPUTexture*> textures;
        SDL_GPUTexture* flightdeckFinish = nullptr;
        unsigned flightdeckSlot = 0;
        SDL_GPUSampler* sampler = nullptr; // borrowed from Scene
        std::vector<Group> groups;
    };
    SDL_GPUCopyPass* UploadPass();
    SDL_GPUBuffer* UploadBuffer(SDL_GPUBufferUsageFlags, const void*, std::size_t);
    void UploadMesh(const SceneMesh&, GpuMesh&, bool vesselSkin);
    void Release(GpuMesh&) noexcept;
    void DrawMesh(SDL_GPURenderPass*, SDL_GPUCommandBuffer*, const GpuMesh&, DrawPass, bool receiver = false);
    struct Bounds {
        std::array<float, 3> low, high;
        Bounds();
        void Include(const Vertex&);
        bool InView(const std::array<std::array<double, 4>, 4>& planes) const;
        bool InShadowFootprint(const std::array<float, 16>& projection) const;
    };
    struct Base {
        GpuMesh mesh;
        SDL_GPUBuffer* casterIndices = nullptr;
        unsigned casterCount = 0;
        Bounds casters, surfaces;
        SDL_GPUTexture* shadowMap = nullptr;
        std::array<float, 16> transform{};
        float slopeX = 0, slopeZ = 0;
        bool mapValid = false, sunlit = false;
    };
    void PrepareBaseShadow(SDL_GPUCommandBuffer*, Base&, const SceneUniform&);
    void DrawGroundShadows(SDL_GPURenderPass*, SDL_GPUCommandBuffer*, SceneUniform, const EarthView&);
    struct GroundTile {
        VECTOR3 origin{};
        SceneUniform uniform{};
        SDL_GPUBuffer* vertices = nullptr;
        SDL_GPUBuffer* indices = nullptr;
        SDL_GPUTexture* texture = nullptr;
        unsigned indexCount = 0;
        bool visible = false, inView = false;
        Bounds bounds;
    };
    void DrawTile(SDL_GPURenderPass*, const GroundTile&);
    struct Ship {
        GpuMesh mesh;
        SDL_GPUTransferBuffer* poseUpload = nullptr;
        SDL_GPUBuffer* shadowVertices = nullptr;
        SDL_GPUTransferBuffer* shadowUpload = nullptr;
        SDL_GPUBuffer* shadowIndices = nullptr;  // null when all groups cast
        Uint32 vertexBytes = 0, shadowIndexCount = 0;
        bool showShadow = false;
    };
    void Release(GroundTile&) noexcept;
    void UpdateVesselVertices(const std::vector<Vertex>&, SDL_GPUBuffer*, SDL_GPUTransferBuffer*&, Uint32 bytes);
    SDL_GPUTexture* UploadTexture(const TextureData&, bool completeMipChain = false);
    SDL_GPUGraphicsPipeline* CreatePipeline(SDL_GPUShader*, SDL_GPUShader*, DrawPass);
    void ResizeDepth(unsigned, unsigned);
    void SaveFrame(SDL_GPUCommandBuffer*, SDL_GPUTexture*, SDL_GPUTexture*, unsigned, unsigned, const std::filesystem::path& sample);
    std::filesystem::path capture_;

    SDL_Window* window_ = nullptr;
    SDL_GPUDevice* device_ = nullptr;
    SDL_GPUCommandBuffer* uploadCommands_ = nullptr;
    SDL_GPUCopyPass* uploadPass_ = nullptr;
    SDL_GPUSampler* sampler_ = nullptr;
    SDL_GPUSampler* vesselSampler_ = nullptr;
    SDL_GPUSampler* terrainSampler_ = nullptr;
    SDL_GPUGraphicsPipeline* sky_ = nullptr;
    SDL_GPUGraphicsPipeline* terrain_ = nullptr;
    SDL_GPUGraphicsPipeline* opaque_ = nullptr;
    SDL_GPUGraphicsPipeline* translucent_ = nullptr;
    SDL_GPUGraphicsPipeline* shadow_ = nullptr;
    SDL_GPUTextureFormat depthFormat_ = SDL_GPU_TEXTUREFORMAT_INVALID;
    SDL_GPUTexture* depth_ = nullptr;
    std::map<OBJHANDLE, Ship> ships_;
    std::map<unsigned, Base> bases_;
    SDL_GPUGraphicsPipeline* shadowMapPipeline_ = nullptr;
    SDL_GPUGraphicsPipeline* pavement_ = nullptr;
    SDL_GPUGraphicsPipeline* groundShadow_ = nullptr;
    SDL_GPUGraphicsPipeline* pavementShadow_ = nullptr;
    SDL_GPUSampler* shadowSampler_ = nullptr;
    bool mapUpdated_ = false;
    bool trace_ = false;
    FrameTimings timings_;
    std::map<TileKey, GroundTile> tiles_;
    unsigned width_ = 0;
    unsigned height_ = 0;
    bool claimed_ = false;
};

void Require(bool, const char*);

} // namespace orbiter::vulkan
