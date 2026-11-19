// Licensed under the MIT License
#pragma once

#include <SDL3/SDL.h>
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
};

TextureData ReadDds(const std::filesystem::path& path);
TextureData DecodeDds(const std::vector<std::uint8_t>& bytes, const std::filesystem::path& label);

struct SceneUniform {
    float projection[16];
    float light[4];
    float eye[4];
};

struct MaterialUniform {
    std::array<float, 4> diffuse{1, 1, 1, 1};
    std::array<float, 4> emission{};
    std::array<float, 4> ambient{1, 1, 1, 0};
    std::array<float, 4> specular{}; // RGB reflectance and Orbiter specular power
};

enum class DrawPass { Terrain, Shadow, Opaque, Translucent };

struct Group {
    unsigned firstIndex;
    unsigned indexCount;
    unsigned textureIndex;
    MaterialUniform material;
    DrawPass pass;
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
    TextureData texture;
    std::vector<Vertex> vertices;
    std::vector<std::uint32_t> indices;
};

class Scene {
public:
    Scene() = default;
    ~Scene();
    Scene(const Scene&) = delete;
    Scene& operator=(const Scene&) = delete;

    void Open(SDL_Window*);
    void SetShip(const SceneMesh&);
    void SetShipPose(const std::vector<Vertex>&);
    void StageTile(const TileKey&, const TerrainMesh&);
    void SelectTiles(const std::set<TileKey>& visible, const std::set<TileKey>& pending);
    void SetShadow(const std::vector<Vertex>&);
    bool Present(const SceneUniform& ship, const SceneUniform& ground);
    void Capture(std::filesystem::path path) { capture_ = std::move(path); }
    void Close() noexcept;
    void ClearMesh() noexcept;

private:
    struct GroundTile {
        SDL_GPUBuffer* vertices = nullptr;
        SDL_GPUBuffer* indices = nullptr;
        SDL_GPUTexture* texture = nullptr;
        unsigned indexCount = 0;
        bool visible = false;
    };
    void ClearShip() noexcept;
    void Release(GroundTile&) noexcept;
    void UpdateVesselVertices(const std::vector<Vertex>&, SDL_GPUBuffer*, SDL_GPUTransferBuffer*);
    SDL_GPUTexture* UploadTexture(const TextureData&);
    SDL_GPUGraphicsPipeline* CreatePipeline(SDL_GPUShader*, SDL_GPUShader*, DrawPass);
    void ResizeDepth(unsigned, unsigned);
    void SaveFrame(SDL_GPUCommandBuffer*, SDL_GPUTexture*, SDL_GPUTexture*, unsigned, unsigned);
    std::filesystem::path capture_;

    SDL_Window* window_ = nullptr;
    SDL_GPUDevice* device_ = nullptr;
    SDL_GPUSampler* sampler_ = nullptr;
    SDL_GPUSampler* terrainSampler_ = nullptr;
    SDL_GPUGraphicsPipeline* terrain_ = nullptr;
    SDL_GPUGraphicsPipeline* opaque_ = nullptr;
    SDL_GPUGraphicsPipeline* translucent_ = nullptr;
    SDL_GPUGraphicsPipeline* shadow_ = nullptr;
    SDL_GPUTextureFormat depthFormat_ = SDL_GPU_TEXTUREFORMAT_INVALID;
    SDL_GPUTexture* depth_ = nullptr;
    SDL_GPUBuffer* vertices_ = nullptr;
    SDL_GPUBuffer* indices_ = nullptr;
    unsigned shipIndexCount_ = 0;
    SDL_GPUBuffer* shadowVertices_ = nullptr;
    SDL_GPUTransferBuffer* shipUpload_ = nullptr;
    SDL_GPUTransferBuffer* shadowUpload_ = nullptr;
    Uint32 vesselVertexBytes_ = 0;
    bool showShadow_ = false;
    std::map<TileKey, GroundTile> tiles_;
    std::vector<SDL_GPUTexture*> textures_;
    std::vector<Group> groups_;
    unsigned width_ = 0;
    unsigned height_ = 0;
    bool claimed_ = false;
};

void Require(bool, const char*);

} // namespace orbiter::vulkan
