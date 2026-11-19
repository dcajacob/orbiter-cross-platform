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
#include <type_traits>

#ifndef _WIN32
#include "Base.h"
#endif

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
    const auto eye = frame.ToLocal(camera);
    uniform.eye[0] = float(eye.x);
    uniform.eye[1] = float(eye.y);
    uniform.eye[2] = float(eye.z);
    const auto displacement = Subtract(frame.origin, camera);
    const auto sunlight = Subtract(SunPosition(), frame.origin);
    const double distance = std::sqrt(Dot(sunlight, sunlight));
    const double vertical = 1 / std::tan(oapiCameraAperture());
    const double horizontal = vertical * height / width;
    constexpr double nearPlane = 0.1;
    constexpr double farPlane = 220000.0;
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

void OrbiterScene::Open(SDL_Window* window, BaseMeshes baseMeshes, bool baseShadows)
{
    baseMeshes_ = std::move(baseMeshes);
    baseShadows_ = baseShadows;
    if (const char* dir = SDL_getenv("ORBITER_VULKAN_CAPTURE_DIR"); dir && *dir) {
        captureDirectory_ = dir;
        if (!std::filesystem::is_directory(captureDirectory_))
            throw std::runtime_error("Vulkan capture directory does not exist");
    }
    scene_.Open(window);
    if (const char* path = SDL_getenv("ORBITER_VULKAN_FRAME_TRACE"); path && *path) {
        frameTrace_.open(std::filesystem::path(path));
        if (!frameTrace_) throw std::runtime_error("Cannot open Vulkan frame trace");
        frameTrace_ << "sim_seconds,interval_ms,scene_ms,terrain_ms,tiles_staged,imagery_staged,tiles_switched,pose_uploaded,shadow_drawn,base_upload_ms,base_shadow_updated\n";
    }
    previousFrame_ = 0;
}

void OrbiterScene::AppendMesh(MESHHANDLE mesh, SceneMesh& ship, std::vector<VertexRange>& groups,
    std::map<SURFHANDLE, unsigned>& textureSlots, std::optional<DrawPass> surfacePass, SURFHANDLE surfaceTexture) const
{
    if (!mesh) return;
    const auto materials = oapiMeshMaterialCount(mesh);
    const auto textures = oapiMeshTextureCount(mesh);
    unsigned materialIndex = defaultIndex;
    unsigned textureIndex = defaultIndex;
    const auto firstGroup = groups.size();
    const auto count = oapiMeshGroupCount(mesh);
    groups.resize(firstGroup + count);
    for (unsigned i = 0; i < count; ++i) {
        const auto* group = oapiMeshGroup(mesh, i);
        if (!group) continue;
        if (group->MtrlIdx != inheritedIndex) materialIndex = group->MtrlIdx;
        if (group->TexIdx != inheritedIndex) textureIndex = group->TexIdx;
        if ((group->UsrFlag & 2) || !group->nVtx || !group->nIdx) continue;
        MaterialUniform material;
        if (materialIndex < materials) {
            const auto* mat = oapiMeshMaterial(mesh, materialIndex);
            if (mat) {
                material.diffuse = {mat->diffuse.r, mat->diffuse.g, mat->diffuse.b, mat->diffuse.a};
                material.ambient = {mat->ambient.r, mat->ambient.g, mat->ambient.b, 0};
                material.specular = {mat->specular.r, mat->specular.g, mat->specular.b, mat->power};
                material.emission = {mat->emissive.r, mat->emissive.g, mat->emissive.b, 0};
            }
        }
        unsigned gpuTexture = 0;
        if (surfaceTexture || textureIndex < textures) {
            const auto handle = surfaceTexture ? surfaceTexture : oapiGetTextureHandle(mesh, textureIndex + 1);
            const auto* texture = Lookup(handle);
            if (texture) {
                const auto slot = textureSlots.emplace(handle, unsigned(ship.textures.size()));
                if (slot.second) ship.textures.push_back(texture);
                gpuTexture = slot.first->second;
            }
        }
        const auto startVertex = unsigned(ship.vertices.size());
        groups[firstGroup + i] = {startVertex, group->nVtx};
        const auto pass = surfacePass.value_or(material.diffuse[3] < 0.999f ? DrawPass::Translucent : DrawPass::Opaque);
        ship.groups.push_back({unsigned(ship.indices.size()), group->nIdx, gpuTexture, material, pass, !surfacePass && !(group->UsrFlag & 1)});
        for (unsigned j = 0; j < group->nVtx; ++j) {
            const auto& v = group->Vtx[j];
            ship.vertices.push_back({{v.x, v.y, v.z}, {v.nx, v.ny, v.nz}, {v.tu, v.tv}});
        }
        for (unsigned j = 0; j < group->nIdx; ++j) {
            if (group->Idx[j] >= group->nVtx) throw std::runtime_error("Invalid exterior mesh index");
            ship.indices.push_back(startVertex + group->Idx[j]);
        }
    }
}

