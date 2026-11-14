// Licensed under the MIT License
#pragma once

#include <SDL3/SDL.h>
#include <array>
#include <cstdint>
#include <filesystem>
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
};

struct MaterialUniform {
    float diffuse[4] = {1, 1, 1, 1};
    float emission[4] = {};
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

class Scene {
public:
    Scene() = default;
    ~Scene();
    Scene(const Scene&) = delete;
    Scene& operator=(const Scene&) = delete;

    void Open(SDL_Window*);
    void SetMesh(const SceneMesh&);
    bool Present(const SceneUniform& ship, const SceneUniform& ground);
    void Capture(std::filesystem::path path) { capture_ = std::move(path); }
    void Close() noexcept;
    void ClearMesh() noexcept;

private:
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
    std::vector<SDL_GPUTexture*> textures_;
    std::vector<Group> groups_;
    unsigned width_ = 0;
    unsigned height_ = 0;
    bool claimed_ = false;
};

void Require(bool, const char*);

} // namespace orbiter::vulkan
