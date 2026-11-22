// Licensed under the MIT License
#include "RunwayTerrain.h"
#include "ZTreeMgr.h"
#ifndef _WIN32
#include "Production/NativeInterpreterSdk.h"
#endif

#include <algorithm>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <exception>
#include <mutex>
#include <queue>
#include <thread>
#include <set>
#include <sstream>
#include <stdexcept>

namespace orbiter::vulkan {
namespace {

constexpr double pi = 3.14159265358979323846;
constexpr int rootLevel = 4;
constexpr int detailLevel = 19;

int Rows(int level) { return 1 << (level - 4); }
double TileAngle(int level) { return pi / Rows(level); }
int WrapColumn(int level, int column)
{
    const auto columns = 2 * Rows(level);
    return (column % columns + columns) % columns;
}

TileKey At(int level, double lng, double lat)
{
    const auto angle = TileAngle(level);
    return {level, std::clamp(int(std::floor((pi / 2 - lat) / angle)), 0, Rows(level) - 1),
        WrapColumn(level, int(std::floor((std::remainder(lng, 2 * pi) + pi) / angle)))};
}

std::array<TileKey, 4> Children(const TileKey& key)
{
    return {{{key.level + 1, 2 * key.row, 2 * key.column},
        {key.level + 1, 2 * key.row, 2 * key.column + 1},
        {key.level + 1, 2 * key.row + 1, 2 * key.column},
        {key.level + 1, 2 * key.row + 1, 2 * key.column + 1}}};
}

VECTOR3 Radial(double lng, double lat)
{
    const double c = std::cos(lat);
    return {c * std::cos(lng), std::sin(lat), c * std::sin(lng)};
}

// Find the nearest point of the spherical latitude/longitude rectangle to the
// eye. This also works at the date line, poles and for the two hemisphere roots.
double ProjectedSize(const TileKey& key, double lng, double lat, double altitude, double radius,
    double focal, double horizonCosine)
{
    if (key.level == detailLevel) return 0;
    const double angle = TileAngle(key.level);
    const double mid = -pi + (key.column + 0.5) * angle;
    const double dlng = std::max(0.0, std::abs(std::remainder(lng - mid, 2 * pi)) - angle * 0.5);
    const double north = pi / 2 - key.row * angle;
    const double dx = std::cos(lat) * std::cos(dlng), dy = std::sin(lat);
    const double nearest = std::clamp(std::atan2(dy, dx), north - angle, north);
    const double cosine = std::clamp(dx * std::cos(nearest) + dy * std::sin(nearest), -1.0, 1.0);
    const double eyeRadius = radius + altitude;
    if (cosine < horizonCosine) return 0;
    const double range = std::sqrt(altitude * altitude + 2 * eyeRadius * radius * (1 - cosine));
    return radius * angle * focal / range;
}

struct TileTexture {
    TextureData image;
    float u, v, scale;
};

TileTexture LoadTile(ZTreeMgr& archive, const std::filesystem::path& filename, const TileKey& key)
{
    for (int level = key.level, stride = 1; level >= 4; --level, stride *= 2) {
        unsigned char* raw = nullptr;
        const auto size = archive.ReadData(level, key.row / stride, key.column / stride, &raw);
        const auto release = [&archive](unsigned char* ptr) { archive.ReleaseData(ptr); };
        const std::unique_ptr<unsigned char, decltype(release)> data(raw, release);
        if (!size) continue;
        const auto label = filename.string() + " [" + std::to_string(level) + "/" +
            std::to_string(key.row / stride) + "/" + std::to_string(key.column / stride) + "]";
        return {DecodeDds(std::vector<std::uint8_t>(raw, raw + size), label),
            float(key.column % stride) / stride, float(key.row % stride) / stride, 1.0f / stride};
    }
    throw std::runtime_error("Stock Earth surface tile has no usable ancestor");
}

} // namespace

// The worker owns its archive cursor. Jobs contain Earth-fixed geometry and
// sampled elevations, so no SDK or GPU calls cross threads.
class RunwayTerrain::Loader {
public:
    Loader(std::filesystem::path filename, std::filesystem::path imagery)
        : thread_([this, filename = std::move(filename), imagery = std::move(imagery)] {
            try {
                auto archive = ZTreeMgr::OpenArchiveFile(filename, ZTreeMgr::LAYER_SURF);
                std::unique_lock lock(mutex_);
                while (true) {
                    wake_.wait(lock, [this] { return stopping_ || !jobs_.empty(); });
                    if (stopping_) return;
                    Job job = std::move(jobs_.front());
                    jobs_.pop_front();
                    active_ = job.key;
                    lock.unlock();
                    Prepared result = BuildTile(std::move(job), *archive, filename, imagery);
                    lock.lock();
                    if (wanted_.count(result.key)) ready_.push_back(std::move(result));
                    active_.reset();
                }
            } catch (...) {
                std::lock_guard lock(mutex_);
                error_ = std::current_exception();
            }
        }) {}