void OrbiterScene::CaptureFocus(std::filesystem::path archive)
{
    ClearFocus();
    archivePath_ = std::move(archive);
    auto* vessel = oapiGetFocusInterface();
    if (!vessel) return;
    focus_ = vessel->GetHandle();
    terrain_.Open(archivePath_, ObjectFrame(focus_).origin);
    char earthName[] = "Earth";
    const auto earth = oapiGetGbodyByName(earthName);
    const auto count = oapiGetBaseCount(earth);
    for (unsigned i = 0; i < count; ++i) {
        const auto base = oapiGetBaseByIndex(earth, i);
        double lng, lat;
#ifdef _WIN32
        oapiGetBaseEquPos(base, &lng, &lat, nullptr);
#else
        static_cast<const Base*>(base)->EquPos(lng, lat);
#endif
        bases_.push_back({i, base, terrain_.BasePosition(lng, lat), lng, lat});
    }
    RefreshExterior(*vessel);
}

void OrbiterScene::LoadBase(const EarthBase& base, const SceneFrame& frame)
{
    const auto geometry = baseMeshes_(base.handle);
    SceneMesh mesh;
    std::map<SURFHANDLE, unsigned> textures;
    std::vector<VertexRange> groups;
    for (unsigned i = 0; i < geometry.tileCount; ++i) {
        const auto& tile = geometry.tiles[i];
        if (tile.mesh && Lookup(tile.tex))
            AppendMesh(tile.mesh, mesh, groups, textures, DrawPass::BaseTile, tile.tex);
    }
    const auto tileVertices = mesh.vertices.size();
    for (unsigned i = 0; i < geometry.surfaceCount; ++i)
        AppendMesh(geometry.surfaces[i], mesh, groups, textures, DrawPass::Pavement);
    for (unsigned i = 0; i < geometry.buildingCount; ++i)
        AppendMesh(geometry.buildings[i], mesh, groups, textures);
    // Place Orbiter's already elevated and rotated structures in the same
    // Earth-fixed tangent frame as the tile vertices. Do this once per region.
    for (std::size_t i = 0; i < mesh.vertices.size(); ++i) {
        auto& v = mesh.vertices[i];
        auto pos = frame.ToGlobal({v.position[0], v.position[1], v.position[2]});
        if (i < tileVertices) pos = terrain_.DrapeSurfaceTile(pos);
        const auto normal = frame.Rotate({v.normal[0], v.normal[1], v.normal[2]});
        for (unsigned axis = 0; axis < 3; ++axis) {
            v.position[axis] = float(pos.data[axis]);
            v.normal[axis] = float(normal.data[axis]);
        }
    }
    scene_.AddBase(base.index, mesh, baseShadows_);
    char name[256]{};
    oapiGetObjectName(base.handle, name, sizeof(name) - 1);
    std::ostringstream message;
    message << "Vulkan base " << name << ": " << geometry.tileCount << " surface tiles, "
            << geometry.surfaceCount << " ground meshes, " << geometry.buildingCount << " building meshes, "
            << mesh.groups.size() << " groups, " << textures.size() << " textures";
    SceneLog(message.str());
}

bool OrbiterScene::UpdateBases(const VECTOR3& eye)
{
    bool uploaded = false;
    for (auto& base : bases_) {
        // No elevation or mesh IO for distant bases. Hysteresis avoids repeatedly
        // rebuilding GPU resources when the camera hovers near the boundary.
        const auto delta = Subtract(base.position, eye);
        const double range = base.loaded ? 110000.0 : 100000.0;
        const bool nearby = Dot(delta, delta) < range * range;
        if (nearby == base.loaded) continue;
        if (nearby) {
            LoadBase(base, terrain_.BaseFrame(base.longitude, base.latitude));
            uploaded = true;
        } else {
            scene_.RemoveBase(base.index);
        }
        base.loaded = nearby;
    }
    return uploaded;
}

