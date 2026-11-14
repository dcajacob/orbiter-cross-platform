// Licensed under the MIT License
#include "OrbiterScene.h"

#include <algorithm>
#include <cmath>
#include <cctype>
#include <limits>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace orbiter::vulkan {
#include "SurfaceCopy.inc"
namespace {

constexpr auto defaultIndex = std::numeric_limits<std::uint32_t>::max();
constexpr auto inheritedIndex = defaultIndex - 1;

VECTOR3 Subtract(const VECTOR3& lhs, const VECTOR3& rhs)
{
    return {lhs.x - rhs.x, lhs.y - rhs.y, lhs.z - rhs.z};
}

double Dot(const VECTOR3& lhs, const VECTOR3& rhs)
{
    return lhs.x * rhs.x + lhs.y * rhs.y + lhs.z * rhs.z;
}

SceneUniform MakeUniform(OBJHANDLE focus, const VECTOR3& offset, unsigned width, unsigned height)
{
    SceneUniform uniform{};
    VECTOR3 position, camera, sun;
    MATRIX3 worldRotation, cameraRotation;
    oapiGetGlobalPos(focus, &position);
    oapiCameraGlobalPos(&camera);
    oapiCameraRotationMatrix(&cameraRotation);
    oapiGetRotationMatrix(focus, &worldRotation);
    if (const auto body = oapiGetGbodyByIndex(0)) oapiGetGlobalPos(body, &sun);
    else sun = {};
    const VECTOR3 columns[] = {
        {worldRotation.m11, worldRotation.m21, worldRotation.m31},
        {worldRotation.m12, worldRotation.m22, worldRotation.m32},
        {worldRotation.m13, worldRotation.m23, worldRotation.m33}
    };
    const VECTOR3 axes[] = {
        {cameraRotation.m11, cameraRotation.m21, cameraRotation.m31},
        {cameraRotation.m12, cameraRotation.m22, cameraRotation.m32},
        {cameraRotation.m13, cameraRotation.m23, cameraRotation.m33}
    };
    auto displacement = Subtract(position, camera);
    displacement.x += columns[0].x * offset.x + columns[1].x * offset.y + columns[2].x * offset.z;
    displacement.y += columns[0].y * offset.x + columns[1].y * offset.y + columns[2].y * offset.z;
    displacement.z += columns[0].z * offset.x + columns[1].z * offset.y + columns[2].z * offset.z;
    const auto sunlight = Subtract(sun, position);
    const double distance = std::sqrt(Dot(sunlight, sunlight));
    const double vertical = 1 / std::tan(oapiCameraAperture());
    const double horizontal = vertical * height / width;
    constexpr double nearPlane = 0.1;
    constexpr double farPlane = 10000.0;
    for (unsigned i = 0; i < 4; ++i) {
        const auto& v = i == 3 ? displacement : columns[i];
        const auto z = Dot(v, axes[2]);
        uniform.projection[4 * i] = float(horizontal * Dot(v, axes[0]));
        uniform.projection[4 * i + 1] = float(vertical * Dot(v, axes[1]));
        uniform.projection[4 * i + 2] = float((z - (i == 3 ? nearPlane : 0.0)) * farPlane / (farPlane - nearPlane));
        uniform.projection[4 * i + 3] = float(z);
        if (i < 3) uniform.light[i] = distance > 0 ? float(Dot(columns[i], sunlight) / distance) : 0.0f;
    }
    return uniform;
}

} // namespace

OrbiterScene::~OrbiterScene()
{
    Close();
}