    ~Loader()
    {
        {
            std::lock_guard lock(mutex_);
            stopping_ = true;
        }
        wake_.notify_one();
        thread_.join();
    }

    std::set<TileKey> Retarget(const std::set<TileKey>& wanted)
    {
        std::lock_guard lock(mutex_);
        std::set<TileKey> retained;
        const auto obsolete = [&](const auto& item) {
            if (!wanted.count(item.key)) return true;
            retained.insert(item.key);
            return false;
        };
        jobs_.erase(std::remove_if(jobs_.begin(), jobs_.end(), obsolete), jobs_.end());
        ready_.erase(std::remove_if(ready_.begin(), ready_.end(), obsolete), ready_.end());
        if (active_) retained.insert(*active_);
        wanted_ = wanted;
        return retained;
    }

    bool HasRoom()
    {
        std::lock_guard lock(mutex_);
        if (error_) std::rethrow_exception(error_);
        return jobs_.size() + ready_.size() + active_.has_value() < 12;
    }

    void Submit(Job job)
    {
        {
            std::lock_guard lock(mutex_);
            jobs_.push_back(std::move(job));
        }
        wake_.notify_one();
    }

    std::optional<Prepared> Take()
    {
        std::lock_guard lock(mutex_);
        if (error_) std::rethrow_exception(error_);
        if (ready_.empty()) return {};
        Prepared tile = std::move(ready_.front());
        ready_.pop_front();
        return tile;
    }

private:
    std::mutex mutex_;
    std::condition_variable wake_;
    std::deque<Job> jobs_;
    std::deque<Prepared> ready_;
    std::optional<TileKey> active_;
    std::set<TileKey> wanted_;
    std::exception_ptr error_;
    bool stopping_ = false;
    std::thread thread_;
};

RunwayTerrain::RunwayTerrain() = default;
RunwayTerrain::~RunwayTerrain()
{
    Close();
}

void RunwayTerrain::Open(const std::filesystem::path& filename, const VECTOR3& origin)
{
    Close();
    char name[] = "Earth";
    earth_ = oapiGetGbodyByName(name);
    if (!earth_) throw std::runtime_error("Stock Runway 33 terrain requires Earth");
    filename_ = filename;
    if (const char* path = SDL_getenv("ORBITER_VULKAN_KENNEDY_IMAGERY"); path && *path) {
        imagery_ = std::filesystem::path(path);
        if (!std::filesystem::is_directory(imagery_))
            throw std::runtime_error("Kennedy imagery directory does not exist: " + imagery_.string());
    }
    archive_ = ZTreeMgr::OpenArchiveFile(filename_, ZTreeMgr::LAYER_SURF);
    loader_ = std::make_unique<Loader>(filename_, imagery_);
    elevationCache_ = InitTileCache(48);
    Reanchor(origin);
}

void RunwayTerrain::Reanchor(const VECTOR3& origin)
{
    double distance;
    oapiGlobalToEqu(earth_, origin, &longitude_, &latitude_, &distance);
    radius_ = oapiGetSize(earth_);
    altitude_ = oapiSurfaceElevationEx(earth_, longitude_, latitude_, 0, elevationCache_);
    const auto slat = std::sin(latitude_);
    const auto clat = std::cos(latitude_);
    const auto slng = std::sin(longitude_);
    const auto clng = std::cos(longitude_);
    local_.axes = {{{-slng, 0, clng}, {clat * clng, slat, clat * slng}, {-slat * clng, clat, -slat * slng}}};
    local_.origin = Scale(local_.axes[1], radius_ + altitude_);
}

bool RunwayTerrain::NeedsReanchor(const VECTOR3& position) const
{
    // Keep the regional meshes in a well-conditioned float coordinate frame
    // during long flights and camera jumps, including across the antimeridian.
    const auto radial = ObjectFrame(earth_).ToLocal(position);
    constexpr double cosTwoDegrees = 0.9993908270190958;
    return Dot(radial, local_.axes[1]) < cosTwoDegrees * std::sqrt(Dot(radial, radial));
}

void RunwayTerrain::Close()
{
    loader_.reset();
    sampling_.reset();
    tiles_.clear();
    archive_.reset();
    imagery_.clear();
    visible_.clear();
    wanted_.clear();
    pending_.clear();
    requested_ = {0, 0, 0};
    selectedAltitude_ = -1;
    if (elevationCache_) ReleaseTileCache(elevationCache_);
    elevationCache_ = nullptr;
    earth_ = nullptr;
}

void RunwayTerrain::RetainTiles(Scene& scene)
{
    scene.SelectTiles(visible_, wanted_);
    for (auto it = tiles_.begin(); it != tiles_.end();) {
        if (visible_.count(it->first) || wanted_.count(it->first)) ++it;
        else it = tiles_.erase(it);
    }
}

void RunwayTerrain::CollectVisible(const TileKey& key, std::set<TileKey>& selected) const
{
    const auto children = Children(key);
    const auto ready = [this](const TileKey& child) { return tiles_.count(child) != 0; };
    if (key.level == detailLevel || !wanted_.count(children.front()) ||
        !std::all_of(children.begin(), children.end(), ready)) {
        selected.insert(key);
        return;
    }
    for (const auto& child : children) CollectVisible(child, selected);
}

TerrainUpdate RunwayTerrain::Update(const EarthView& view, unsigned height, Scene& scene)
{
    const auto& eye = view.camera.origin;
    const double longitude = std::atan2(eye.z, eye.x);
    const double latitude = std::atan2(eye.y, std::hypot(eye.x, eye.z));
    const double altitude = std::max(1.0, view.altitude);
    const double focal = height * 0.5 * view.vertical;
    // Quantize motion only for selection. Rendering always uses the exact eye.
    const int tracking = std::clamp(int(std::ceil(std::log2(radius_ * pi * focal /
        (std::max(100.0, altitude) * 510.0)))) + rootLevel + 3, rootLevel, detailLevel);
    const auto center = At(tracking, longitude, latitude);
    TerrainUpdate result;
    result.recentered = !(center == requested_) || selectedAltitude_ < 0 ||
        std::abs(altitude - selectedAltitude_) > 0.1 * std::max(20.0, selectedAltitude_) ||
        std::abs(focal - selectedFocal_) > 0.05 * selectedFocal_;
    const auto publish = [&](Prepared tile) {
        scene.StageTile(tile.key, tile.mesh);
        result.imagery += tile.tile.regionalImagery;
        tiles_.emplace(tile.key, std::move(tile.tile));
        ++result.staged;
    };
    if (result.recentered) {
        wanted_.clear();
        // Refine the largest apparent patches first. Limit the resident target,
        // particularly near a pole where all longitude wedges meet.
        constexpr size_t maxDesiredTiles = 1024;
        const double horizon = std::acos(radius_ / (radius_ + altitude))
                             + std::acos(radius_ / (radius_ + 9000.0));
        const double horizonCosine = std::cos(horizon);
        std::priority_queue<std::pair<double, TileKey>> candidates;
        const auto consider = [&](const TileKey& key) {
            wanted_.insert(key);
            const double pixels = ProjectedSize(key, longitude, latitude, altitude, radius_, focal, horizonCosine);
            if (pixels > 510.0) candidates.emplace(pixels, key);
        };
        for (const auto& key : roots_) consider(key);
        while (!candidates.empty() && wanted_.size() + 4 <= maxDesiredTiles) {
            const auto parent = candidates.top().second;
            candidates.pop();
            for (const auto& child : Children(parent)) consider(child);
        }
        RetainTiles(scene);
        selectedAltitude_ = altitude;
        selectedFocal_ = focal;
        const auto retained = loader_->Retarget(wanted_);
        if (sampling_ && !wanted_.count(sampling_->key)) sampling_.reset();

        for (const auto& key : roots_) {
            if (!tiles_.count(key)) publish(BuildTile(StartTile(key), *archive_, filename_, imagery_));
        }
        pending_.clear();
        for (const auto& key : wanted_) {
            if (!tiles_.count(key) && !retained.count(key) && !(sampling_ && sampling_->key == key))
                pending_.push_back(key);
        }
        // Complete each sibling group on the way to the camera tile first.
        // This brings the runway into focus before refining distant terrain.
        std::stable_partition(pending_.begin(), pending_.end(), [&](const TileKey& key) {
            const auto target = At(key.level - 1, longitude, latitude);
            return key.row / 2 == target.row && key.column / 2 == target.column;
        });
        requested_ = center;
    }

    using Clock = std::chrono::steady_clock;
    const auto deadline = Clock::now() + std::chrono::milliseconds(2);
    while (result.staged < 12 && Clock::now() < deadline) {
        auto prepared = loader_->Take();
        if (!prepared) break;
        publish(std::move(*prepared));
    }
    // The engine elevation service shares archive cursors and plugin filters
    // with the simulation. Sample one raster row at a time within the budget.
    while (Clock::now() < deadline && (sampling_ || !pending_.empty())) {
        if (!sampling_) {
            if (!loader_->HasRoom()) break;
            sampling_ = StartTile(pending_.front());
            pending_.pop_front();
        }
        SampleRow(*sampling_);
        const auto stride = size_t(sampling_->tile.divisions + 1);
        if (sampling_->elevations.size() == stride * stride) {
            loader_->Submit(std::move(*sampling_));
            sampling_.reset();
        }
    }

    const auto ready = [this](const TileKey& key) { return tiles_.count(key) != 0; };
    if ((result.recentered || result.staged) && std::all_of(roots_.begin(), roots_.end(), ready)) {
        std::set<TileKey> selected;
        for (const auto& root : roots_) CollectVisible(root, selected);
        result.switched = selected != visible_;
        if (result.switched) {
            visible_.swap(selected);
            RetainTiles(scene);
        }
    }
    if (result.recentered) {
        std::ostringstream message;
        message << "Vulkan Earth tiles: center " << center.level << '/' << center.row << '/' << center.column
                << ", " << visible_.size() << " visible, "
                << std::count_if(wanted_.begin(), wanted_.end(), [&](const TileKey& key) { return !tiles_.count(key); })
                << " waiting";
        SceneLog(message.str());
    }
    return result;
}

RunwayTerrain::Job RunwayTerrain::StartTile(const TileKey& key) const
{
    const auto angle = TileAngle(key.level);
    const double west = -pi + key.column * angle;
    const double north = pi / 2 - key.row * angle;
    Job job{key, {}, {}, west, north, angle, radius_};
    auto& tile = job.tile;
    tile.key = key;
    tile.origin = Scale(Radial(west + angle * 0.5, north - angle * 0.5), radius_);
    tile.divisions = key.level <= 6 || key.level == detailLevel ? 64 : 16;
    const auto stride = tile.divisions + 1;
    if (key.level <= 8) job.elevations.assign(stride * stride, 0.0);
    else job.elevations.reserve(stride * stride);
    return job;
}

void RunwayTerrain::SampleRow(Job& job)
{
    const auto steps = job.tile.divisions;
    const int row = int(job.elevations.size()) / (steps + 1);
    if (row > steps) return;
    const double lat = job.north - double(row) / steps * job.angle;
    const int level = job.key.level == detailLevel ? 0 : job.key.level + 3;
    for (int column = 0; column <= steps; ++column) {
        const double lng = std::remainder(job.west + double(column) / steps * job.angle, 2 * pi);
        job.elevations.push_back(oapiSurfaceElevationEx(earth_, lng, lat, level, elevationCache_));
    }
}

RunwayTerrain::Prepared RunwayTerrain::BuildTile(Job job, ZTreeMgr& archive,
    const std::filesystem::path& filename, const std::filesystem::path& imagery)
{
    const auto& key = job.key;
    auto& tile = job.tile;
    TerrainMesh mesh;
    TileTexture texture;
    if (!imagery.empty() && key.level >= 16) {
        const auto override = imagery / std::to_string(key.level) / std::to_string(key.row)
            / (std::to_string(key.column) + ".dds");
        if (std::filesystem::is_regular_file(override)) {
            texture = {ReadDds(override), 0, 0, 1};
            tile.regionalImagery = true;
        }
    }
    if (!tile.regionalImagery) texture = LoadTile(archive, filename, key);
    mesh.texture = std::move(texture.image);
    mesh.origin = tile.origin;
    const auto steps = tile.divisions;
    const auto stride = steps + 1;
    mesh.vertices.reserve(stride * stride + 4 * stride);
    mesh.indices.reserve(6 * steps * (steps + 4));

    for (int row = 0; row <= steps; ++row) {
        const auto v = double(row) / steps;
        const auto lat = job.north - v * job.angle;
        const auto clat = std::cos(lat), slat = std::sin(lat);
        for (int column = 0; column <= steps; ++column) {
            const auto u = double(column) / steps;
            const auto lng = std::remainder(job.west + u * job.angle, 2 * pi);
            const auto elevation = job.elevations[row * stride + column];
            const VECTOR3 up{clat * std::cos(lng), slat, clat * std::sin(lng)};
            const auto pos = Subtract(Scale(up, job.radius + elevation), tile.origin);
            if (key.level >= 9) tile.points.push_back({float(pos.x), float(pos.y), float(pos.z)});
            mesh.vertices.push_back({{float(pos.x), float(pos.y), float(pos.z)}, {float(up.x), float(up.y), float(up.z)},
                {texture.u + texture.scale * float(u), texture.v + texture.scale * float(v)}});
        }
    }
    for (unsigned row = 0; row < unsigned(steps); ++row) {
        for (unsigned col = 0; col < unsigned(steps); ++col) {
            const auto a = row * stride + col;
            const auto b = a + stride;
            mesh.indices.insert(mesh.indices.end(), {a, a + 1, b, a + 1, b + 1, b});
        }
    }

    // Extend the edge below the surface to cover gaps between different LODs.
    const float skirt = float(std::max(30.0, 4 * job.radius * (1 - std::cos(job.angle / steps))
        + std::min(10000.0, 0.6 * job.radius * job.angle / steps)));
    const auto edge = [&mesh, steps, skirt](unsigned start, unsigned increment) {
        const auto first = unsigned(mesh.vertices.size());
        for (unsigned i = 0; i <= unsigned(steps); ++i) {
            auto vertex = mesh.vertices[start + increment * i];
            for (int axis = 0; axis < 3; ++axis) vertex.position[axis] -= skirt * vertex.normal[axis];
            mesh.vertices.push_back(vertex);
        }
        for (unsigned i = 0; i < unsigned(steps); ++i) {
            const auto a = start + increment * i;
            const auto b = first + i;
            mesh.indices.insert(mesh.indices.end(), {a, a + increment, b, a + increment, b + 1, b});
        }
    };
    edge(0, 1);
    edge(steps * stride, 1);
    edge(0, stride);
    edge(steps, stride);
    return {key, std::move(tile), std::move(mesh)};
}

double RunwayTerrain::Tile::Height(double lng, double lat, const SceneFrame& ground) const
{
    const double angle = TileAngle(key.level);
    const double west = -pi + key.column * angle, north = pi / 2 - key.row * angle;
    const double gx = std::clamp(std::remainder(lng - west, 2*pi) / angle * divisions, 0.0, double(divisions));
    const double gz = std::clamp((north - lat) / angle * divisions, 0.0, double(divisions));
    const auto col = std::min(int(gx), divisions - 1);
    const auto row = std::min(int(gz), divisions - 1);
    const auto u = gx - col;
    const auto v = gz - row;
    const auto stride = divisions + 1;
    const auto a = row * stride + col;
    const auto b = a + stride;
    const double offset = Dot(Subtract(origin, ground.origin), ground.axes[1]);
    const auto y = [&](int i) { const auto& p = points[i]; return Dot({p[0],p[1],p[2]}, ground.axes[1]); };
    if (u + v <= 1) return offset + (1 - u - v) * y(a) + u * y(a + 1) + v * y(b);
    return offset + (u + v - 1) * y(b + 1) + (1 - u) * y(b) + (1 - v) * y(a + 1);
}

const RunwayTerrain::Tile* RunwayTerrain::FindTile(double lng, double lat) const
{
    for (int level = detailLevel; level >= 9; --level) {
        const auto key = At(level, lng, lat);
        if (visible_.count(key)) return &tiles_.at(key);
    }
    return nullptr;
}

void RunwayTerrain::ProjectShadow(const SceneFrame& ground, const SceneFrame& ship, const std::vector<Vertex>& vertices,
    std::vector<Vertex>& projected) const
{
    projected.clear();
    const auto origin = ground.ToLocal(ship.origin);
    // The terrain origin can be hundreds of kilometres behind a low-flying vessel.
    // Cull by height above Earth's reference sphere, independently of reanchoring.
    const auto radial = local_.ToGlobal(origin);
    const double limit = radius_ + 100000.0;
    if (Dot(radial, radial) > limit * limit || Dot(radial, local_.axes[1]) <= 0) return;
    const auto sun = Subtract(ground.ToLocal(SunPosition()), origin);
    if (sun.y <= 0) return;
    const auto rayX = sun.x / sun.y;
    const auto rayZ = sun.z / sun.y;
    const SceneFrame localShip{origin, {{
        {Dot(ground.axes[0], ship.axes[0]), Dot(ground.axes[1], ship.axes[0]), Dot(ground.axes[2], ship.axes[0])},
        {Dot(ground.axes[0], ship.axes[1]), Dot(ground.axes[1], ship.axes[1]), Dot(ground.axes[2], ship.axes[1])},
        {Dot(ground.axes[0], ship.axes[2]), Dot(ground.axes[1], ship.axes[2]), Dot(ground.axes[2], ship.axes[2])}
    }}};
    const Tile* tile = nullptr;
    projected.reserve(vertices.size());
    for (const auto& vertex : vertices) {
        const auto p = localShip.ToGlobal({vertex.position[0], vertex.position[1], vertex.position[2]});
        double east = p.x, north = p.z, groundHeight = 0;
        for (int step = 0; step < 4; ++step) {
            const auto point = local_.ToGlobal({east, groundHeight, north});
            const double lng = std::atan2(point.z, point.x), lat = std::atan2(point.y, std::hypot(point.x, point.z));
            if (!tile || !(At(tile->key.level, lng, lat) == tile->key)) tile = FindTile(lng, lat);
            if (!tile) {
                // At sunrise or sunset the shadow may extend beyond visible terrain.
                projected.clear();
                return;
            }
            groundHeight = tile->Height(lng, lat, local_);
            if (step == 3) break;
            const double height = std::max(0.0, p.y - groundHeight);
            const double nextEast = p.x - height * rayX, nextNorth = p.z - height * rayZ;
            const bool converged = std::abs(nextEast - east) + std::abs(nextNorth - north) < 0.001;
            east = nextEast;
            north = nextNorth;
            if (converged) break;
        }
        const auto y = groundHeight + 0.025;
        projected.push_back({{float(east), float(y), float(north)}, {0, 1, 0}, {0, 0}});
    }
}

VECTOR3 RunwayTerrain::DrapeSurfaceTile(const VECTOR3& local) const
{
    // Orbiter exports legacy tile meshes on a sphere, without Earth elevation.
    const auto point = local_.ToGlobal(local);
    const double lng = std::atan2(point.z, point.x);
    const double lat = std::atan2(point.y, std::hypot(point.x, point.z));
    const double elevation = oapiSurfaceElevationEx(earth_, lng, lat, 0, elevationCache_);
    return local_.ToLocal(Scale(point, (radius_ + elevation) / std::sqrt(Dot(point, point))));
}

VECTOR3 RunwayTerrain::BasePosition(double lng, double lat) const
{
    const double c = std::cos(lat);
    return local_.ToLocal(Scale({c * std::cos(lng), std::sin(lat), c * std::sin(lng)}, radius_));
}

SceneFrame RunwayTerrain::BaseFrame(double lng, double lat) const
{
    const double slng = std::sin(lng), clng = std::cos(lng), slat = std::sin(lat), clat = std::cos(lat);
    // Orbiter base axes are south, up, east. Derive them from the configured
    // location so the very first paused frame also has a valid base pose.
    const std::array<VECTOR3, 3> axes = {{{clng*slat, -clat, slng*slat},
        {clng*clat, slat, slng*clat}, {-slng, 0, clng}}};
    const double elevation = oapiSurfaceElevationEx(earth_, lng, lat, 0, elevationCache_);
    SceneFrame result;
    result.origin = local_.ToLocal(Scale(axes[1], radius_ + elevation));
    for (unsigned i = 0; i < 3; ++i)
        result.axes[i] = {Dot(axes[i], local_.axes[0]), Dot(axes[i], local_.axes[1]), Dot(axes[i], local_.axes[2])};
    return result;
}

double RunwayTerrain::LeafArea() const
{
    // Fraction of the two root rectangles covered by the selected leaves.
    double area = 0;
    for (const auto& key : visible_) area += std::ldexp(0.5, -2 * (key.level - rootLevel));
    return area;
}

size_t RunwayTerrain::DetailCount() const
{
    return std::count_if(visible_.begin(), visible_.end(), [](const TileKey& key) { return key.level == detailLevel; });
}

EarthView RunwayTerrain::View(unsigned width, unsigned height) const
{
    const auto earth = ObjectFrame(earth_);
    VECTOR3 camera;
    MATRIX3 rotation;
    oapiCameraGlobalPos(&camera);
    oapiCameraRotationMatrix(&rotation);
    EarthView view;
    view.camera.origin = earth.ToLocal(camera);
    const auto axes = Axes(rotation);
    for (int i = 0; i < 3; ++i) view.camera.axes[i] = DirectionIn(earth, axes[i]);
    view.ground = local_;
    const auto sun = earth.ToLocal(SunPosition());
    view.sun = Scale(sun, 1.0 / std::sqrt(Dot(sun, sun)));
    view.radius = radius_;
    view.altitude = std::sqrt(Dot(view.camera.origin, view.camera.origin)) - radius_;
    view.vertical = 1.0 / std::tan(oapiCameraAperture());
    view.horizontal = view.vertical * height / width;
    return view;
}

SceneFrame RunwayTerrain::Frame() const
{
    const auto earth = ObjectFrame(earth_);
    return {earth.ToGlobal(local_.origin),
        {earth.Rotate(local_.axes[0]), earth.Rotate(local_.axes[1]), earth.Rotate(local_.axes[2])}};
}

} // namespace orbiter::vulkan