void OrbiterScene::RefreshExterior(const VESSEL& vessel)
{
    const auto count = vessel.GetMeshCount();
    bool rebuild = exteriorSlots_.size() != count;
    exteriorSlots_.resize(count);
    for (unsigned index = 0; index < count; ++index) {
        std::optional<MESHHANDLE> current;
        if (vessel.GetMeshVisibilityMode(index) & MESHVIS_EXTERNAL)
            current = vessel.GetMeshTemplate(index);
        rebuild |= current != exteriorSlots_[index];
        exteriorSlots_[index] = current;
    }
    if (!rebuild) return;
    SceneMesh ship;
    std::map<SURFHANDLE, unsigned> textureSlots;
    std::vector<VertexRange> groups;
    std::vector<MeshGroups> meshes(count);
    // Keep on-demand copies (and their texture handles) alive through GPU upload.
    using OwnedMesh = std::unique_ptr<std::remove_pointer_t<MESHHANDLE>, decltype(&oapiDeleteMesh)>;
    std::vector<OwnedMesh> copies;
    unsigned exteriorCount = 0;
    for (unsigned index = 0; index < meshes.size(); ++index) {
        if (!exteriorSlots_[index]) continue;
        auto mesh = *exteriorSlots_[index];
        if (!mesh) {
            mesh = vessel.CopyMeshFromTemplate(index);
            if (!mesh) continue;
            copies.emplace_back(mesh, &oapiDeleteMesh);
        }
        auto& slot = meshes[index];
        slot.first = groups.size();
        AppendMesh(mesh, ship, groups, textureSlots);
        slot.count = groups.size() - slot.first;
        ++exteriorCount;
    }
    shadowTime_.reset();
    scene_.SetShip(ship);
    pose_.Reset(std::move(ship.vertices), std::move(groups), std::move(meshes));
    std::ostringstream message;
    message << "Vulkan exterior: " << vessel.GetName() << " (" << vessel.GetClassName() << "), "
            << exteriorCount << " meshes, " << ship.groups.size() << " groups, "
            << textureSlots.size() << " textures";
    SceneLog(message.str());
}

void OrbiterScene::ClearFocus() noexcept
{
    focus_ = nullptr;
    archivePath_.clear();
    bases_.clear();
    lastCapture_ = -1;
    exteriorSlots_.clear();
    scene_.ClearMesh();
    terrain_.Close();
    pose_.Reset({}, {}, {});
    shadowVertices_.clear();
    shadowTime_.reset();
    loggedLiftoff_ = false;
}

bool OrbiterScene::Present(unsigned width, unsigned height)
{
    if (!width || !height) return true;
    if (!archivePath_.empty() && oapiGetFocusObject() != focus_) CaptureFocus(archivePath_);
    if (!focus_) return scene_.Present({}, {});
    const auto start = SDL_GetTicksNS();
    const auto ship = ObjectFrame(focus_);
    const auto simTime = oapiGetSimTime();
    VECTOR3 camera;
    oapiCameraGlobalPos(&camera);
    if (terrain_.NeedsReanchor(camera)) {
        scene_.ClearGround();
        terrain_.Open(archivePath_, camera);
        for (auto& base : bases_) {
            base.position = terrain_.BasePosition(base.longitude, base.latitude);
            base.loaded = false;
        }
        shadowTime_.reset();
    }
    const auto groundFrame = terrain_.Frame();
    auto* vessel = oapiGetVesselInterface(focus_);
    RefreshExterior(*vessel);
    const bool poseChanged = pose_.Update(*vessel);
    if (poseChanged) scene_.SetShipPose(pose_.Vertices());
    const auto beforeTerrain = SDL_GetTicksNS();
    const auto tiles = terrain_.Update(camera, scene_);
    const auto terrainTime = SDL_GetTicksNS() - beforeTerrain;
    if (shadowTime_ != simTime || poseChanged || tiles.switched) {
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
    const auto beforeBases = SDL_GetTicksNS();
    const auto baseUploadTime = UpdateBases(groundFrame.ToLocal(camera)) ? SDL_GetTicksNS() - beforeBases : 0;
    std::filesystem::path samplePath;
    if (!captureDirectory_.empty()) {
        const auto sample = static_cast<long long>(std::floor(simTime * 10.0 + 1e-6));
        if (sample != lastCapture_) {
            std::ostringstream filename;
            filename << "frame-" << std::setw(6) << std::setfill('0') << sample << ".bmp";
            samplePath = captureDirectory_ / filename.str();
            lastCapture_ = sample;
        }
    }
    const bool presented = scene_.Present(MakeUniform(ship, width, height),
        MakeUniform(groundFrame, width, height), samplePath);
    if (frameTrace_.is_open()) {
        const auto milliseconds = [](Uint64 time) { return double(time) / 1000000; };
        frameTrace_ << simTime << ',' << milliseconds(previousFrame_ ? start - previousFrame_ : 0)
                    << ',' << milliseconds(SDL_GetTicksNS() - start) << ',' << milliseconds(terrainTime)
                    << ',' << tiles.staged << ',' << tiles.imagery << ',' << tiles.switched << ',' << poseChanged
                    << ',' << !shadowVertices_.empty() << ',' << milliseconds(baseUploadTime) << ',' << scene_.ShadowMapUpdated() << '\n';
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
    const auto name = "Orbiter [Vulkan]";
    if (!focus_) return name;
    auto* vessel = oapiGetVesselInterface(focus_);
    std::ostringstream title;
    title << name << " - " << vessel->GetName() << (oapiGetPause() ? " | Paused" : "") << std::fixed << std::setprecision(0)
          << " | " << vessel->GetAirspeed() << " m/s | " << vessel->GetAltitude(ALTMODE_GROUND)
          << " m AGL | Main " << 100 * vessel->GetThrusterGroupLevel(THGROUP_MAIN) << '%';
    return title.str();
}

} // namespace orbiter::vulkan