SURFHANDLE OrbiterScene::Load(const std::filesystem::path& path)
{
    for (auto& entry : surfaces_) {
        if (entry.second->path == path) {
            ++entry.second->references;
            return entry.first;
        }
    }
    auto suffix = path.extension().string();
    std::transform(suffix.begin(), suffix.end(), suffix.begin(),
        [](unsigned char c) { return char(std::tolower(c)); });
    if (suffix == ".dds") return Add(ReadDds(path));
    if (suffix != ".bmp") return nullptr;
    std::unique_ptr<SDL_Surface, decltype(&SDL_DestroySurface)> source(SDL_LoadBMP(path.string().c_str()), SDL_DestroySurface);
    if (!source) return nullptr;
    std::unique_ptr<SDL_Surface, decltype(&SDL_DestroySurface)> image(
        SDL_ConvertSurface(source.get(), SDL_PIXELFORMAT_RGBA32), SDL_DestroySurface);
    if (!image) return nullptr;
    TextureData data;
    data.path = path;
    data.width = unsigned(image->w);
    data.height = unsigned(image->h);
    const auto* pixels = static_cast<const std::uint8_t*>(image->pixels);
    for (unsigned row = 0; row < data.height; ++row) {
        const auto* start = pixels + row * image->pitch;
        data.pixels.insert(data.pixels.end(), start, start + 4 * data.width);
    }
    return Add(std::move(data));
}

SURFHANDLE OrbiterScene::Create(unsigned width, unsigned height)
{
    if (!width || !height || width > 4096 || height > 4096) return nullptr;
    TextureData data;
    data.width = width;
    data.height = height;
    data.pixels.resize(std::size_t(width) * height * 4);
    return Add(std::move(data));
}

SURFHANDLE OrbiterScene::Add(TextureData data)
{
    auto resource = std::make_unique<TextureData>(std::move(data));
    auto* handle = resource.get();
    surfaces_.emplace(handle, std::move(resource));
    return handle;
}

const TextureData* OrbiterScene::Lookup(SURFHANDLE surface) const
{
    const auto it = surfaces_.find(surface);
    return it != surfaces_.end() ? it->second.get() : nullptr;
}

void OrbiterScene::Retain(SURFHANDLE surface)
{
    const auto it = surfaces_.find(surface);
    if (it != surfaces_.end()) ++it->second->references;
}

bool OrbiterScene::Release(SURFHANDLE surface)
{
    const auto it = surfaces_.find(surface);
    if (it == surfaces_.end()) return false;
    if (--it->second->references == 0) surfaces_.erase(it);
    return true;
}

bool OrbiterScene::Size(SURFHANDLE surface, unsigned& width, unsigned& height) const
{
    const auto* data = Lookup(surface);
    if (!data) return false;
    width = data->width;
    height = data->height;
    return true;
}

bool OrbiterScene::Fill(SURFHANDLE surface, unsigned x, unsigned y, unsigned width, unsigned height, std::uint32_t color)
{
    const auto target = surfaces_.find(surface);
    if (target == surfaces_.end()) return false;
    auto& image = *target->second;
    if (image.blockBytes || x > image.width || y > image.height || width > image.width - x || height > image.height - y)
        return false;
    const std::uint8_t rgba[] = {std::uint8_t(color), std::uint8_t(color >> 8), std::uint8_t(color >> 16), 255};
    for (unsigned row = y; row < y + height; ++row)
        for (unsigned col = x; col < x + width; ++col)
            std::memcpy(image.pixels.data() + (std::size_t(row) * image.width + col) * 4, rgba, 4);
    return true;
}

bool OrbiterScene::Blit(SURFHANDLE target, unsigned x, unsigned y, SURFHANDLE source,
    unsigned sx, unsigned sy, unsigned width, unsigned height)
{
    const auto dest = surfaces_.find(target);
    const auto* input = Lookup(source);
    if (dest == surfaces_.end() || !input) return false;
    auto& output = *dest->second;
    if (input == &output) return false;
    if (output.format != SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM || output.blockBytes ||
        x > output.width || y > output.height || sx > input->width || sy > input->height)
        return false;
    width = std::min({width, output.width - x, input->width - sx});
    height = std::min({height, output.height - y, input->height - sy});
    for (unsigned row = 0; row < height; ++row) {
        auto* pixels = output.pixels.data() + (std::size_t(y + row) * output.width + x) * 4;
        if (!input->blockBytes && input->format == output.format) {
            std::memcpy(pixels, input->pixels.data() + (std::size_t(sy + row) * input->width + sx) * 4, 4 * width);
            continue;
        }
        for (unsigned col = 0; col < width; ++col) {
            const auto rgba = ReadPixel(*input, sx + col, sy + row);
            std::memcpy(pixels + 4 * col, rgba.data(), rgba.size());
        }
    }
    return true;
}

