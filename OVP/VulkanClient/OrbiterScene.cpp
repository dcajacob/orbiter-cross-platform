// Licensed under the MIT License
#include "OrbiterScene.h"

#include <algorithm>
#include <cmath>
#include <cctype>
#include <limits>
#include <cstring>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace orbiter::vulkan {
#include "SurfaceCopy.inc"
namespace {

constexpr auto defaultIndex = std::numeric_limits<std::uint32_t>::max();
constexpr auto inheritedIndex = defaultIndex - 1;

SceneUniform MakeUniform(const SceneFrame& frame, unsigned width, unsigned height)
{
    SceneUniform uniform{};
    VECTOR3 camera;
    MATRIX3 cameraRotation;
    oapiCameraGlobalPos(&camera);
    oapiCameraRotationMatrix(&cameraRotation);
    const auto axes = Axes(cameraRotation);
    const auto displacement = Subtract(frame.origin, camera);
    const auto sunlight = Subtract(SunPosition(), frame.origin);
    const double distance = std::sqrt(Dot(sunlight, sunlight));
    const double vertical = 1 / std::tan(oapiCameraAperture());
    const double horizontal = vertical * height / width;
    constexpr double nearPlane = 0.1;
    constexpr double farPlane = 85000.0;
    for (unsigned i = 0; i < 4; ++i) {
        const auto& v = i == 3 ? displacement : frame.axes[i];
        const auto z = Dot(v, axes[2]);
        uniform.projection[4 * i] = float(horizontal * Dot(v, axes[0]));
        uniform.projection[4 * i + 1] = float(vertical * Dot(v, axes[1]));
        // Reverse Z preserves floating-point depth precision for distant ground and its shadow.
        uniform.projection[4 * i + 2] = float(((i == 3 ? farPlane : 0.0) - z) * nearPlane / (farPlane - nearPlane));
        uniform.projection[4 * i + 3] = float(z);
        if (i < 3) uniform.light[i] = distance > 0 ? float(Dot(v, sunlight) / distance) : 0.0f;
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
    if (const char* path = SDL_getenv("ORBITER_VULKAN_FRAME_TRACE"); path && *path) {
        frameTrace_.open(std::filesystem::path(path));
        if (!frameTrace_) throw std::runtime_error("Cannot open Vulkan frame trace");
        frameTrace_ << "sim_seconds,interval_ms,scene_ms,terrain_ms,tiles_staged,tiles_switched,pose_uploaded,shadow_drawn\n";
    }
    previousFrame_ = 0;
}

void OrbiterScene::CaptureFocus(const std::filesystem::path& archive)
{
    auto* vessel = oapiGetFocusInterface();
    if (!vessel || std::strcmp(vessel->GetClassName(), "DG-S"))
        throw std::runtime_error("The Runway 33 Vulkan client requires the stock DG-S focus vessel");
    const auto mesh = vessel->GetMeshTemplate(0);
    if (!mesh || !(vessel->GetMeshVisibilityMode(0) & MESHVIS_EXTERNAL))
        throw std::runtime_error("Focus DG-S has no exterior mesh");
    focus_ = vessel->GetHandle();
    vessel->GetMeshOffset(0, offset_);
    SceneMesh ship;
    const auto materials = oapiMeshMaterialCount(mesh);
    const auto textures = oapiMeshTextureCount(mesh);
    unsigned materialIndex = defaultIndex;
    unsigned textureIndex = defaultIndex;
    std::map<SURFHANDLE, unsigned> textureSlots;
    std::vector<VertexRange> groups(oapiMeshGroupCount(mesh));

    for (unsigned i = 0; i < groups.size(); ++i) {
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
        groups[i] = {startVertex, group->nVtx};
        const auto pass = material.diffuse[3] < 0.999f ? DrawPass::Translucent : DrawPass::Opaque;
        ship.groups.push_back({unsigned(ship.indices.size()), group->nIdx, gpuTexture, material, pass});
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
    terrain_.Open(archive, ShipFrame().origin);
    scene_.SetShip(ship);
    pose_.Reset(std::move(ship.vertices), std::move(groups));
}

SceneFrame OrbiterScene::ShipFrame() const
{
    auto frame = ObjectFrame(focus_);
    frame.origin = frame.ToGlobal(offset_);
    return frame;
}

void OrbiterScene::ClearFocus() noexcept
{
    focus_ = nullptr;
    scene_.ClearMesh();
    terrain_.Close();
    pose_.Reset({}, {});
    shadowVertices_.clear();
    shadowTime_.reset();
    loggedLiftoff_ = false;
}

bool OrbiterScene::Present(unsigned width, unsigned height)
{
    if (!width || !height) return true;
    if (!focus_) return scene_.Present({}, {});
    const auto start = SDL_GetTicksNS();
    const auto ship = ShipFrame();
    const auto simTime = oapiGetSimTime();
    const auto groundFrame = terrain_.Frame();
    auto* vessel = oapiGetVesselInterface(focus_);
    const bool poseChanged = pose_.Update(*vessel);
    if (poseChanged) scene_.SetShipPose(pose_.Vertices());
    TerrainUpdate tiles;
    Uint64 terrainTime = 0;
    if (shadowTime_ != simTime || poseChanged) {
        const auto beforeTerrain = SDL_GetTicksNS();
        tiles = terrain_.Update(ship.origin, scene_);
        terrainTime = SDL_GetTicksNS() - beforeTerrain;
        terrain_.ProjectShadow(groundFrame, ship, pose_.Vertices(), shadowVertices_);
        scene_.SetShadow(shadowVertices_);
        shadowTime_ = simTime;

        const auto altitude = vessel->GetAltitude(ALTMODE_GROUND);
        const bool liftoff = !loggedLiftoff_ && !vessel->GroundContact() && altitude > 8 && vessel->GetAirspeed() > 30;
        loggedLiftoff_ |= liftoff;
        if (tiles.recentered || liftoff) {
            std::ostringstream sample;
            sample << "Vulkan flight " << (liftoff ? "liftoff" : "terrain") << ": t=" << simTime
                   << " AGL=" << altitude << " airspeed=" << vessel->GetAirspeed();
            if (!shadowVertices_.empty()) {
                const auto* shadow = shadowVertices_.front().position;
                sample << " projected shadow east=" << shadow[0] << " north=" << shadow[2];
            }
            SceneLog(sample.str());
        }
    }
    auto ground = MakeUniform(groundFrame, width, height);
    // The stock aerial imagery already contains its illumination.
    ground.light[0] = ground.light[2] = 0;
    ground.light[1] = 1;
    const bool presented = scene_.Present(MakeUniform(ship, width, height), ground);
    if (frameTrace_.is_open()) {
        const auto milliseconds = [](Uint64 time) { return double(time) / 1000000; };
        frameTrace_ << simTime << ',' << milliseconds(previousFrame_ ? start - previousFrame_ : 0)
                    << ',' << milliseconds(SDL_GetTicksNS() - start) << ',' << milliseconds(terrainTime)
                    << ',' << tiles.staged << ',' << tiles.switched << ',' << poseChanged
                    << ',' << !shadowVertices_.empty() << '\n';
        previousFrame_ = start;
    }
    return presented;
}

void OrbiterScene::Close() noexcept
{
    ClearFocus();
    scene_.Close();
    if (frameTrace_.is_open()) frameTrace_.close();
}

std::string OrbiterScene::FlightTitle() const
{
    const auto name = "Orbiter - Runway 33 [Vulkan]";
    if (!focus_) return name;
    auto* vessel = oapiGetVesselInterface(focus_);
    std::ostringstream title;
    title << name << (oapiGetPause() ? " | Paused" : "") << std::fixed << std::setprecision(0)
          << " | " << vessel->GetAirspeed() << " m/s | " << vessel->GetAltitude(ALTMODE_GROUND)
          << " m AGL | Main " << 100 * vessel->GetThrusterGroupLevel(THGROUP_MAIN) << '%';
    return title.str();
}

} // namespace orbiter::vulkan
