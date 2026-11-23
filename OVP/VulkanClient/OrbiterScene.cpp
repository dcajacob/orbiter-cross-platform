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
#include "Production/NativeInterpreterSdk.h"
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
    if (suffix != ".bmp" && suffix != ".png") return nullptr;
    const auto load = suffix == ".png" ? SDL_LoadPNG : SDL_LoadBMP;
    std::unique_ptr<SDL_Surface, decltype(&SDL_DestroySurface)> source(load(path.string().c_str()), SDL_DestroySurface);
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
    bool changed = false;
    const std::uint8_t rgba[] = {std::uint8_t(color), std::uint8_t(color >> 8), std::uint8_t(color >> 16), 255};
    for (unsigned row = y; row < y + height; ++row) {
        auto* pixel = image.pixels.data() + (std::size_t(row) * image.width + x) * 4;
        for (unsigned col = 0; col < width; ++col, pixel += 4) {
            if (std::memcmp(pixel, rgba, 4) != 0) {
                std::memcpy(pixel, rgba, 4);
                changed = true;
            }
        }
    }
    if (changed) ++image.revision;
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
    width = std::min({width, output.width - x, input->width - sx});
    height = std::min({height, output.height - y, input->height - sy});
    bool changed = false;
    for (unsigned row = 0; row < height; ++row) {
        // Copy bottom-up when a self-blit overlaps subsequent source rows.
        const auto offset = input == &output && y > sy ? height - 1 - row : row;
        auto* pixels = output.pixels.data() + (std::size_t(y + offset) * output.width + x) * 4;
        if (!input->blockBytes && input->format == output.format) {
            const auto* sourceRow = input->pixels.data() + (std::size_t(sy + offset) * input->width + sx) * 4;
            if (std::memcmp(pixels, sourceRow, 4 * width) != 0) {
                std::memmove(pixels, sourceRow, 4 * width);
                changed = true;
            }
            continue;
        }
        for (unsigned col = 0; col < width; ++col) {
            const auto rgba = ReadPixel(*input, sx + col, sy + row);
            auto* targetPixel = pixels + 4 * col;
            if (std::memcmp(targetPixel, rgba.data(), rgba.size()) != 0) {
                std::memcpy(targetPixel, rgba.data(), rgba.size());
                changed = true;
            }
        }
    }
    // Vessel callbacks can repaint exactly the same digits every step.
    // Keep the resident texture and its mip chain until a texel changes.
    if (changed) ++output.revision;
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
    std::map<SURFHANDLE, unsigned>& textureSlots, std::optional<DrawPass> surfacePass, SURFHANDLE surfaceTexture,
    unsigned meshIndex, const std::vector<CockpitDisplay>& displays, bool dgCockpit) const
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
        const auto display = std::find_if(displays.begin(), displays.end(), [&](const CockpitDisplay& d) {
            return d.mesh == meshIndex && d.group == i;
        });
        const bool instrument = display != displays.end();
        if ((!instrument && (group->UsrFlag & 2)) || !group->nVtx || !group->nIdx) continue;
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
        if (dgCockpit) {
            const bool backlit = materialIndex == 0 || materialIndex == 11 || materialIndex == 17
                || materialIndex == 18 || materialIndex == 28;
            for (unsigned c = 0; c < 3; ++c) material.emission[c] *= backlit ? 0.85f : 0.045f;
            material.ambient[3] = (materialIndex == 23 || materialIndex == 25) ? 2.0f : 1.0f;
            if (materials == 31 && materialIndex == 30) {
                // Faceplate markings follow the DG's stock legend rheostat.
                if (const auto* lamp = oapiMeshMaterial(mesh, 11))
                    material.emission = {lamp->emissive.r, lamp->emissive.g, lamp->emissive.b, 0};
                material.ambient[3] = 3.0f;
            }
        }
        if (instrument) {
            material.ambient[3] = display->hud ? -1.0f : -2.0f;
            material.diffuse[3] = display->hud ? 0.5f : 1.0f;
        }
        unsigned gpuTexture = 0;
        if (instrument || surfaceTexture || textureIndex < textures) {
            const auto handle = instrument ? display->surface : surfaceTexture ? surfaceTexture : oapiGetTextureHandle(mesh, textureIndex + 1);
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
        ship.groups.push_back({unsigned(ship.indices.size()), group->nIdx, gpuTexture, material, pass, !instrument && !surfacePass && !(group->UsrFlag & 1)});
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

void OrbiterScene::RefreshMeshes(const VESSEL& vessel, VesselVisual& visual, bool internal,
    const std::vector<CockpitDisplay>& displays)
{
    const auto count = vessel.GetMeshCount();
    const bool pilotSeat = internal && vessel.GetHandle() == pilot_;
    bool rebuild = visual.meshSlots.size() != count || visual.displays != displays || visual.pilotSeat != pilotSeat;
    visual.pilotSeat = pilotSeat;
    visual.meshSlots.resize(count);
    for (unsigned index = 0; index < count; ++index) {
        std::optional<MESHHANDLE> current;
        const auto visibleMask = internal ? MESHVIS_COCKPIT | MESHVIS_VC : MESHVIS_EXTERNAL;
        if (vessel.GetMeshVisibilityMode(index) & (visibleMask | (pilotSeat ? MESHVIS_EXTERNAL : 0)))
            current = vessel.GetMeshTemplate(index);
        if (pilotSeat && current && index < pilotMeshes_.size() && pilotMeshes_[index].mesh) {
            auto& device = pilotMeshes_[index];
            current = device.mesh;
            rebuild |= device.rebuild;
            device.rebuild = false;
            for (unsigned group : device.changed) {
                if (auto* data = oapiMeshGroup(device.mesh,group)) visual.pose.SetGroup(index,group,*data);
            }
            device.changed.clear();
        }
        rebuild |= current != visual.meshSlots[index];
        visual.meshSlots[index] = current;
    }
    // A cockpit texture atlas may become writable after its original compressed
    // upload. Rebuild once on its first edit to obtain a writable RGBA mip chain.
    if (!rebuild && pilotSeat) {
        for (const auto& [surface, slot] : visual.displaySlots) {
            const auto* image=Lookup(surface);
            if (image && image->revision && !visual.revisions[slot]) rebuild=true;
        }
    }
    if (!rebuild) {
        for (const auto& [surface, slot] : visual.displaySlots) {
            const auto* image = Lookup(surface);
            if (image && image->revision != visual.revisions[slot]) {
                scene_.UpdateDisplay(vessel.GetHandle(), slot, *image);
                visual.revisions[slot] = image->revision;
            }
        }
        return;
    }
    visual.displays = displays;
    visual.displaySlots.clear();
    visual.revisions.clear();
    SceneMesh ship;
    std::map<SURFHANDLE, unsigned> textureSlots;
    std::vector<VertexRange> groups;
    std::vector<MeshGroups> meshes(count);
    // Keep on-demand copies (and their texture handles) alive through GPU upload.
    using OwnedMesh = std::unique_ptr<std::remove_pointer_t<MESHHANDLE>, decltype(&oapiDeleteMesh)>;
    std::vector<OwnedMesh> copies;
    unsigned exteriorCount = 0;
    for (unsigned index = 0; index < meshes.size(); ++index) {
        if (!visual.meshSlots[index]) continue;
        auto mesh = *visual.meshSlots[index];
        if (!mesh) {
            mesh = vessel.CopyMeshFromTemplate(index);
            if (!mesh) continue;
            copies.emplace_back(mesh, &oapiDeleteMesh);
        }
        auto& slot = meshes[index];
        slot.first = groups.size();
        const std::string className(vessel.GetClassName());
        const bool dgCockpit = pilotSeat && index == 1 && (className == "DG-S" || className == "DeltaGlider")
            && (oapiMeshGroupCount(mesh) == 133 || (oapiMeshGroupCount(mesh) == 135
                && oapiMeshMaterialCount(mesh) == 31 && oapiMeshTextureCount(mesh) == 21));
        const auto firstGroup = ship.groups.size();
        AppendMesh(mesh, ship, groups, textureSlots, {}, nullptr, index, displays, dgCockpit);
        if (pilotSeat && !(vessel.GetMeshVisibilityMode(index) & MESHVIS_EXTERNAL)) {
            // The exterior mesh supplies the vessel's ground silhouette.
            for (auto j = firstGroup; j < ship.groups.size(); ++j) ship.groups[j].castsShadow = false;
        } else if (pilotSeat && !(vessel.GetMeshVisibilityMode(index) & (MESHVIS_COCKPIT | MESHVIS_VC))) {
            // Keep the exterior silhouette in the shadow map from the pilot's seat.
            for (auto j=firstGroup; j<ship.groups.size(); ++j) {
                auto& group=ship.groups[j];
                group.castsShadow &= group.pass == DrawPass::Opaque;
                group.pass=DrawPass::ShadowOnly;
            }
        }
        slot.count = groups.size() - slot.first;
        ++exteriorCount;
    }
    if (internal) {
        visual.displaySlots=textureSlots;
        for (const auto& [surface,slot] : textureSlots)
            visual.revisions[slot]=ship.textures[slot]->revision;
    }
    visual.shadowTime.reset();
    scene_.SetShip(vessel.GetHandle(), ship);
    visual.pose.Reset(std::move(ship.vertices), std::move(groups), std::move(meshes));
    std::ostringstream message;
    message << (internal ? "Vulkan cockpit: " : "Vulkan exterior: ") << vessel.GetName() << " (" << vessel.GetClassName() << "), "
            << exteriorCount << " meshes, " << ship.groups.size() << " groups, "
            << textureSlots.size() << " textures";
    SceneLog(message.str());
}

void OrbiterScene::SetPilot(OBJHANDLE handle)
{
    if (pilot_ == handle) return;
    if (pilot_) {
        registerPilot_(pilot_,nullptr);
        pilot_ = nullptr;
        for (auto& slot : pilotMeshes_) {
            if (slot.mesh) oapiDeleteMesh(slot.mesh);
            slot = {};
        }
    }
    if (!handle) return;
    auto* vessel = oapiGetVesselInterface(handle);
    const std::string name(vessel->GetClassName());
    if ((name!="DG-S" && name!="DeltaGlider") || vessel->GetMeshCount()!=2) return;
    pilot_ = handle;
    for (unsigned i = 0; i < pilotMeshes_.size(); ++i) {
        auto* source = vessel->GetMeshTemplate(i);
        if (i == 1 && source && oapiMeshGroupCount(source) == 133 &&
            oapiMeshMaterialCount(source) == 29 && oapiMeshTextureCount(source) == 20) {
            // Load the optional Vulkan model as a private instance. Other
            // renderers and callbacks that use the stock template retain it.
            auto* enhanced = oapiLoadMesh("Vulkan\\DG\\deltaglider_vc");
            if (enhanced && oapiMeshGroupCount(enhanced) == 135 &&
                oapiMeshMaterialCount(enhanced) == 31 && oapiMeshTextureCount(enhanced) == 21) {
                // DG instruments paint the template's stock surfaces. Keep precisely
                // those handles in the private mesh and retain its new art in slot 21.
                bool shared = true;
                for (unsigned slot = 1; slot <= oapiMeshTextureCount(source); ++slot) {
                    if (!ReplaceTextureSlot(enhanced, slot, oapiGetTextureHandle(source, slot))) {
                        shared = false;
                        break;
                    }
                }
                if (shared) {
                    pilotMeshes_[i].mesh = enhanced;
                    SceneLog("Vulkan DeltaGlider: detailed flight deck");
                    continue;
                }
            }
            if (enhanced) oapiDeleteMesh(enhanced);
        }
        auto mesh = pilotMeshes_[i].mesh = vessel->CopyMeshFromTemplate(i);
        if (mesh && vessel->GetMeshTemplate(i)) {
            // Orbiter copies the template's surface handles by value. Deleting
            // the instance releases each one, so acquire its own references.
            for (unsigned slot = 1; slot <= oapiMeshTextureCount(mesh); ++slot)
                Retain(oapiGetTextureHandle(mesh, slot));
        }
    }
    // VisualCreated and the initial VC redraw immediately request these handles.
    registerPilot_(pilot_,this);
}

MESHHANDLE OrbiterScene::DeviceMesh(VISHANDLE visual,unsigned i)
{
    if (!pilot_ || visual!=this || i>=pilotMeshes_.size() || !pilotMeshes_[i].mesh) return nullptr;
    return reinterpret_cast<MESHHANDLE>(&pilotMeshes_[i]);
}

OrbiterScene::PilotMesh* OrbiterScene::FindDevice(DEVMESHHANDLE device)
{
    for (auto& slot : pilotMeshes_)
        if (slot.mesh && reinterpret_cast<DEVMESHHANDLE>(&slot)==device) return &slot;
    return nullptr;
}

int OrbiterScene::ReadGroup(DEVMESHHANDLE device, unsigned i, GROUPREQUESTSPEC* request)
{
    const auto* slot = FindDevice(device);
    auto* g = slot ? oapiMeshGroup(slot->mesh,i) : nullptr;
    if (!g || !request) return 1;
    int status=0;
    const auto copy=[&](auto* dest,auto& count,const auto* permutation,const auto* source,unsigned available) {
        if (!dest) return;
        if (!permutation) { count=std::min<unsigned>(count,available); std::copy_n(source,count,dest); return; }
        for (unsigned j=0;j<count;++j) {
            if (permutation[j]<available) dest[j]=source[permutation[j]];
            else { dest[j]={}; status=1; }
        }
    };
    copy(request->Vtx,request->nVtx,request->VtxPerm,g->Vtx,g->nVtx);
    copy(request->Idx,request->nIdx,request->IdxPerm,g->Idx,g->nIdx);
    request->MtrlIdx=g->MtrlIdx; request->TexIdx=g->TexIdx;
    return status;
}

int OrbiterScene::EditGroup(DEVMESHHANDLE device,unsigned i,GROUPEDITSPEC* edit)
{
    auto* slot=FindDevice(device);
    auto* g=slot ? oapiMeshGroup(slot->mesh,i) : nullptr;
    if (!g || !edit) return 1;
    const auto flags=g->UsrFlag;
    const int status=oapiEditMeshGroup(slot->mesh,i,edit);
    if (!status) {
        slot->rebuild |= flags!=g->UsrFlag;
        if (edit->flags & GRPEDIT_VTXMOD) slot->changed.insert(i);
    }
    return status;
}

int OrbiterScene::SetMaterial(DEVMESHHANDLE device,unsigned index,const MATERIAL* material)
{
    auto* slot=FindDevice(device);
    if (!slot || !material || index>=oapiMeshMaterialCount(slot->mesh)) return 1;
    auto* dest=oapiMeshMaterial(slot->mesh,index);
    if (std::memcmp(dest,material,sizeof(*dest))) { *dest=*material; slot->rebuild=true; }
    return 0;
}

bool OrbiterScene::SetTexture(DEVMESHHANDLE device,unsigned index,SURFHANDLE texture)
{
    auto* slot=FindDevice(device);
    if (!slot || !index || index>oapiMeshTextureCount(slot->mesh)) return false;
    if (oapiGetTextureHandle(slot->mesh,index)==texture) return true;
    if (!ReplaceTextureSlot(slot->mesh, index, texture)) return false;
    slot->rebuild = true;
    return true;
}

bool OrbiterScene::ReplaceTextureSlot(MESHHANDLE mesh, unsigned index, SURFHANDLE texture)
{
    if (oapiGetTextureHandle(mesh, index) == texture) return true;
    if (texture && !Lookup(texture)) return false;
    // oapiSetTexture releases the previous surface. The mesh owns a reference
    // to its replacement until another replacement or mesh destruction.
    Retain(texture);
    if (oapiSetTexture(mesh, index, texture)) return true;
    Release(texture);
    return false;
}

void OrbiterScene::RemoveVessel(OBJHANDLE handle) noexcept
{
    if (handle == pilot_) SetPilot(nullptr);
    scene_.RemoveShip(handle);
    vessels_.erase(handle);
    if (focus_ == handle) focus_ = nullptr;
}

void OrbiterScene::CloseWorld() noexcept
{
    SetPilot(nullptr);
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
    const EarthView& earth, unsigned height, bool vesselShadows, bool refreshShadow, bool terrainRecentered,
    const std::vector<CockpitDisplay>& displays)
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
        if (handle != focus_ && Dot(eye, eye) > maxRange * maxRange) {
            const auto it = vessels_.find(handle);
            if (it != vessels_.end() && it->second.pose.HasLocalVertices()) {
                // Release the distant visual, but keep module-owned attachment
                // frames moving and retain their bind pose for the next view.
                auto& visual = it->second;
                if (!visual.meshSlots.empty()) {
                    scene_.RemoveShip(handle);
                    auto pose = std::move(visual.pose);
                    pose.Reset({}, {}, {});
                    visual = {};
                    visual.pose = std::move(pose);
                }
                visual.pose.Update(*vessel);
                visual.retained = true;
            }
            continue;
        }
        auto& visual = vessels_[handle];
        visual.retained = true;
        const bool pilotView = handle == pilot_ && oapiCameraInternal();
        static const std::vector<CockpitDisplay> noDisplays;
        RefreshMeshes(*vessel, visual, pilotView, pilotView ? displays : noDisplays);
        const bool changed = visual.pose.Update(*vessel);
        if (visual.pose.Vertices().empty()) continue;
        if (changed) scene_.SetShipPose(handle, visual.pose.Vertices());
        update.poseUploaded |= changed;
        if (!vesselShadows) {
            if (!visual.shadow.empty()) {
                visual.shadow.clear();
                scene_.SetShadow(handle, visual.shadow);
            }
            visual.shadowTime.reset();
        } else if (visual.shadowTime != simTime || changed || refreshShadow) {
            terrain_.ProjectShadow(groundFrame, frame, visual.pose.Vertices(), visual.shadow);
            scene_.SetShadow(handle, visual.shadow);
            visual.shadowTime = simTime;
        }
        update.shadowDrawn |= !visual.shadow.empty();
        // Sphere against the four side planes and the eye. Orbiter's clip radius
        // includes parts extending beyond the nominal size, such as solar panels.
        if ((handle != focus_ || !oapiCameraInternal() || pilotView) && eye.z + radius > 0 &&
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

bool OrbiterScene::Present(unsigned width, unsigned height, bool vesselShadows, const std::vector<CockpitDisplay>& displays)
{
    if (!width || !height) return true;
    if (!worldOpen_) return scene_.Present({}, {}, {});
    const auto start = SDL_GetTicksNS();
    const auto focus = oapiGetFocusObject();
    SetPilot(oapiCameraInternal() && oapiCockpitMode() == COCKPIT_VIRTUAL ? focus : nullptr);
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
    const auto vessels = UpdateVessels(camera, groundFrame, earth, height, vesselShadows, tiles.switched || reanchorTime, tiles.recentered, displays);
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
