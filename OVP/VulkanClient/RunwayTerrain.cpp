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
#include <thread>
#include <set>
#include <sstream>
#include <stdexcept>

namespace orbiter::vulkan {
namespace {

constexpr double pi = 3.14159265358979323846;
constexpr int coarseLevel = 11;
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

void Select(const TileKey& key, const TileKey& focus, std::set<TileKey>& selection)
{
    selection.insert(key);
    const int stride = 1 << (detailLevel - key.level);
    const auto columnDistance = std::abs(key.column - focus.column / stride);
    const auto columns = 2 * Rows(key.level);
    if (key.level == detailLevel || std::abs(key.row - focus.row / stride) > 1 ||
        std::min(columnDistance, columns - columnDistance) > 1) return;
    for (const auto& child : Children(key)) Select(child, focus, selection);
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

// The worker owns its archive cursor. Jobs contain a snapshot of the tangent
// frame and Orbiter elevations, so no SDK or GPU calls cross threads.
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
                    const auto region = region_;
                    lock.unlock();
                    Prepared result = BuildTile(std::move(job), *archive, filename, imagery);
                    lock.lock();
                    if (region == region_ && wanted_.count(result.key)) ready_.push_back(std::move(result));
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

    std::set<TileKey> Retarget(unsigned region, const std::set<TileKey>& wanted)
    {
        std::lock_guard lock(mutex_);
        std::set<TileKey> retained;
        if (region != region_) {
            jobs_.clear();
            ready_.clear();
            active_.reset();
        } else {
            const auto obsolete = [&](const auto& item) {
                if (!wanted.count(item.key)) return true;
                retained.insert(item.key);
                return false;
            };
            jobs_.erase(std::remove_if(jobs_.begin(), jobs_.end(), obsolete), jobs_.end());
            ready_.erase(std::remove_if(ready_.begin(), ready_.end(), obsolete), ready_.end());
            if (active_) retained.insert(*active_);
        }
        region_ = region;
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
    unsigned region_ = 0;
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
    ++region_;
    tiles_.clear();
    visible_.clear();
    sampling_.reset();
    requested_ = {0, 0, 0};
    double distance;
    oapiGlobalToEqu(earth_, origin, &longitude_, &latitude_, &distance);
    radius_ = oapiGetSize(earth_);
    altitude_ = oapiSurfaceElevationEx(earth_, longitude_, latitude_, 0, elevationCache_);
    const auto slat = std::sin(latitude_);
    const auto clat = std::cos(latitude_);
    const auto slng = std::sin(longitude_);
    const auto clng = std::cos(longitude_);
    eastScale_ = radius_ * std::max(clat, 1e-12);
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
    roots_.clear();
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

TerrainUpdate RunwayTerrain::Update(const VECTOR3& position, Scene& scene)
{
    double longitude, latitude, distance;
    oapiGlobalToEqu(earth_, position, &longitude, &latitude, &distance);
    const auto center = At(detailLevel, longitude, latitude);
    TerrainUpdate result;
    result.recentered = !(center == requested_);
    const auto publish = [&](Prepared tile) {
        scene.StageTile(tile.key, tile.mesh);
        result.imagery += tile.tile.regionalImagery;
        tiles_.emplace(tile.key, std::move(tile.tile));
        ++result.staged;
    };
    if (result.recentered) {
        const auto root = At(coarseLevel, longitude, latitude);
        roots_.clear();
        wanted_.clear();
        for (int row = std::max(0, root.row - 1); row <= std::min(Rows(coarseLevel) - 1, root.row + 1); ++row) {
            for (int x = -1; x <= 1; ++x) {
                roots_.push_back({coarseLevel, row, WrapColumn(coarseLevel, root.column + x)});
                Select(roots_.back(), center, wanted_);
            }
        }
        RetainTiles(scene);
        const bool needCoverage = !tiles_.count(root);
        if (needCoverage && !visible_.empty()) {
            // A cut can outrun the coarse neighborhood even within one tangent
            // frame. Invalidate old jobs before supplying its new roots.
            ++region_;
            sampling_.reset();
        }
        const auto retained = loader_->Retarget(region_, wanted_);
        if (sampling_ && !wanted_.count(sampling_->key)) sampling_.reset();

        // Supply immediate, textured coverage, including across a cold camera
        // cut. Only missing coarse parents use the render thread's archive.
        if (needCoverage) {
            for (const auto& key : roots_) {
                if (tiles_.count(key)) continue;
                auto job = StartTile(key);
                const int rows = job.tile.divisions + 1;
                for (int row = 0; row < rows; ++row) SampleRow(job);
                publish(BuildTile(std::move(job), *archive_, filename_, imagery_));
            }
        }

        pending_.clear();
        for (const auto& key : wanted_) {
            if (!tiles_.count(key) && !retained.count(key) && !(sampling_ && sampling_->key == key))
                pending_.push_back(key);
        }
        // Complete each sibling group on the way to the camera tile first.
        // This brings the runway into focus before refining distant terrain.
        std::stable_partition(pending_.begin(), pending_.end(), [&](const TileKey& key) {
            if (key.level == coarseLevel) return true;
            const int shift = detailLevel - key.level + 1;
            return key.row / 2 == (center.row >> shift) && key.column / 2 == (center.column >> shift);
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
        if (sampling_->tile.heights.size() == stride * stride) {
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
    const auto left = std::remainder(key.column * angle - pi - longitude_, 2 * pi);
    const auto top = pi / 2 - key.row * angle;
    Job job{key, {}, local_, longitude_ + left, top, angle, radius_};
    auto& tile = job.tile;
    tile.divisions = key.level == detailLevel ? 64 : 16;
    tile.x = left * eastScale_;
    tile.z = (top - latitude_) * radius_;
    tile.width = angle * eastScale_;
    tile.length = angle * radius_;
    const auto stride = tile.divisions + 1;
    tile.heights.reserve(stride * stride);
    return job;
}

void RunwayTerrain::SampleRow(Job& job)
{
    const auto steps = job.tile.divisions;
    const int row = int(job.tile.heights.size()) / (steps + 1);
    const double lat = job.north - double(row) / steps * job.angle;
    const int level = job.key.level == detailLevel ? 0 : job.key.level + 3;
    for (int column = 0; column <= steps; ++column) {
        const double lng = std::remainder(job.west + double(column) / steps * job.angle, 2 * pi);
        job.tile.heights.push_back(oapiSurfaceElevationEx(earth_, lng, lat, level, elevationCache_));
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
            const auto elevation = tile.heights[row * stride + column];
            const VECTOR3 up{clat * std::cos(lng), slat, clat * std::sin(lng)};
            const auto pos = job.frame.ToLocal(Scale(up, job.radius + elevation));
            tile.heights[row * stride + column] = pos.y;
            mesh.vertices.push_back({{float(pos.x), float(pos.y), float(pos.z)}, {0, 1, 0},
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
    const auto edge = [&mesh, steps](unsigned start, unsigned increment) {
        const auto first = unsigned(mesh.vertices.size());
        for (unsigned i = 0; i <= unsigned(steps); ++i) {
            auto vertex = mesh.vertices[start + increment * i];
            vertex.position[1] -= 30.0f;
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

bool RunwayTerrain::Tile::Contains(double east, double north) const
{
    return east >= x && east <= x + width && north <= z && north >= z - length;
}

double RunwayTerrain::Tile::Height(double east, double north) const
{
    const auto gx = std::clamp((east - x) * divisions / width, 0.0, double(divisions));
    const auto gz = std::clamp((z - north) * divisions / length, 0.0, double(divisions));
    const auto col = std::min(int(gx), divisions - 1);
    const auto row = std::min(int(gz), divisions - 1);
    const auto u = gx - col;
    const auto v = gz - row;
    const auto stride = divisions + 1;
    const auto a = row * stride + col;
    const auto b = a + stride;
    if (u + v <= 1) return (1 - u - v) * heights[a] + u * heights[a + 1] + v * heights[b];
    return (u + v - 1) * heights[b + 1] + (1 - u) * heights[b] + (1 - v) * heights[a + 1];
}

std::array<double, 2> RunwayTerrain::GridPosition(double east, double height, double north) const
{
    // Mesh vertices use the sphere. Height interpolation uses the source
    // raster's longitude/latitude grid, also for rays spanning several tiles.
    const auto point = local_.ToGlobal({east, height, north});
    const double lng = std::atan2(point.z, point.x);
    const double lat = std::atan2(point.y, std::hypot(point.x, point.z));
    return {std::remainder(lng - longitude_, 2 * pi) * eastScale_, (lat - latitude_) * radius_};
}

const RunwayTerrain::Tile* RunwayTerrain::FindTile(double east, double north) const
{
    const auto lng = longitude_ + east / eastScale_;
    const auto lat = latitude_ + north / radius_;
    for (int level = detailLevel; level >= coarseLevel; --level) {
        const auto key = At(level, lng, lat);
        if (!visible_.count(key)) continue;
        const auto it = tiles_.find(key);
        if (it != tiles_.end()) return &it->second;
    }
    return nullptr;
}

void RunwayTerrain::ProjectShadow(const SceneFrame& ground, const SceneFrame& ship, const std::vector<Vertex>& vertices,
    std::vector<Vertex>& projected) const
{
    projected.clear();
    const auto origin = ground.ToLocal(ship.origin);
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
            const auto grid = GridPosition(east, groundHeight, north);
            if (!tile || !tile->Contains(grid[0], grid[1])) tile = FindTile(grid[0], grid[1]);
            if (!tile) {
                // At sunrise or sunset the shadow may extend beyond visible terrain.
                projected.clear();
                return;
            }
            groundHeight = tile->Height(grid[0], grid[1]);
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

size_t RunwayTerrain::DetailCount() const
{
    return std::count_if(visible_.begin(), visible_.end(), [](const TileKey& key) { return key.level == detailLevel; });
}

SceneFrame RunwayTerrain::Frame() const
{
    const auto earth = ObjectFrame(earth_);
    return {earth.ToGlobal(local_.origin),
        {earth.Rotate(local_.axes[0]), earth.Rotate(local_.axes[1]), earth.Rotate(local_.axes[2])}};
}

} // namespace orbiter::vulkan
