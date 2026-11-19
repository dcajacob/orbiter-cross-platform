// Licensed under the MIT License
#include "VulkanScene.h"
#include "ShipShaders.h"
#include "SceneFrame.h"

#include <algorithm>
#include <cmath>
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

SDL_GPUShader* Shader(SDL_GPUDevice* device, const std::uint8_t* bytes, std::size_t size, SDL_GPUShaderStage stage, unsigned samplers, unsigned uniforms)
{
    SDL_GPUShaderCreateInfo info{};
    info.code = bytes;
    info.code_size = size;
    info.entrypoint = "main";
    info.format = SDL_GPU_SHADERFORMAT_SPIRV;
    info.stage = stage;
    info.num_samplers = samplers;
    info.num_uniform_buffers = uniforms;
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

// Inward-facing left, right, bottom and top clip planes, in local terrain
// metres. The GPU performs the final near/far and per-triangle clipping.
using ViewPlanes = std::array<std::array<double, 4>, 4>;

ViewPlanes CameraPlanes(const SceneUniform& ground)
{
    ViewPlanes planes{};
    for (unsigned side = 0; side < planes.size(); ++side) {
        auto& plane = planes[side];
        for (unsigned i = 0; i < 4; ++i) {
            const auto* column = ground.projection + 4 * i;
            plane[i] = double(column[3]) + (side % 2 ? -double(column[side / 2]) : double(column[side / 2]));
        }
        // Expand by one metre to keep grazing bounds conservative.
        plane[3] += std::hypot(plane[0], plane[1], plane[2]);
    }
    return planes;
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

void Scene::Open(SDL_Window* window, bool trace)
{
    window_ = window;
    trace_ = trace;
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

    const auto release = [this](SDL_GPUShader* shader) { SDL_ReleaseGPUShader(device_, shader); };
    const auto shader = [&](const auto& code, SDL_GPUShaderStage stage, unsigned samplers, unsigned uniforms) {
        return std::unique_ptr<SDL_GPUShader, decltype(release)>(
            Shader(device_, code, sizeof(code), stage, samplers, uniforms), release);
    };
    const auto vertex = shader(Ship_vert, SDL_GPU_SHADERSTAGE_VERTEX, 0, 1);
    const auto fragment = shader(Ship_frag, SDL_GPU_SHADERSTAGE_FRAGMENT, 1, 1);
    terrain_ = CreatePipeline(vertex.get(), fragment.get(), DrawPass::Terrain);
    opaque_ = CreatePipeline(vertex.get(), fragment.get(), DrawPass::Opaque);
    translucent_ = CreatePipeline(vertex.get(), fragment.get(), DrawPass::Translucent);
    shadow_ = CreatePipeline(vertex.get(), fragment.get(), DrawPass::Shadow);
    const auto receiver = shader(Terrain_frag, SDL_GPU_SHADERSTAGE_FRAGMENT, 2, 0);
    pavement_ = CreatePipeline(vertex.get(), fragment.get(), DrawPass::Pavement);
    groundShadow_ = CreatePipeline(vertex.get(), receiver.get(), DrawPass::GroundShadow);
    pavementShadow_ = CreatePipeline(vertex.get(), receiver.get(), DrawPass::PavementShadow);

    const auto casterVertex = shader(BaseDepth_vert, SDL_GPU_SHADERSTAGE_VERTEX, 0, 1);
    const auto casterFragment = shader(BaseDepth_frag, SDL_GPU_SHADERSTAGE_FRAGMENT, 0, 0);
    SDL_GPUVertexBufferDescription positionBuffer{};
    positionBuffer.pitch = sizeof(Vertex);
    const SDL_GPUVertexAttribute position{0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, offsetof(Vertex, position)};
    SDL_GPUGraphicsPipelineCreateInfo caster{};
    caster.vertex_shader = casterVertex.get();
    caster.fragment_shader = casterFragment.get();
    caster.vertex_input_state = {&positionBuffer, 1, &position, 1};
    caster.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
    caster.depth_stencil_state.enable_depth_test = caster.depth_stencil_state.enable_depth_write = true;
    caster.depth_stencil_state.compare_op = SDL_GPU_COMPAREOP_GREATER;
    caster.target_info.has_depth_stencil_target = true;
    caster.target_info.depth_stencil_format = SDL_GPU_TEXTUREFORMAT_D16_UNORM;
    shadowMapPipeline_ = SDL_CreateGPUGraphicsPipeline(device_, &caster);
    Require(shadowMapPipeline_ != nullptr, "Create base shadow map pipeline");
    sampler.enable_compare = true;
    sampler.compare_op = SDL_GPU_COMPAREOP_GREATER_OR_EQUAL;
    shadowSampler_ = SDL_CreateGPUSampler(device_, &sampler);
    Require(shadowSampler_ != nullptr, "Create base shadow comparison sampler");
    const auto properties = SDL_GetGPUDeviceProperties(device_);
    const auto* name = SDL_GetStringProperty(properties, SDL_PROP_GPU_DEVICE_NAME_STRING, "unknown");
    SceneLog(std::string("Vulkan device: ") + name);
}

SDL_GPUGraphicsPipeline* Scene::CreatePipeline(SDL_GPUShader* vertex, SDL_GPUShader* fragment, DrawPass kind)
{
    const bool decal = kind == DrawPass::Pavement || kind == DrawPass::PavementShadow;
    const bool projected = kind == DrawPass::GroundShadow || kind == DrawPass::PavementShadow;
    const bool blend = decal || projected || kind == DrawPass::Translucent || kind == DrawPass::Shadow;
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
    info.depth_stencil_state.enable_depth_write = !blend || kind == DrawPass::Pavement;
    if (decal || kind == DrawPass::Shadow) {
        info.rasterizer_state.enable_depth_bias = true;
        info.rasterizer_state.depth_bias_constant_factor = 2.0f;
        info.rasterizer_state.depth_bias_slope_factor = 1.0f;
    }
    info.depth_stencil_state.compare_op = SDL_GPU_COMPAREOP_GREATER_OR_EQUAL;
    if (kind == DrawPass::Shadow || projected) {
        // Blend once per pixel even when several projected triangles overlap.
        const SDL_GPUStencilOpState stamp{
            SDL_GPU_STENCILOP_KEEP, SDL_GPU_STENCILOP_REPLACE, SDL_GPU_STENCILOP_KEEP, SDL_GPU_COMPAREOP_NOT_EQUAL};
        info.depth_stencil_state.front_stencil_state = info.depth_stencil_state.back_stencil_state = stamp;
        info.depth_stencil_state.compare_mask = info.depth_stencil_state.write_mask = projected ? 2 : 1;
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

SDL_GPUCopyPass* Scene::UploadPass()
{
    if (!uploadPass_) {
        uploadCommands_ = SDL_AcquireGPUCommandBuffer(device_);
        Require(uploadCommands_ != nullptr, "Acquire Vulkan upload commands");
        uploadPass_ = SDL_BeginGPUCopyPass(uploadCommands_);
    }
    return uploadPass_;
}

SDL_GPUBuffer* Scene::UploadBuffer(SDL_GPUBufferUsageFlags usage, const void* data, std::size_t size)
{
    auto* pass = UploadPass();
    auto* transfer = Upload(device_, data, size);
    const SDL_GPUBufferCreateInfo info{usage, static_cast<Uint32>(size), 0};
    auto* buffer = SDL_CreateGPUBuffer(device_, &info);
    if (!buffer) {
        SDL_ReleaseGPUTransferBuffer(device_, transfer);
        Require(false, "Allocate Vulkan buffer");
    }
    const SDL_GPUTransferBufferLocation source{transfer, 0};
    const SDL_GPUBufferRegion target{buffer, 0, info.size};
    SDL_UploadToGPUBuffer(pass, &source, &target, false);
    SDL_ReleaseGPUTransferBuffer(device_, transfer);
    return buffer;
}

SDL_GPUTexture* Scene::UploadTexture(const TextureData& texture)
{
    auto* pass = UploadPass();
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
    if (!image) {
        SDL_ReleaseGPUTransferBuffer(device_, transfer);
        Require(false, "Allocate Vulkan texture");
    }
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
    SDL_ReleaseGPUTransferBuffer(device_, transfer);
    return image;
}

void Scene::SetShip(const SceneMesh& mesh)
{
    ClearShip();
    if (mesh.indices.empty()) return;
    UploadMesh(mesh, ship_);
    shipIndexCount_ = unsigned(mesh.indices.size());
    vesselVertexBytes_ = Uint32(mesh.vertices.size() * sizeof(Vertex));
    const SDL_GPUBufferCreateInfo shadowVertexInfo{SDL_GPU_BUFFERUSAGE_VERTEX, vesselVertexBytes_, 0};
    shadowVertices_ = SDL_CreateGPUBuffer(device_, &shadowVertexInfo);
    Require(shadowVertices_ != nullptr, "Allocate Vulkan shadow vertices");
    const SDL_GPUTransferBufferCreateInfo uploadInfo{SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD, vesselVertexBytes_, 0};
    shipUpload_ = SDL_CreateGPUTransferBuffer(device_, &uploadInfo);
    Require(shipUpload_ != nullptr, "Allocate Vulkan vessel animation upload buffer");
    shadowUpload_ = SDL_CreateGPUTransferBuffer(device_, &uploadInfo);
    Require(shadowUpload_ != nullptr, "Allocate Vulkan shadow upload buffer");
}

void Scene::UploadMesh(const SceneMesh& mesh, GpuMesh& dest)
{
    dest.vertices = UploadBuffer(SDL_GPU_BUFFERUSAGE_VERTEX, mesh.vertices.data(), mesh.vertices.size() * sizeof(Vertex));
    dest.indices = UploadBuffer(SDL_GPU_BUFFERUSAGE_INDEX, mesh.indices.data(), mesh.indices.size() * sizeof(std::uint32_t));
    TextureData white;
    white.width = white.height = 1;
    white.pixels.assign(4, 255);
    dest.textures.reserve(mesh.textures.size());
    for (auto* texture : mesh.textures) {
        dest.textures.push_back(UploadTexture(texture ? *texture : white));
    }
    dest.groups = mesh.groups;
}

Scene::Bounds::Bounds()
{
    low.fill(std::numeric_limits<float>::max());
    high.fill(std::numeric_limits<float>::lowest());
}

void Scene::Bounds::Include(const Vertex& vertex)
{
    for (unsigned axis = 0; axis < 3; ++axis) {
        low[axis] = std::min(low[axis], vertex.position[axis]);
        high[axis] = std::max(high[axis], vertex.position[axis]);
    }
}

bool Scene::Bounds::InView(const ViewPlanes& planes) const
{
    for (const auto& plane : planes) {
        // If even the furthest corner is outside, the whole tile is clipped.
        double distance = plane[3];
        for (unsigned axis = 0; axis < 3; ++axis)
            distance += plane[axis] * (plane[axis] < 0 ? low[axis] : high[axis]);
        if (distance < 0) return false;
    }
    return true;
}

bool Scene::Bounds::InShadowFootprint(const std::array<float, 16>& m) const
{
    if (low[0] > high[0]) return false;
    // Project this receiver's bounds onto the shadow map. Only overlapping
    // terrain tiles and base surfaces need a second draw.
    for (unsigned row = 0; row < 2; ++row) {
        const auto axis = row * 2;
        const float a = m[4 + row] * low[1], b = m[4 + row] * high[1];
        if (m[12 + row] + m[4 * axis + row] * high[axis] + std::max(a, b) < 0 ||
            m[12 + row] + m[4 * axis + row] * low[axis] + std::min(a, b) > 1) return false;
    }
    return true;
}

void Scene::AddBase(unsigned index, const SceneMesh& mesh, bool shadows)
{
    auto& base = bases_.try_emplace(index).first->second;
    if (mesh.indices.empty()) return;
    UploadMesh(mesh, base.mesh);
    // Stock structures often split one surface into many consecutive groups.
    // Coalesce identical draw states without changing triangle or blending order.
    base.mesh.groups.clear();
    for (const auto& group : mesh.groups) {
        if (!base.mesh.groups.empty()) {
            auto& last = base.mesh.groups.back();
            if (last.firstIndex + last.indexCount == group.firstIndex && last.pass == group.pass &&
                last.textureIndex == group.textureIndex && last.material.diffuse == group.material.diffuse &&
                last.material.ambient == group.material.ambient && last.material.emission == group.material.emission &&
                last.material.specular == group.material.specular) {
                last.indexCount += group.indexCount;
                continue;
            }
        }
        base.mesh.groups.push_back(group);
    }
    for (const auto& group : mesh.groups) {
        if (group.pass != DrawPass::BaseTile && group.pass != DrawPass::Pavement) continue;
        for (unsigned i = group.firstIndex; i < group.firstIndex + group.indexCount; ++i)
            base.surfaces.Include(mesh.vertices[mesh.indices[i]]);
    }
    if (!shadows) return;
    std::vector<std::uint32_t> indices;
    for (const auto& group : mesh.groups) {
        if (!group.castsShadow) continue;
        const auto begin = mesh.indices.begin() + group.firstIndex;
        indices.insert(indices.end(), begin, begin + group.indexCount);
    }
    if (indices.empty()) return;
    for (const auto index : indices) base.casters.Include(mesh.vertices[index]);
    base.casterIndices = UploadBuffer(SDL_GPU_BUFFERUSAGE_INDEX, indices.data(), indices.size() * sizeof(indices[0]));
    base.casterCount = unsigned(indices.size());
    SDL_GPUTextureCreateInfo map{};
    map.type = SDL_GPU_TEXTURETYPE_2D;
    map.format = SDL_GPU_TEXTUREFORMAT_D16_UNORM;
    map.usage = SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET | SDL_GPU_TEXTUREUSAGE_SAMPLER;
    map.width = map.height = 4096;
    map.layer_count_or_depth = map.num_levels = 1;
    base.shadowMap = SDL_CreateGPUTexture(device_, &map);
    Require(base.shadowMap != nullptr, "Allocate base shadow map");
}

void Scene::PrepareBaseShadow(SDL_GPUCommandBuffer* commands, Base& base, const SceneUniform& ground)
{
    base.sunlit = base.shadowMap && ground.light[1] >= 0.07f;
    if (!base.sunlit) return;
    const float sx = ground.light[0] / ground.light[1], sz = ground.light[2] / ground.light[1];
    // Reuse the map until the tip of the highest shadow moves by about half a metre.
    const float height = base.casters.high[1] - base.casters.low[1] + 2;
    if (!base.mapValid || std::max(std::abs(sx - base.slopeX), std::abs(sz - base.slopeZ)) * height > 0.5f) {
        for (unsigned axis : {0u, 2u}) {
            const auto row = axis / 2;
            const float slope = axis == 0 ? sx : sz;
            const float a = slope * base.casters.low[1], b = slope * base.casters.high[1];
            const float lo = base.casters.low[axis] - std::max(a, b) - 2;
            const float hi = base.casters.high[axis] - std::min(a, b) + 2;
            base.transform[4 * axis + row] = 1 / (hi - lo);
            base.transform[4 + row] = -slope / (hi - lo);
            base.transform[12 + row] = -lo / (hi - lo);
        }
        base.transform[6] = 1 / height;
        base.transform[14] = (1 - base.casters.low[1]) / height;
        base.transform[15] = 1;
        SDL_GPUDepthStencilTargetInfo target{};
        target.texture = base.shadowMap;
        target.load_op = SDL_GPU_LOADOP_CLEAR;
        target.store_op = SDL_GPU_STOREOP_STORE;
        auto* pass = SDL_BeginGPURenderPass(commands, nullptr, 0, &target);
        SDL_BindGPUGraphicsPipeline(pass, shadowMapPipeline_);
        SDL_PushGPUVertexUniformData(commands, 0, base.transform.data(), sizeof(base.transform));
        const SDL_GPUBufferBinding vb{base.mesh.vertices, 0}, ib{base.casterIndices, 0};
        SDL_BindGPUVertexBuffers(pass, 0, &vb, 1);
        SDL_BindGPUIndexBuffer(pass, &ib, SDL_GPU_INDEXELEMENTSIZE_32BIT);
        SDL_DrawGPUIndexedPrimitives(pass, base.casterCount, 1, 0, 0, 0);
        SDL_EndGPURenderPass(pass);
        base.slopeX = sx;
        base.slopeZ = sz;
        base.mapValid = mapUpdated_ = true;
    }
}

void Scene::Release(GroundTile& tile) noexcept
{
    if (tile.vertices) SDL_ReleaseGPUBuffer(device_, tile.vertices);
    if (tile.indices) SDL_ReleaseGPUBuffer(device_, tile.indices);
    if (tile.texture) SDL_ReleaseGPUTexture(device_, tile.texture);
}

void Scene::StageTile(const TileKey& key, const TerrainMesh& mesh)
{
    auto& tile = tiles_.try_emplace(key).first->second;
    tile.vertices = UploadBuffer(SDL_GPU_BUFFERUSAGE_VERTEX, mesh.vertices.data(),
        mesh.vertices.size() * sizeof(Vertex));
    tile.indices = UploadBuffer(SDL_GPU_BUFFERUSAGE_INDEX, mesh.indices.data(),
        mesh.indices.size() * sizeof(std::uint32_t));
    tile.texture = UploadTexture(mesh.texture);
    tile.indexCount = unsigned(mesh.indices.size());
    for (const auto& vertex : mesh.vertices) tile.bounds.Include(vertex);
}

void Scene::SelectTiles(const std::set<TileKey>& visible, const std::set<TileKey>& pending)
{
    for (auto it = tiles_.begin(); it != tiles_.end();) {
        it->second.visible = visible.count(it->first) != 0;
        if (it->second.visible || pending.count(it->first)) ++it;
        else {
            Release(it->second);
            it = tiles_.erase(it);
        }
    }
}

void Scene::SetShadow(const std::vector<Vertex>& vertices)
{
    showShadow_ = false;
    if (vertices.empty()) return;
    UpdateVesselVertices(vertices, shadowVertices_, shadowUpload_);
    showShadow_ = true;
}

void Scene::SetShipPose(const std::vector<Vertex>& vertices)
{
    UpdateVesselVertices(vertices, ship_.vertices, shipUpload_);
}

void Scene::UpdateVesselVertices(const std::vector<Vertex>& vertices, SDL_GPUBuffer* buffer, SDL_GPUTransferBuffer* transfer)
{
    if (vertices.size() * sizeof(Vertex) != vesselVertexBytes_)
        throw std::runtime_error("Vulkan pose vertex count differs from the vessel mesh");
    auto* mapped = SDL_MapGPUTransferBuffer(device_, transfer, true);
    Require(mapped != nullptr, "Map Vulkan pose upload");
    std::memcpy(mapped, vertices.data(), vesselVertexBytes_);
    SDL_UnmapGPUTransferBuffer(device_, transfer);
    auto* copy = UploadPass();
    const SDL_GPUTransferBufferLocation source{transfer, 0};
    const SDL_GPUBufferRegion target{buffer, 0, vesselVertexBytes_};
    SDL_UploadToGPUBuffer(copy, &source, &target, true);
}

void Scene::DrawMesh(SDL_GPURenderPass* pass, SDL_GPUCommandBuffer* commands, const GpuMesh& mesh, DrawPass kind)
{
    if (mesh.groups.empty()) return;
    const SDL_GPUBufferBinding vertex{mesh.vertices, 0};
    const SDL_GPUBufferBinding index{mesh.indices, 0};
    SDL_BindGPUVertexBuffers(pass, 0, &vertex, 1);
    SDL_BindGPUIndexBuffer(pass, &index, SDL_GPU_INDEXELEMENTSIZE_32BIT);
    for (const auto& group : mesh.groups) {
        if (group.pass != kind) continue;
        const SDL_GPUTextureSamplerBinding binding{mesh.textures.at(group.textureIndex), kind == DrawPass::BaseTile ? terrainSampler_ : sampler_};
        SDL_BindGPUFragmentSamplers(pass, 0, &binding, 1);
        SDL_PushGPUFragmentUniformData(commands, 0, &group.material, sizeof(group.material));
        SDL_DrawGPUIndexedPrimitives(pass, group.indexCount, 1, group.firstIndex, 0, 0);
    }
}

void Scene::DrawTile(SDL_GPURenderPass* pass, const GroundTile& tile)
{
    const SDL_GPUBufferBinding vertex{tile.vertices, 0};
    const SDL_GPUBufferBinding index{tile.indices, 0};
    const SDL_GPUTextureSamplerBinding binding{tile.texture, terrainSampler_};
    SDL_BindGPUVertexBuffers(pass, 0, &vertex, 1);
    SDL_BindGPUIndexBuffer(pass, &index, SDL_GPU_INDEXELEMENTSIZE_32BIT);
    SDL_BindGPUFragmentSamplers(pass, 0, &binding, 1);
    SDL_DrawGPUIndexedPrimitives(pass, tile.indexCount, 1, 0, 0, 0);
}

void Scene::DrawGroundShadows(SDL_GPURenderPass* pass, SDL_GPUCommandBuffer* commands, SceneUniform ground)
{
    SDL_SetGPUStencilReference(pass, 2);
    for (const auto& entry : bases_) {
        const auto& caster = entry.second;
        if (!caster.sunlit) continue;
        ground.shadowTransform = caster.transform;
        ground.shadowTransform[14] += 0.2f * caster.transform[6];
        SDL_PushGPUVertexUniformData(commands, 0, &ground, sizeof(ground));
        const SDL_GPUTextureSamplerBinding map{caster.shadowMap, shadowSampler_};
        SDL_BindGPUGraphicsPipeline(pass, groundShadow_);
        SDL_BindGPUFragmentSamplers(pass, 1, &map, 1);
        for (const auto& tile : tiles_) {
            if (tile.second.inView && tile.second.bounds.InShadowFootprint(caster.transform))
                DrawTile(pass, tile.second);
        }
        SDL_BindGPUGraphicsPipeline(pass, pavementShadow_);
        for (const auto& receiver : bases_) {
            if (!receiver.second.surfaces.InShadowFootprint(caster.transform)) continue;
            DrawMesh(pass, commands, receiver.second.mesh, DrawPass::BaseTile);
            DrawMesh(pass, commands, receiver.second.mesh, DrawPass::Pavement);
        }
    }
}

bool Scene::Present(const SceneUniform& ship, const SceneUniform& ground, const std::filesystem::path& sample)
{
    timings_ = {};
    mapUpdated_ = false;
    // Record transfers and dependent draws in submission order. SDL tracks
    // the resources referenced by the command buffer until execution finishes.
    auto* commands = uploadCommands_;
    if (commands) {
        SDL_EndGPUCopyPass(uploadPass_);
        uploadCommands_ = nullptr;
        uploadPass_ = nullptr;
    } else {
        commands = SDL_AcquireGPUCommandBuffer(device_);
        Require(commands != nullptr, "Acquire Vulkan commands");
    }
    SDL_GPUTexture* back = nullptr;
    unsigned width = 0;
    unsigned height = 0;
    const auto beforeAcquire = SDL_GetTicksNS();
    // SDL's Vulkan backend waits for the oldest frame slot and retires GPU
    // resources before acquiring the next presentation image. Split those
    // stages only when profiling. Keep blocking acquisition in both paths.
    if (trace_) {
        if (!SDL_WaitForGPUSwapchain(device_, window_)) {
            SDL_CancelGPUCommandBuffer(commands);
            Require(false, "Wait for Vulkan frame slot");
        }
        timings_.fenceNS = SDL_GetTicksNS() - beforeAcquire;
    }
    const bool acquired = SDL_WaitAndAcquireGPUSwapchainTexture(commands, window_, &back, &width, &height);
    const auto acquiredAt = SDL_GetTicksNS();
    timings_.acquireNS = acquiredAt - beforeAcquire;
    if (!acquired) {
        SDL_CancelGPUCommandBuffer(commands);
        Require(false, "Acquire Vulkan swapchain image");
    }
    if (!back) return SDL_SubmitGPUCommandBuffer(commands);
    ResizeDepth(width, height);

    const bool capture = (!capture_.empty() || !sample.empty()) && !ship_.groups.empty();
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
    color.clear_color = {0.42f, 0.61f, 0.80f, 1.0f};
    color.load_op = SDL_GPU_LOADOP_CLEAR;
    color.store_op = SDL_GPU_STOREOP_STORE;
    SDL_GPUDepthStencilTargetInfo depth{};
    depth.texture = depth_;
    depth.clear_depth = 0;
    depth.load_op = SDL_GPU_LOADOP_CLEAR;
    depth.store_op = SDL_GPU_STOREOP_DONT_CARE;
    depth.stencil_load_op = SDL_GPU_LOADOP_CLEAR;
    depth.stencil_store_op = SDL_GPU_STOREOP_DONT_CARE;
    for (auto& entry : bases_) PrepareBaseShadow(commands, entry.second, ground);
    auto* pass = SDL_BeginGPURenderPass(commands, &color, 1, &depth);
    SDL_BindGPUGraphicsPipeline(pass, terrain_);
    auto surfaceFrame = ground;
    surfaceFrame.light[0] = surfaceFrame.light[2] = 0;
    surfaceFrame.light[1] = 1;
    SDL_PushGPUVertexUniformData(commands, 0, &surfaceFrame, sizeof(surfaceFrame));
    const MaterialUniform surface{{1, 1, 1, 1}, {0, 0, 0, 1}};
    SDL_PushGPUFragmentUniformData(commands, 0, &surface, sizeof(surface));
    const auto planes = CameraPlanes(ground);
    for (auto& [key, tile] : tiles_) {
        tile.inView = tile.visible && tile.bounds.InView(planes);
        if (!tile.inView) continue;
        DrawTile(pass, tile);
        ++timings_.terrainDraws;
    }
    SDL_BindGPUGraphicsPipeline(pass, pavement_);
    SDL_PushGPUVertexUniformData(commands, 0, &ground, sizeof(ground));
    for (auto kind : {DrawPass::BaseTile, DrawPass::Pavement}) {
        for (const auto& entry : bases_) DrawMesh(pass, commands, entry.second.mesh, kind);
    }
    DrawGroundShadows(pass, commands, ground);
    if (showShadow_) {
        SDL_PushGPUVertexUniformData(commands, 0, &surfaceFrame, sizeof(surfaceFrame));
        SDL_BindGPUGraphicsPipeline(pass, shadow_);
        SDL_SetGPUStencilReference(pass, 1);
        const SDL_GPUBufferBinding vertex{shadowVertices_, 0};
        const SDL_GPUBufferBinding index{ship_.indices, 0};
        const SDL_GPUTextureSamplerBinding binding{ship_.textures.front(), sampler_};
        const MaterialUniform shade{{0.015f, 0.015f, 0.015f, 0.63f}, {0, 0, 0, 2}};
        SDL_BindGPUVertexBuffers(pass, 0, &vertex, 1);
        SDL_BindGPUIndexBuffer(pass, &index, SDL_GPU_INDEXELEMENTSIZE_32BIT);
        SDL_BindGPUFragmentSamplers(pass, 0, &binding, 1);
        SDL_PushGPUFragmentUniformData(commands, 0, &shade, sizeof(shade));
        SDL_DrawGPUIndexedPrimitives(pass, shipIndexCount_, 1, 0, 0, 0);
    }
    for (auto kind : {DrawPass::Opaque, DrawPass::Translucent}) {
        SDL_BindGPUGraphicsPipeline(pass, kind == DrawPass::Opaque ? opaque_ : translucent_);
        SDL_PushGPUVertexUniformData(commands, 0, &ground, sizeof(ground));
        for (const auto& entry : bases_) DrawMesh(pass, commands, entry.second.mesh, kind);
        SDL_PushGPUVertexUniformData(commands, 0, &ship, sizeof(ship));
        DrawMesh(pass, commands, ship_, kind);
    }
    SDL_EndGPURenderPass(pass);
    if (!capture) {
        const auto beforeSubmit = SDL_GetTicksNS();
        const bool submitted = SDL_SubmitGPUCommandBuffer(commands);
        timings_.encodeNS = beforeSubmit - acquiredAt;
        timings_.submitNS = SDL_GetTicksNS() - beforeSubmit;
        return submitted;
    }
    try {
        SaveFrame(commands, frame, back, width, height, sample);
    } catch (...) {
        SDL_ReleaseGPUTexture(device_, frame);
        throw;
    }
    SDL_ReleaseGPUTexture(device_, frame);
    capture_.clear();
    return true;
}

void Scene::SaveFrame(SDL_GPUCommandBuffer* commands, SDL_GPUTexture* frame, SDL_GPUTexture* back,
    unsigned width, unsigned height, const std::filesystem::path& sample)
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
            if (surface) {
                saved = (capture_.empty() || SDL_SaveBMP(surface.get(), capture_.string().c_str())) &&
                    (sample.empty() || SDL_SaveBMP(surface.get(), sample.string().c_str()));
            }
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
    ClearGround();
    ClearShip();
}

void Scene::ClearGround() noexcept
{
    for (auto& entry : tiles_) Release(entry.second);
    tiles_.clear();
    while (!bases_.empty()) RemoveBase(bases_.begin()->first);
}

void Scene::Release(GpuMesh& mesh) noexcept
{
    for (auto* texture : mesh.textures) SDL_ReleaseGPUTexture(device_, texture);
    mesh.textures.clear();
    mesh.groups.clear();
    if (mesh.vertices) SDL_ReleaseGPUBuffer(device_, mesh.vertices);
    if (mesh.indices) SDL_ReleaseGPUBuffer(device_, mesh.indices);
    mesh.vertices = mesh.indices = nullptr;
}

void Scene::RemoveBase(unsigned index) noexcept
{
    const auto it = bases_.find(index);
    if (it == bases_.end()) return;
    auto& base = it->second;
    Release(base.mesh);
    if (base.casterIndices) SDL_ReleaseGPUBuffer(device_, base.casterIndices);
    if (base.shadowMap) SDL_ReleaseGPUTexture(device_, base.shadowMap);
    bases_.erase(it);
}

void Scene::ClearShip() noexcept
{
    Release(ship_);
    if (shadowVertices_) SDL_ReleaseGPUBuffer(device_, shadowVertices_);
    if (shipUpload_) SDL_ReleaseGPUTransferBuffer(device_, shipUpload_);
    if (shadowUpload_) SDL_ReleaseGPUTransferBuffer(device_, shadowUpload_);
    shadowVertices_ = nullptr;
    shadowUpload_ = shipUpload_ = nullptr;
    shipIndexCount_ = vesselVertexBytes_ = 0;
    showShadow_ = false;
}

void Scene::Close() noexcept
{
    if (!device_) return;
    if (uploadCommands_) {
        SDL_EndGPUCopyPass(uploadPass_);
        SDL_CancelGPUCommandBuffer(uploadCommands_);
        uploadPass_ = nullptr;
        uploadCommands_ = nullptr;
    }
    SDL_WaitForGPUIdle(device_);
    capture_.clear();
    ClearMesh();
    if (depth_) SDL_ReleaseGPUTexture(device_, depth_);
    if (sampler_) SDL_ReleaseGPUSampler(device_, sampler_);
    if (terrainSampler_) SDL_ReleaseGPUSampler(device_, terrainSampler_);
    if (shadowSampler_) SDL_ReleaseGPUSampler(device_, shadowSampler_);
    if (shadowMapPipeline_) SDL_ReleaseGPUGraphicsPipeline(device_, shadowMapPipeline_);
    if (groundShadow_) SDL_ReleaseGPUGraphicsPipeline(device_, groundShadow_);
    if (pavementShadow_) SDL_ReleaseGPUGraphicsPipeline(device_, pavementShadow_);
    if (pavement_) SDL_ReleaseGPUGraphicsPipeline(device_, pavement_);
    shadowSampler_ = nullptr;
    shadowMapPipeline_ = groundShadow_ = pavementShadow_ = pavement_ = nullptr;
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