void OrbiterScene::Open(SDL_Window* window)
{
    scene_.Open(window);
}

void OrbiterScene::CaptureFocus()
{
    auto* vessel = oapiGetFocusInterface();
    if (!vessel || std::strcmp(vessel->GetClassName(), "DG-S"))
        throw std::runtime_error("The Runway 33 Vulkan client requires the stock DG-S focus vessel");
    const auto mesh = vessel->GetMeshTemplate(0);
    if (!mesh || !(vessel->GetMeshVisibilityMode(0) & MESHVIS_EXTERNAL))
        throw std::runtime_error("Focus DG-S has no exterior mesh");
    focus_ = vessel->GetHandle();
    vessel->GetMeshOffset(0, offset_);
    ShipMesh ship;
    const auto materials = oapiMeshMaterialCount(mesh);
    const auto textures = oapiMeshTextureCount(mesh);
    unsigned materialIndex = defaultIndex;
    unsigned textureIndex = defaultIndex;
    std::map<SURFHANDLE, unsigned> textureSlots;

    for (unsigned i = 0, n = oapiMeshGroupCount(mesh); i < n; ++i) {
        const auto* group = oapiMeshGroup(mesh, i);
        if (!group) continue;
        if (group->MtrlIdx != inheritedIndex) materialIndex = group->MtrlIdx;
        if (group->TexIdx != inheritedIndex) textureIndex = group->TexIdx;
        if ((group->UsrFlag & 2) || !group->nVtx || !group->nIdx) continue;
        MaterialUniform material;
        if (materialIndex < materials) {
            const auto* mat = oapiMeshMaterial(mesh, materialIndex);
            if (mat) {
                const float values[] = {mat->diffuse.r, mat->diffuse.g, mat->diffuse.b, mat->diffuse.a};
                std::copy(std::begin(values), std::end(values), material.diffuse);
                material.emission[0] = mat->emissive.r;
                material.emission[1] = mat->emissive.g;
                material.emission[2] = mat->emissive.b;
            }
        }
        unsigned gpuTexture = 0;
        if (textureIndex < textures) {
            const auto handle = oapiGetTextureHandle(mesh, textureIndex + 1);
            const auto* texture = Lookup(handle);
            if (texture) {
                const auto slot = textureSlots.emplace(handle, unsigned(ship.textures.size()));
                if (slot.second) ship.textures.push_back(texture);
                gpuTexture = slot.first->second;
            }
        }
        const auto startVertex = unsigned(ship.vertices.size());
        ship.groups.push_back({unsigned(ship.indices.size()), group->nIdx, gpuTexture, material, material.diffuse[3] < 0.999f});
        for (unsigned j = 0; j < group->nVtx; ++j) {
            const auto& v = group->Vtx[j];
            ship.vertices.push_back({{v.x, v.y, v.z}, {v.nx, v.ny, v.nz}, {v.tu, v.tv}});
        }
        for (unsigned j = 0; j < group->nIdx; ++j) {
            if (group->Idx[j] >= group->nVtx) throw std::runtime_error("Invalid exterior mesh index");
            ship.indices.push_back(startVertex + group->Idx[j]);
        }
    }
    if (ship.textures.size() <= 1)
        throw std::runtime_error("The DG-S exterior has no loaded textures");
    std::clog << "Runway33 focus: " << vessel->GetName() << ", " << vessel->GetClassName()
              << "; time=" << oapiGetSimTime() << "; aperture=" << oapiCameraAperture() << '\n';
    scene_.SetShip(ship);
}

void OrbiterScene::ClearFocus() noexcept
{
    focus_ = nullptr;
    scene_.ClearShip();
}

bool OrbiterScene::Present(unsigned width, unsigned height)
{
    if (!width || !height) return true;
    const auto uniform = focus_ ? MakeUniform(focus_, offset_, width, height) : SceneUniform{};
    return scene_.Present(uniform);
}

void OrbiterScene::Close() noexcept
{
    scene_.Close();
    focus_ = nullptr;
}

} // namespace orbiter::vulkan
