// Licensed under the MIT License
#include "VulkanScene.h"
#include "ShipShaders.h"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

namespace orbiter::vulkan {
namespace {

std::vector<std::uint8_t> Bytes(const std::filesystem::path& path)
{
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("Cannot open " + path.string());
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

std::uint32_t Read32(const std::vector<std::uint8_t>& bytes, unsigned offset)
{
    std::uint32_t result = 0;
    for (unsigned i = 0; i < 4; ++i) result |= std::uint32_t(bytes[offset + i]) << (i * 8);
    return result;
}

SDL_GPUShader* Shader(SDL_GPUDevice* device, const std::uint8_t* bytes, std::size_t size, SDL_GPUShaderStage stage)
{
    SDL_GPUShaderCreateInfo info{};
    info.code = bytes;
    info.code_size = size;
    info.entrypoint = "main";
    info.format = SDL_GPU_SHADERFORMAT_SPIRV;
    info.stage = stage;
    info.num_samplers = stage == SDL_GPU_SHADERSTAGE_FRAGMENT ? 1 : 0;
    info.num_uniform_buffers = 1;
    auto* shader = SDL_CreateGPUShader(device, &info);
    Require(shader != nullptr, "Create Vulkan shader");
    return shader;
}

SDL_GPUTransferBuffer* Upload(SDL_GPUDevice* device, const void* data, std::size_t size)
{
    if (!size || size > std::numeric_limits<Uint32>::max())
        throw std::runtime_error("Invalid GPU upload size");
    SDL_GPUTransferBufferCreateInfo info{};
    info.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
    info.size = static_cast<Uint32>(size);
    auto* buffer = SDL_CreateGPUTransferBuffer(device, &info);
    Require(buffer != nullptr, "Create Vulkan transfer buffer");
    auto* mapped = SDL_MapGPUTransferBuffer(device, buffer, false);
    if (!mapped) {
        SDL_ReleaseGPUTransferBuffer(device, buffer);
        Require(false, "Map Vulkan transfer buffer");
    }
    std::memcpy(mapped, data, size);
    SDL_UnmapGPUTransferBuffer(device, buffer);
    return buffer;
}

SDL_GPUBuffer* Buffer(SDL_GPUDevice* device, SDL_GPUBufferUsageFlags usage, const void* data, std::size_t size)
{
    auto* transfer = Upload(device, data, size);
    SDL_GPUBufferCreateInfo info{};
    info.usage = usage;
    info.size = static_cast<Uint32>(size);
    auto* buffer = SDL_CreateGPUBuffer(device, &info);
    auto* commands = buffer ? SDL_AcquireGPUCommandBuffer(device) : nullptr;
    if (!commands) {
        if (buffer) SDL_ReleaseGPUBuffer(device, buffer);
        SDL_ReleaseGPUTransferBuffer(device, transfer);
        Require(false, "Allocate Vulkan buffer and upload commands");
    }
    auto* pass = SDL_BeginGPUCopyPass(commands);
    const SDL_GPUTransferBufferLocation source{transfer, 0};
    const SDL_GPUBufferRegion target{buffer, 0, info.size};
    SDL_UploadToGPUBuffer(pass, &source, &target, false);
    SDL_EndGPUCopyPass(pass);
    const bool submitted = SDL_SubmitGPUCommandBuffer(commands);
    SDL_ReleaseGPUTransferBuffer(device, transfer);
    if (!submitted) SDL_ReleaseGPUBuffer(device, buffer);
    Require(submitted, "Submit Vulkan buffer upload");
    return buffer;
}

unsigned LevelSize(const TextureData& texture, unsigned width, unsigned height)
{
    if (texture.blockBytes) return ((width + 3) / 4) * ((height + 3) / 4) * texture.blockBytes;
    return width * height * 4;
}

} // namespace

void Require(bool success, const char* operation)
{
    if (!success) throw std::runtime_error(std::string(operation) + ": " + SDL_GetError());
}

TextureData ReadDds(const std::filesystem::path& path)
{
    return DecodeDds(Bytes(path), path);
}

TextureData DecodeDds(const std::vector<std::uint8_t>& bytes, const std::filesystem::path& path)
{
    if (bytes.size() < 128 || std::memcmp(bytes.data(), "DDS ", 4) || Read32(bytes, 4) != 124)
        throw std::runtime_error("Invalid DDS header: " + path.string());
    TextureData texture;
    texture.path = path;
    texture.height = Read32(bytes, 12);
    texture.width = Read32(bytes, 16);
    texture.levels = std::max(1u, Read32(bytes, 28));
    if (!texture.height || !texture.width || texture.width > 16384 || texture.height > 16384 ||
        texture.levels > 15 || (Read32(bytes, 112) & 0x220000))
        throw std::runtime_error("Unsupported DDS dimensions or type: " + path.string());

    const auto flags = Read32(bytes, 80);
    const std::string fourcc(reinterpret_cast<const char*>(bytes.data() + 84), 4);
    const bool argb4444 = !(flags & 4) && Read32(bytes, 88) == 16 &&
        Read32(bytes, 92) == 0xf00 && Read32(bytes, 96) == 0xf0 &&
        Read32(bytes, 100) == 0xf && Read32(bytes, 104) == 0xf000;
    if ((flags & 4) && fourcc == "DXT1") {
        texture.format = SDL_GPU_TEXTUREFORMAT_BC1_RGBA_UNORM;
        texture.blockBytes = 8;
    } else if ((flags & 4) && (fourcc == "DXT3" || fourcc == "DXT5")) {
        texture.format = fourcc == "DXT3" ? SDL_GPU_TEXTUREFORMAT_BC2_RGBA_UNORM : SDL_GPU_TEXTUREFORMAT_BC3_RGBA_UNORM;
        texture.blockBytes = 16;
    } else if (!(flags & 4) && Read32(bytes, 88) == 32 && Read32(bytes, 96) == 0xff00 &&
               (Read32(bytes, 92) == 0xff || Read32(bytes, 92) == 0xff0000)) {
        const bool rgba = Read32(bytes, 92) == 0xff;
        texture.format = rgba ? SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM : SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM;
    } else if (!argb4444) {
        throw std::runtime_error("Unsupported DDS pixel format: " + path.string());
    }
    auto width = texture.width;
    auto height = texture.height;
    auto end = std::size_t{128};
    for (unsigned level = 0; level < texture.levels; ++level) {
        end += LevelSize(texture, width, height) / (argb4444 ? 2 : 1);
        width = std::max(1u, width / 2);
        height = std::max(1u, height / 2);
    }
    if (end > bytes.size()) throw std::runtime_error("Truncated DDS: " + path.string());
    if (argb4444) {
        texture.pixels.reserve((end - 128) * 2);
        for (std::size_t i = 128; i < end; i += 2) {
            texture.pixels.push_back(std::uint8_t((bytes[i + 1] & 15) * 17));
            texture.pixels.push_back(std::uint8_t((bytes[i] >> 4) * 17));
            texture.pixels.push_back(std::uint8_t((bytes[i] & 15) * 17));
            texture.pixels.push_back(std::uint8_t((bytes[i + 1] >> 4) * 17));
        }
    } else {
        texture.pixels.assign(bytes.begin() + 128, bytes.begin() + end);
    }
    if (!texture.blockBytes && !Read32(bytes, 104))
        for (std::size_t i = 3; i < texture.pixels.size(); i += 4) texture.pixels[i] = 255;
    return texture;
}

Scene::~Scene()
{
    Close();
}

void Scene::Open(SDL_Window* window)
{
    window_ = window;
    device_ = SDL_CreateGPUDevice(SDL_GPU_SHADERFORMAT_SPIRV, true, "vulkan");
    Require(device_ != nullptr, "Create native Vulkan GPU device");
    Require(std::string(SDL_GetGPUDeviceDriver(device_)) == "vulkan", "Select Vulkan driver");
    Require(SDL_ClaimWindowForGPUDevice(device_, window_), "Create Vulkan swapchain");
    claimed_ = true;

    SDL_GPUSamplerCreateInfo sampler{};
    sampler.min_filter = sampler.mag_filter = SDL_GPU_FILTER_LINEAR;
    sampler.mipmap_mode = SDL_GPU_SAMPLERMIPMAPMODE_LINEAR;
    sampler.address_mode_u = sampler.address_mode_v = sampler.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_REPEAT;
    sampler.max_lod = 15;
    sampler_ = SDL_CreateGPUSampler(device_, &sampler);
    Require(sampler_ != nullptr, "Create Vulkan sampler");
    sampler.address_mode_u = sampler.address_mode_v = sampler.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    terrainSampler_ = SDL_CreateGPUSampler(device_, &sampler);
    Require(terrainSampler_ != nullptr, "Create Vulkan terrain sampler");

    for (auto format : {SDL_GPU_TEXTUREFORMAT_D32_FLOAT_S8_UINT, SDL_GPU_TEXTUREFORMAT_D24_UNORM_S8_UINT}) {
        if (SDL_GPUTextureSupportsFormat(device_, format, SDL_GPU_TEXTURETYPE_2D, SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET)) {
            depthFormat_ = format;
            break;
        }
    }
    if (depthFormat_ == SDL_GPU_TEXTUREFORMAT_INVALID)
        throw std::runtime_error("Vulkan device has no supported depth and stencil format");

    auto* vertex = Shader(device_, Ship_vert, sizeof(Ship_vert), SDL_GPU_SHADERSTAGE_VERTEX);
    SDL_GPUShader* fragment = nullptr;
    try {
        fragment = Shader(device_, Ship_frag, sizeof(Ship_frag), SDL_GPU_SHADERSTAGE_FRAGMENT);
        terrain_ = CreatePipeline(vertex, fragment, DrawPass::Terrain);
        opaque_ = CreatePipeline(vertex, fragment, DrawPass::Opaque);
        translucent_ = CreatePipeline(vertex, fragment, DrawPass::Translucent);
        shadow_ = CreatePipeline(vertex, fragment, DrawPass::Shadow);
    } catch (...) {
        if (fragment) SDL_ReleaseGPUShader(device_, fragment);
        SDL_ReleaseGPUShader(device_, vertex);
        throw;
    }
    SDL_ReleaseGPUShader(device_, fragment);
    SDL_ReleaseGPUShader(device_, vertex);
    const auto properties = SDL_GetGPUDeviceProperties(device_);
    const auto* name = SDL_GetStringProperty(properties, SDL_PROP_GPU_DEVICE_NAME_STRING, "unknown");
    std::clog << "Runway33 Vulkan backend: " << SDL_GetGPUDeviceDriver(device_) << "; GPU: " << name << '\n';
}

SDL_GPUGraphicsPipeline* Scene::CreatePipeline(SDL_GPUShader* vertex, SDL_GPUShader* fragment, DrawPass kind)
{
    const bool blend = kind == DrawPass::Translucent || kind == DrawPass::Shadow;
    SDL_GPUVertexBufferDescription buffer{};
    buffer.pitch = sizeof(Vertex);
    const SDL_GPUVertexAttribute attributes[] = {
        {0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, offsetof(Vertex, position)},
        {1, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, offsetof(Vertex, normal)},
        {2, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2, offsetof(Vertex, uv)}
    };
    SDL_GPUColorTargetDescription target{};
    target.format = SDL_GetGPUSwapchainTextureFormat(device_, window_);
    target.blend_state.enable_blend = blend;
    target.blend_state.src_color_blendfactor = SDL_GPU_BLENDFACTOR_SRC_ALPHA;
    target.blend_state.dst_color_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
    target.blend_state.color_blend_op = SDL_GPU_BLENDOP_ADD;
    target.blend_state.src_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE;
    target.blend_state.dst_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
    target.blend_state.alpha_blend_op = SDL_GPU_BLENDOP_ADD;

    SDL_GPUGraphicsPipelineCreateInfo info{};
    info.vertex_shader = vertex;
    info.fragment_shader = fragment;
    info.vertex_input_state = {&buffer, 1, attributes, 3};
    info.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
    info.rasterizer_state.fill_mode = SDL_GPU_FILLMODE_FILL;
    // Stock ship panels supply separate front and back faces at the same positions.
    const bool ship = kind == DrawPass::Opaque || kind == DrawPass::Translucent;
    info.rasterizer_state.cull_mode = ship ? SDL_GPU_CULLMODE_BACK : SDL_GPU_CULLMODE_NONE;
    info.rasterizer_state.front_face = SDL_GPU_FRONTFACE_CLOCKWISE;
    info.depth_stencil_state.enable_depth_test = true;
    info.depth_stencil_state.enable_depth_write = !blend;
    info.depth_stencil_state.compare_op = SDL_GPU_COMPAREOP_LESS_OR_EQUAL;
    if (kind == DrawPass::Shadow) {
        // Blend once per pixel even when several projected triangles overlap.
        const SDL_GPUStencilOpState stamp{
            SDL_GPU_STENCILOP_KEEP, SDL_GPU_STENCILOP_REPLACE, SDL_GPU_STENCILOP_KEEP, SDL_GPU_COMPAREOP_NOT_EQUAL};
        info.depth_stencil_state.front_stencil_state = info.depth_stencil_state.back_stencil_state = stamp;
        info.depth_stencil_state.compare_mask = info.depth_stencil_state.write_mask = 0xff;
        info.depth_stencil_state.enable_stencil_test = true;
    }
    info.target_info.color_target_descriptions = &target;
    info.target_info.num_color_targets = 1;
    info.target_info.depth_stencil_format = depthFormat_;
    info.target_info.has_depth_stencil_target = true;
    auto* pipeline = SDL_CreateGPUGraphicsPipeline(device_, &info);
    Require(pipeline != nullptr, "Create Vulkan mesh pipeline");
    return pipeline;
}

void Scene::ResizeDepth(unsigned width, unsigned height)
{
    if (depth_ && width == width_ && height == height_) return;
    if (depth_) SDL_ReleaseGPUTexture(device_, depth_);
    SDL_GPUTextureCreateInfo info{};
    info.type = SDL_GPU_TEXTURETYPE_2D;
    info.format = depthFormat_;
    info.usage = SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET;
    info.width = width;
    info.height = height;
    info.layer_count_or_depth = info.num_levels = 1;
    depth_ = SDL_CreateGPUTexture(device_, &info);
    Require(depth_ != nullptr, "Create Vulkan depth image");
    width_ = width;
    height_ = height;
}

SDL_GPUTexture* Scene::UploadTexture(const TextureData& texture)
{
    auto* transfer = Upload(device_, texture.pixels.data(), texture.pixels.size());
    SDL_GPUTextureCreateInfo info{};
    info.type = SDL_GPU_TEXTURETYPE_2D;
    info.format = texture.format;
    info.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER;
    info.width = texture.width;
    info.height = texture.height;
    info.layer_count_or_depth = 1;
    info.num_levels = texture.levels;
    auto* image = SDL_CreateGPUTexture(device_, &info);
    auto* commands = image ? SDL_AcquireGPUCommandBuffer(device_) : nullptr;
    if (!commands) {
        if (image) SDL_ReleaseGPUTexture(device_, image);
        SDL_ReleaseGPUTransferBuffer(device_, transfer);
        Require(false, "Allocate Vulkan texture and upload commands");
    }
    auto* pass = SDL_BeginGPUCopyPass(commands);
    auto width = texture.width;
    auto height = texture.height;
    SDL_GPUTextureTransferInfo source{};
    source.transfer_buffer = transfer;
    for (unsigned level = 0; level < texture.levels; ++level) {
        SDL_GPUTextureRegion region{};
        region.texture = image;
        region.mip_level = level;
        region.w = width;
        region.h = height;
        region.d = 1;
        SDL_UploadToGPUTexture(pass, &source, &region, false);
        source.offset += LevelSize(texture, width, height);
        width = std::max(1u, width / 2);
        height = std::max(1u, height / 2);
    }
    SDL_EndGPUCopyPass(pass);
    const bool submitted = SDL_SubmitGPUCommandBuffer(commands);
    SDL_ReleaseGPUTransferBuffer(device_, transfer);
    if (!submitted) SDL_ReleaseGPUTexture(device_, image);
    Require(submitted, "Submit Vulkan texture upload");
    return image;
}

void Scene::SetMesh(const SceneMesh& mesh)
{
    ClearMesh();
    vertices_ = Buffer(device_, SDL_GPU_BUFFERUSAGE_VERTEX, mesh.vertices.data(), mesh.vertices.size() * sizeof(Vertex));
    indices_ = Buffer(device_, SDL_GPU_BUFFERUSAGE_INDEX, mesh.indices.data(), mesh.indices.size() * sizeof(std::uint32_t));
    TextureData white;
    white.width = white.height = 1;
    white.pixels.assign(4, 255);
    textures_.reserve(mesh.textures.size());
    for (auto* texture : mesh.textures) {
        textures_.push_back(UploadTexture(texture ? *texture : white));
        if (texture) std::clog << "Runway33 uploaded " << texture->path.string() << '\n';
    }
    groups_ = mesh.groups;
    std::clog << "Runway33 indexed mesh: " << mesh.vertices.size() << " vertices, "
              << mesh.indices.size() << " indices, " << groups_.size() << " visible groups\n";
}

bool Scene::Present(const SceneUniform& ship, const SceneUniform& ground)
{
    auto* commands = SDL_AcquireGPUCommandBuffer(device_);
    Require(commands != nullptr, "Acquire Vulkan commands");
    SDL_GPUTexture* back = nullptr;
    unsigned width = 0;
    unsigned height = 0;
    if (!SDL_WaitAndAcquireGPUSwapchainTexture(commands, window_, &back, &width, &height)) {
        SDL_CancelGPUCommandBuffer(commands);
        Require(false, "Acquire Vulkan swapchain image");
    }
    if (!back) return SDL_SubmitGPUCommandBuffer(commands);
    ResizeDepth(width, height);

    const bool capture = !capture_.empty() && !groups_.empty();
    SDL_GPUTexture* frame = back;
    if (capture) {
        SDL_GPUTextureCreateInfo info{};
        info.type = SDL_GPU_TEXTURETYPE_2D;
        info.format = SDL_GetGPUSwapchainTextureFormat(device_, window_);
        info.usage = SDL_GPU_TEXTUREUSAGE_COLOR_TARGET | SDL_GPU_TEXTUREUSAGE_SAMPLER;
        info.width = width;
        info.height = height;
        info.layer_count_or_depth = info.num_levels = 1;
        frame = SDL_CreateGPUTexture(device_, &info);
        if (!frame) {
            SDL_SubmitGPUCommandBuffer(commands);
            Require(false, "Create Vulkan capture target");
        }
    }
    SDL_GPUColorTargetInfo color{};
    color.texture = frame;
    color.clear_color = {0.085f, 0.095f, 0.112f, 1.0f};
    color.load_op = SDL_GPU_LOADOP_CLEAR;
    color.store_op = SDL_GPU_STOREOP_STORE;
    SDL_GPUDepthStencilTargetInfo depth{};
    depth.texture = depth_;
    depth.clear_depth = 1;
    depth.load_op = SDL_GPU_LOADOP_CLEAR;
    depth.store_op = SDL_GPU_STOREOP_DONT_CARE;
    depth.stencil_load_op = SDL_GPU_LOADOP_CLEAR;
    depth.stencil_store_op = SDL_GPU_STOREOP_DONT_CARE;
    auto* pass = SDL_BeginGPURenderPass(commands, &color, 1, &depth);
    if (!groups_.empty()) {
        const SDL_GPUBufferBinding vertex{vertices_, 0};
        const SDL_GPUBufferBinding index{indices_, 0};
        SDL_BindGPUVertexBuffers(pass, 0, &vertex, 1);
        SDL_BindGPUIndexBuffer(pass, &index, SDL_GPU_INDEXELEMENTSIZE_32BIT);
        const struct {
            DrawPass kind;
            SDL_GPUGraphicsPipeline* pipeline;
            SDL_GPUSampler* sampler;
            const SceneUniform& uniform;
        } draws[] = {
            {DrawPass::Terrain, terrain_, terrainSampler_, ground},
            {DrawPass::Shadow, shadow_, sampler_, ground},
            {DrawPass::Opaque, opaque_, sampler_, ship},
            {DrawPass::Translucent, translucent_, sampler_, ship}
        };
        for (const auto& draw : draws) {
            SDL_BindGPUGraphicsPipeline(pass, draw.pipeline);
            if (draw.kind == DrawPass::Shadow) SDL_SetGPUStencilReference(pass, 1);
            SDL_PushGPUVertexUniformData(commands, 0, &draw.uniform, sizeof(draw.uniform));
            for (const auto& group : groups_) {
                if (group.pass != draw.kind) continue;
                const SDL_GPUTextureSamplerBinding binding{textures_.at(group.textureIndex), draw.sampler};
                SDL_BindGPUFragmentSamplers(pass, 0, &binding, 1);
                SDL_PushGPUFragmentUniformData(commands, 0, &group.material, sizeof(group.material));
                SDL_DrawGPUIndexedPrimitives(pass, group.indexCount, 1, group.firstIndex, 0, 0);
            }
        }
    }
    SDL_EndGPURenderPass(pass);
    if (!capture) return SDL_SubmitGPUCommandBuffer(commands);
    try {
        SaveFrame(commands, frame, back, width, height);
    } catch (...) {
        SDL_ReleaseGPUTexture(device_, frame);
        throw;
    }
    SDL_ReleaseGPUTexture(device_, frame);
    capture_.clear();
    return true;
}

void Scene::SaveFrame(SDL_GPUCommandBuffer* commands, SDL_GPUTexture* frame, SDL_GPUTexture* back,
    unsigned width, unsigned height)
{
    SDL_GPUBlitInfo blit{};
    blit.source = {frame, 0, 0, 0, 0, width, height};
    blit.destination = {back, 0, 0, 0, 0, width, height};
    blit.load_op = SDL_GPU_LOADOP_DONT_CARE;
    blit.filter = SDL_GPU_FILTER_NEAREST;
    SDL_BlitGPUTexture(commands, &blit);
    const SDL_GPUTransferBufferCreateInfo info{SDL_GPU_TRANSFERBUFFERUSAGE_DOWNLOAD, width * height * 4, 0};
    auto* transfer = SDL_CreateGPUTransferBuffer(device_, &info);
    if (!transfer) {
        SDL_SubmitGPUCommandBuffer(commands);
        Require(false, "Create Vulkan frame readback buffer");
    }
    auto* copy = SDL_BeginGPUCopyPass(commands);
    const SDL_GPUTextureRegion region{frame, 0, 0, 0, 0, 0, width, height, 1};
    const SDL_GPUTextureTransferInfo destination{transfer, 0, 0, 0};
    SDL_DownloadFromGPUTexture(copy, &region, &destination);
    SDL_EndGPUCopyPass(copy);
    auto* fence = SDL_SubmitGPUCommandBufferAndAcquireFence(commands);
    bool saved = false;
    if (fence && SDL_WaitForGPUFences(device_, true, &fence, 1)) {
        if (auto* pixels = SDL_MapGPUTransferBuffer(device_, transfer, false)) {
            const auto gpuFormat = SDL_GetGPUSwapchainTextureFormat(device_, window_);
            const auto pixelFormat = gpuFormat == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM ||
                gpuFormat == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM_SRGB ? SDL_PIXELFORMAT_BGRA32 : SDL_PIXELFORMAT_RGBA32;
            std::unique_ptr<SDL_Surface, decltype(&SDL_DestroySurface)> surface(
                SDL_CreateSurfaceFrom(int(width), int(height), pixelFormat, pixels, int(width * 4)), SDL_DestroySurface);
            if (surface) saved = SDL_SaveBMP(surface.get(), capture_.string().c_str());
            surface.reset();
            SDL_UnmapGPUTransferBuffer(device_, transfer);
        }
    }
    if (fence) SDL_ReleaseGPUFence(device_, fence);
    SDL_ReleaseGPUTransferBuffer(device_, transfer);
    Require(saved, "Save Vulkan frame");
}

void Scene::ClearMesh() noexcept
{
    if (!device_) return;
    for (auto* texture : textures_) SDL_ReleaseGPUTexture(device_, texture);
    textures_.clear();
    groups_.clear();
    if (vertices_) SDL_ReleaseGPUBuffer(device_, vertices_);
    if (indices_) SDL_ReleaseGPUBuffer(device_, indices_);
    vertices_ = indices_ = nullptr;
}

void Scene::Close() noexcept
{
    if (!device_) return;
    SDL_WaitForGPUIdle(device_);
    ClearMesh();
    if (depth_) SDL_ReleaseGPUTexture(device_, depth_);
    if (sampler_) SDL_ReleaseGPUSampler(device_, sampler_);
    if (terrainSampler_) SDL_ReleaseGPUSampler(device_, terrainSampler_);
    if (terrain_) SDL_ReleaseGPUGraphicsPipeline(device_, terrain_);
    if (opaque_) SDL_ReleaseGPUGraphicsPipeline(device_, opaque_);
    if (translucent_) SDL_ReleaseGPUGraphicsPipeline(device_, translucent_);
    if (shadow_) SDL_ReleaseGPUGraphicsPipeline(device_, shadow_);
    if (claimed_) SDL_ReleaseWindowFromGPUDevice(device_, window_);
    SDL_DestroyGPUDevice(device_);
    device_ = nullptr;
    depth_ = nullptr;
    sampler_ = terrainSampler_ = nullptr;
    terrain_ = opaque_ = translucent_ = shadow_ = nullptr;
    claimed_ = false;
}

} // namespace orbiter::vulkan
