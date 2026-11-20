// Licensed under the MIT License
#include "OrbiterScene.h"

#include <algorithm>
#include <cmath>
#include <cctype>
#include <charconv>
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

SceneUniform MakeUniform(const SceneFrame& frame, const SceneFrame& camera, const VECTOR3& sun,
    double horizontal, double vertical)
{
    SceneUniform uniform{};
    const auto eye = frame.ToLocal(camera.origin);
    uniform.eye[0] = float(eye.x);
    uniform.eye[1] = float(eye.y);
    uniform.eye[2] = float(eye.z);
    const auto displacement = Subtract(frame.origin, camera.origin);
    const auto sunlight = Subtract(sun, frame.origin);
    const double distance = std::sqrt(Dot(sunlight, sunlight));
    constexpr double nearPlane = 0.1;

    for (unsigned i = 0; i < 4; ++i) {
        const auto& v = i == 3 ? displacement : frame.axes[i];
        const auto z = Dot(v, camera.axes[2]);
        uniform.projection[4 * i] = float(horizontal * Dot(v, camera.axes[0]));
        uniform.projection[4 * i + 1] = float(vertical * Dot(v, camera.axes[1]));
        // Reverse Z preserves floating-point depth precision for distant ground and its shadow.
        uniform.projection[4 * i + 2] = i == 3 ? float(nearPlane) : 0.0f;
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

TextureData* OrbiterScene::Writable(SURFHANDLE surface)
{
    const auto it = surfaces_.find(surface);
    if (it == surfaces_.end()) return nullptr;
    MakeWritable(*it->second);
    ++it->second->revision;
    return it->second.get();
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
    if (--it->second->references == 0) {
        scene_.ForgetPanelTexture(it->second.get());
        surfaces_.erase(it);
    }
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
    if (x > image.width || y > image.height || width > image.width - x || height > image.height - y)
        return false;
    MakeWritable(image);
    ++image.revision;
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
    if (x > output.width || y > output.height || sx > input->width || sy > input->height)
        return false;
    MakeWritable(output);
    ++output.revision;
    width = std::min({width, output.width - x, input->width - sx});
    height = std::min({height, output.height - y, input->height - sy});
    for (unsigned row = 0; row < height; ++row) {
        // Copy bottom-up when a self-blit overlaps subsequent source rows.
        const auto offset = input == &output && y > sy ? height - 1 - row : row;
        auto* pixels = output.pixels.data() + (std::size_t(y + offset) * output.width + x) * 4;
        if (!input->blockBytes && input->format == output.format) {
            std::memmove(pixels, input->pixels.data() + (std::size_t(sy + offset) * input->width + sx) * 4, 4 * width);
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
        captureFps_ = 10;
        if (const char* fps = SDL_getenv("ORBITER_VULKAN_CAPTURE_FPS"); fps && *fps) {
            const char* end = fps + std::strlen(fps);
            const auto parsed = std::from_chars(fps, end, captureFps_);
            if (parsed.ec != std::errc{} || parsed.ptr != end || captureFps_ < 1 || captureFps_ > 120)
                throw std::runtime_error("Vulkan capture FPS must be an integer from 1 to 120");
        }
        if (!std::filesystem::is_directory(captureDirectory_))
            throw std::runtime_error("Vulkan capture directory does not exist");
    }
    if (const char* path = SDL_getenv("ORBITER_VULKAN_FRAME_TRACE"); path && *path) {
        frameTrace_.open(std::filesystem::path(path));
        if (!frameTrace_) throw std::runtime_error("Cannot open Vulkan frame trace");
        frameTrace_ << "sim_seconds,interval_ms,scene_ms,terrain_ms,tiles_staged,imagery_staged,tiles_switched,pose_uploaded,shadow_drawn,base_upload_ms,base_shadow_updated,acquire_wait_ms,reanchor_ms,terrain_recentered,visible_tiles,detail_tiles,frame_slot_ms,image_acquire_ms,draw_encode_ms,present_submit_ms,terrain_draws,camera_altitude_m,earth_leaf_area,vessels_drawn,focus\n";
    }
    scene_.Open(window, frameTrace_.is_open());
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

void OrbiterScene::OpenWorld(std::filesystem::path archive)
{
    CloseWorld();
    VECTOR3 camera;
    oapiCameraGlobalPos(&camera);
    terrain_.Open(archive, camera);
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
    worldOpen_ = true;
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

void OrbiterScene::RefreshExterior(const VESSEL& vessel, VesselVisual& visual)
{
    const auto count = vessel.GetMeshCount();
    bool rebuild = visual.exteriorSlots.size() != count;
    visual.exteriorSlots.resize(count);
    for (unsigned index = 0; index < count; ++index) {
        std::optional<MESHHANDLE> current;
        if (vessel.GetMeshVisibilityMode(index) & MESHVIS_EXTERNAL)
            current = vessel.GetMeshTemplate(index);
        rebuild |= current != visual.exteriorSlots[index];
        visual.exteriorSlots[index] = current;
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
        if (!visual.exteriorSlots[index]) continue;
        auto mesh = *visual.exteriorSlots[index];
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
    visual.shadowTime.reset();
    scene_.SetShip(vessel.GetHandle(), ship);
    visual.pose.Reset(std::move(ship.vertices), std::move(groups), std::move(meshes));
    std::ostringstream message;
    message << "Vulkan exterior: " << vessel.GetName() << " (" << vessel.GetClassName() << "), "
            << exteriorCount << " meshes, " << ship.groups.size() << " groups, "
            << textureSlots.size() << " textures";
    SceneLog(message.str());
}

void OrbiterScene::RemoveVessel(OBJHANDLE handle) noexcept
{
    scene_.RemoveShip(handle);
    vessels_.erase(handle);
    if (focus_ == handle) focus_ = nullptr;
}

void OrbiterScene::CloseWorld() noexcept
{
    focus_ = nullptr;
    worldOpen_ = false;
    bases_.clear();
    vessels_.clear();
    draws_.clear();
    lastCapture_ = -1;
    scene_.ClearMesh();
    terrain_.Close();
}

OrbiterScene::VesselUpdate OrbiterScene::UpdateVessels(const SceneFrame& camera, const SceneFrame& groundFrame,
    const EarthView& earth, unsigned height, bool refreshShadow, bool terrainRecentered)
{
    const auto simTime = oapiGetSimTime();
    const auto sun = SunPosition();
    const double focal = 0.5 * height * earth.vertical;
    draws_.clear();
    VesselUpdate update;
    for (auto& entry : vessels_) entry.second.retained = false;
    const auto count = oapiGetVesselCount();
    for (unsigned i = 0; i < count; ++i) {
        const auto handle = oapiGetVesselByIndex(i);
        auto* vessel = oapiGetVesselInterface(handle);
        if (!vessel) continue;
        const auto frame = ObjectFrame(handle);
        const auto eye = camera.ToLocal(frame.origin);
        const double radius = std::max(vessel->GetSize(), vessel->GetClipRadius());
        // Hysteresis keeps readable non-focus exteriors resident as the camera moves.
        const double minPixels = vessels_.count(handle) ? 0.35 : 0.6;
        const double maxRange = radius * focal / minPixels;
        if (handle != focus_ && Dot(eye, eye) > maxRange * maxRange) continue;
        auto& visual = vessels_[handle];
        visual.retained = true;
        RefreshExterior(*vessel, visual);
        if (visual.pose.Vertices().empty()) continue;
        const bool changed = visual.pose.Update(*vessel);
        if (changed) scene_.SetShipPose(handle, visual.pose.Vertices());
        update.poseUploaded |= changed;
        if (visual.shadowTime != simTime || changed || refreshShadow) {
            terrain_.ProjectShadow(groundFrame, frame, visual.pose.Vertices(), visual.shadow);
            scene_.SetShadow(handle, visual.shadow);
            visual.shadowTime = simTime;
        }
        update.shadowDrawn |= !visual.shadow.empty();
        // Sphere against the four side planes and the eye. Orbiter's clip radius
        // includes parts extending beyond the nominal size, such as solar panels.
        if (!(handle == focus_ && oapiCameraInternal()) && eye.z + radius > 0 &&
            std::abs(eye.x * earth.horizontal) <= eye.z + radius * std::hypot(1.0, earth.horizontal) &&
            std::abs(eye.y * earth.vertical) <= eye.z + radius * std::hypot(1.0, earth.vertical)) {
            draws_.push_back({handle, MakeUniform(frame, camera, sun, earth.horizontal, earth.vertical)});
        }
        if (handle == focus_) {
            const auto altitude = vessel->GetAltitude(ALTMODE_GROUND);
            const bool grounded = vessel->GroundContact();
            visual.awaitingLiftoff |= grounded;
            const bool liftoff = visual.awaitingLiftoff && !grounded && altitude > 8 && vessel->GetAirspeed() > 30;
            if (liftoff) visual.awaitingLiftoff = false;
            if (terrainRecentered || liftoff) {
                std::ostringstream sample;
                sample << "Vulkan flight " << (liftoff ? "liftoff" : "terrain") << ": t=" << simTime
                       << " AGL=" << altitude << " airspeed=" << vessel->GetAirspeed();
                if (!visual.shadow.empty()) {
                    const auto* shadow = visual.shadow.front().position;
                    sample << " projected shadow east=" << shadow[0] << " north=" << shadow[2];
                }
                SceneLog(sample.str());
            }
        }
    }
    for (auto it = vessels_.begin(); it != vessels_.end();) {
        if (it->second.retained) { ++it; continue; }
        scene_.RemoveShip(it->first);
        it = vessels_.erase(it);
    }
    // Back-to-front vessel order for the translucent pass. Opaque geometry
    // from every vessel populates the shared depth buffer first.
    std::stable_sort(draws_.begin(), draws_.end(), [](const VesselDraw& a, const VesselDraw& b) {
        return a.uniform.projection[15] > b.uniform.projection[15];
    });
    return update;
}

bool OrbiterScene::Present(unsigned width, unsigned height)
{
    if (!width || !height) return true;
    if (!worldOpen_) return scene_.Present({}, {}, {});
    const auto start = SDL_GetTicksNS();
    const auto focus = oapiGetFocusObject();
    if (focus != focus_) {
        focus_ = focus;
        if (focus) SceneLog(std::string("Vulkan focus: ") + oapiGetVesselInterface(focus)->GetName());
    }
    const auto simTime = oapiGetSimTime();
    SceneFrame camera;
    oapiCameraGlobalPos(&camera.origin);
    MATRIX3 rotation;
    oapiCameraRotationMatrix(&rotation);
    camera.axes = Axes(rotation);
    Uint64 reanchorTime = 0;
    if (terrain_.NeedsReanchor(camera.origin)) {
        const auto beforeReanchor = SDL_GetTicksNS();
        terrain_.Reanchor(camera.origin);
        for (auto& base : bases_) {
            if (base.loaded) scene_.RemoveBase(base.index);
            base.position = terrain_.BasePosition(base.longitude, base.latitude);
            base.loaded = false;
        }
        reanchorTime = SDL_GetTicksNS() - beforeReanchor;
    }
    const auto groundFrame = terrain_.Frame();
    const auto beforeTerrain = SDL_GetTicksNS();
    const auto earth = terrain_.View(width, height);
    const auto tiles = terrain_.Update(earth, height, scene_);
    const auto terrainTime = SDL_GetTicksNS() - beforeTerrain;
    const auto vessels = UpdateVessels(camera, groundFrame, earth, height, tiles.switched || reanchorTime, tiles.recentered);
    const auto beforeBases = SDL_GetTicksNS();
    const auto baseUploadTime = UpdateBases(groundFrame.ToLocal(camera.origin)) ? SDL_GetTicksNS() - beforeBases : 0;
    std::filesystem::path samplePath;
    if (!captureDirectory_.empty()) {
        const auto sample = static_cast<long long>(std::floor(simTime * captureFps_ + 1e-6));
        if (sample != lastCapture_) {
            std::ostringstream filename;
            filename << "frame-" << std::setw(6) << std::setfill('0') << sample << ".bmp";
            samplePath = captureDirectory_ / filename.str();
            lastCapture_ = sample;
        }
    }
    const bool presented = scene_.Present(draws_,
        MakeUniform(groundFrame, camera, SunPosition(), earth.horizontal, earth.vertical), earth, samplePath);
    if (frameTrace_.is_open()) {
        const auto milliseconds = [](Uint64 time) { return double(time) / 1000000; };
        const auto& timing = scene_.Timings();
        frameTrace_ << simTime << ',' << milliseconds(previousFrame_ ? start - previousFrame_ : 0)
                    << ',' << milliseconds(SDL_GetTicksNS() - start) << ',' << milliseconds(terrainTime)
                    << ',' << tiles.staged << ',' << tiles.imagery << ',' << tiles.switched << ',' << vessels.poseUploaded
                    << ',' << vessels.shadowDrawn << ',' << milliseconds(baseUploadTime) << ',' << scene_.ShadowMapUpdated()
                    << ',' << milliseconds(timing.acquireNS) << ',' << milliseconds(reanchorTime)
                    << ',' << tiles.recentered << ',' << terrain_.VisibleCount() << ',' << terrain_.DetailCount()
                    << ',' << milliseconds(timing.fenceNS) << ',' << milliseconds(timing.acquireNS - timing.fenceNS)
                    << ',' << milliseconds(timing.encodeNS) << ',' << milliseconds(timing.submitNS)
                    << ',' << timing.terrainDraws << ',' << earth.altitude << ',' << terrain_.LeafArea()
                    << ',' << draws_.size() << ",\"";
        if (focus) {
            for (const char* c = oapiGetVesselInterface(focus)->GetName(); *c; ++c) {
                if (*c == '"') frameTrace_ << '"';
                frameTrace_ << *c;
            }
        }
        frameTrace_ << "\"\n";
        previousFrame_ = start;
    }
    return presented;
}

void OrbiterScene::Close() noexcept
{
    captureDirectory_.clear();
    CloseWorld();
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
