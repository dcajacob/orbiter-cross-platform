// Licensed under the MIT License
#include "RunwayTerrain.h"
#include "ZTreeMgr.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <set>
#include <sstream>
#include <stdexcept>

namespace orbiter::vulkan {
namespace {

constexpr double pi = 3.14159265358979323846;
constexpr int coarseLevel = 13;
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

void Select(const TileKey& key, const TileKey& focus, std::set<TileKey>& selection)
{
    const int stride = 1 << (detailLevel - key.level);
    const auto columnDistance = std::abs(key.column - focus.column / stride);
    const auto columns = 2 * Rows(key.level);
    if (key.level == detailLevel || std::abs(key.row - focus.row / stride) > 1 ||
        std::min(columnDistance, columns - columnDistance) > 1) {
        selection.insert(key);
        return;
    }
    for (int y = 0; y < 2; ++y)
        for (int x = 0; x < 2; ++x)
            Select({key.level + 1, 2 * key.row + y, 2 * key.column + x}, focus, selection);
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

RunwayTerrain::RunwayTerrain() = default;
RunwayTerrain::~RunwayTerrain() = default;

void RunwayTerrain::Open(const std::filesystem::path& filename, const VECTOR3& origin)
{
    Close();
    char name[] = "Earth";
    earth_ = oapiGetGbodyByName(name);
    if (!earth_) throw std::runtime_error("Stock Runway 33 terrain requires Earth");
    filename_ = filename;
    archive_ = ZTreeMgr::OpenArchiveFile(filename_, ZTreeMgr::LAYER_SURF);
    double distance;
    oapiGlobalToEqu(earth_, origin, &longitude_, &latitude_, &distance);
    radius_ = oapiGetSize(earth_);
    altitude_ = oapiSurfaceElevation(earth_, longitude_, latitude_);
    const auto slat = std::sin(latitude_);
    const auto clat = std::cos(latitude_);
    const auto slng = std::sin(longitude_);
    const auto clng = std::cos(longitude_);
    eastScale_ = radius_ * clat;
    local_.axes = {{{-slng, 0, clng}, {clat * clng, slat, clat * slng}, {-slat * clng, clat, -slat * slng}}};
    local_.origin = Scale(local_.axes[1], radius_ + altitude_);
}

void RunwayTerrain::Close()
{
    tiles_.clear();
    archive_.reset();
    visible_.clear();
    wanted_.clear();
    pending_.clear();
    requested_ = {0, 0, 0};
    switching_ = false;
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

bool RunwayTerrain::Update(const VECTOR3& position, Scene& scene)
{
    double longitude, latitude, distance;
    oapiGlobalToEqu(earth_, position, &longitude, &latitude, &distance);
    const auto center = At(detailLevel, longitude, latitude);
    if (center.level != requested_.level || center.row != requested_.row || center.column != requested_.column) {
        const auto root = At(coarseLevel, longitude, latitude);
        wanted_.clear();
        for (int row = std::max(0, root.row - 1); row <= std::min(Rows(coarseLevel) - 1, root.row + 1); ++row)
            for (int x = -1; x <= 1; ++x)
                Select({coarseLevel, row, WrapColumn(coarseLevel, root.column + x)}, center, wanted_);

        RetainTiles(scene);
        pending_.clear();
        for (const auto& key : wanted_) {
            if (!tiles_.count(key)) pending_.push_back(key);
        }
        requested_ = center;
        switching_ = true;
        loaded_ = 0;
    }

    if (!switching_) return false;
    // The Orbiter elevation API belongs to the simulation thread. Stage tiles
    // within a frame budget and keep the previous coverage until the new LODs are ready.
    using Clock = std::chrono::steady_clock;
    const auto deadline = Clock::now() + std::chrono::milliseconds(5);
    while (!pending_.empty()) {
        const auto key = pending_.back();
        TerrainMesh mesh;
        auto tile = BuildTile(key, mesh);
        scene.StageTile(key, mesh);
        tiles_.emplace(key, std::move(tile));
        pending_.pop_back();
        ++loaded_;
        if (!visible_.empty() && Clock::now() >= deadline) break;
    }
    if (!pending_.empty()) return false;

    visible_.swap(wanted_);
    wanted_.clear();
    RetainTiles(scene);
    switching_ = false;
    std::ostringstream message;
    message << "Vulkan Earth tiles: center " << center.level << '/' << center.row << '/' << center.column
            << ", " << visible_.size() << " visible, " << loaded_ << " loaded";
    SceneLog(message.str());
    return true;
}

RunwayTerrain::Tile RunwayTerrain::BuildTile(const TileKey& key, TerrainMesh& mesh)
{
    auto texture = LoadTile(*archive_, filename_, key);
    Tile tile;
    tile.divisions = key.level == detailLevel ? 64 : 16;
    const auto angle = TileAngle(key.level);
    const auto left = std::remainder(key.column * angle - pi - longitude_, 2 * pi);
    const auto top = pi / 2 - key.row * angle;
    tile.x = left * eastScale_;
    tile.z = (top - latitude_) * radius_;
    tile.width = angle * eastScale_;
    tile.length = angle * radius_;
    mesh.texture = std::move(texture.image);
    const auto steps = tile.divisions;
    const auto stride = steps + 1;
    tile.heights.reserve(stride * stride);

    for (int row = 0; row <= steps; ++row) {
        const auto v = double(row) / steps;
        const auto z = tile.z - v * tile.length;
        for (int column = 0; column <= steps; ++column) {
            const auto u = double(column) / steps;
            const auto x = tile.x + u * tile.width;
            const auto lng = std::remainder(longitude_ + left + u * angle, 2 * pi);
            const auto elevation = oapiSurfaceElevation(earth_, lng, top - v * angle);
            const auto y = elevation - altitude_ - (x*x + z*z) / (2 * radius_);
            tile.heights.push_back(y);
            mesh.vertices.push_back({{float(x), float(y), float(z)}, {0, 1, 0},
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
    return tile;
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
    const auto* tile = FindTile(origin.x, origin.z);
    projected.reserve(vertices.size());
    for (const auto& vertex : vertices) {
        const auto p = localShip.ToGlobal({vertex.position[0], vertex.position[1], vertex.position[2]});
        double east = p.x, north = p.z;
        for (int step = 0; step < 3; ++step) {
            if (!tile || !tile->Contains(east, north)) tile = FindTile(east, north);
            if (!tile) break;
            const auto height = std::max(0.0, p.y - tile->Height(east, north));
            east = p.x - height * rayX;
            north = p.z - height * rayZ;
        }
        if (!tile || !tile->Contains(east, north)) tile = FindTile(east, north);
        if (!tile) {
            // At sunrise or sunset the projected hull can lie beyond the rendered region.
            projected.clear();
            return;
        }
        const auto y = tile->Height(east, north) + 0.025;
        projected.push_back({{float(east), float(y), float(north)}, {0, 1, 0}, {0, 0}});
    }
}

SceneFrame RunwayTerrain::Frame() const
{
    const auto earth = ObjectFrame(earth_);
    return {earth.ToGlobal(local_.origin),
        {earth.Rotate(local_.axes[0]), earth.Rotate(local_.axes[1]), earth.Rotate(local_.axes[2])}};
}

} // namespace orbiter::vulkan
