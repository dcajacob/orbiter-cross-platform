// Licensed under the MIT License
#include "RunwayTerrain.h"
#include "ZTreeMgr.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace orbiter::vulkan {
namespace {

constexpr double pi = 3.14159265358979323846;
constexpr int groundLevel = 19;
constexpr int tileCount = 3;
constexpr int tileResolution = 64;
constexpr int gridSize = tileCount * tileResolution + 1;
constexpr double tileAngle = pi / (1 << (groundLevel - 4));

struct Heightfield {
    std::vector<double> heights;
    double xStart = 0;
    double zStart = 0;
    double xStep = 0;
    double zStep = 0;

    double Height(int row, int column) const { return heights[row * gridSize + column]; }

    double Sample(double x, double z) const
    {
        const auto gx = std::clamp((x - xStart) / xStep, 0.0, double(gridSize - 1));
        const auto gz = std::clamp((zStart - z) / zStep, 0.0, double(gridSize - 1));
        const auto col = std::min(int(gx), gridSize - 2);
        const auto row = std::min(int(gz), gridSize - 2);
        const auto u = gx - col;
        const auto v = gz - row;
        // Match the terrain triangles' diagonal so the shadow rests on the
        // rendered surface rather than on a separately interpolated surface.
        if (u + v <= 1)
            return (1 - u - v) * Height(row, col) + u * Height(row, col + 1) + v * Height(row + 1, col);
        return (u + v - 1) * Height(row + 1, col + 1) +
            (1 - u) * Height(row + 1, col) + (1 - v) * Height(row, col + 1);
    }
};

struct TileTexture {
    TextureData image;
    float u = 0;
    float v = 0;
    float scale = 1;
};

TileTexture LoadTile(ZTreeMgr& archive, const std::filesystem::path& filename, int row, int col)
{
    for (int level = groundLevel, stride = 1; level >= 4; --level, stride *= 2) {
        unsigned char* raw = nullptr;
        const auto size = archive.ReadData(level, row / stride, col / stride, &raw);
        const auto release = [&archive](unsigned char* ptr) { archive.ReleaseData(ptr); };
        const std::unique_ptr<unsigned char, decltype(release)> data(raw, release);
        if (!size) continue;
        const auto label = filename.string() + " [" + std::to_string(level) + "/" +
            std::to_string(row / stride) + "/" + std::to_string(col / stride) + "]";
        return {DecodeDds(std::vector<std::uint8_t>(raw, raw + size), label), float(col % stride) / stride,
            float(row % stride) / stride, 1.0f / stride};
    }
    throw std::runtime_error("Stock Earth surface tile has no usable ancestor");
}

void AppendTile(SceneMesh& mesh, Heightfield const& terrain, int row, int column, const TileTexture& tile, unsigned texture)
{
    const auto firstVertex = unsigned(mesh.vertices.size());
    const auto firstIndex = unsigned(mesh.indices.size());
    for (int y = 0; y <= tileResolution; ++y) {
        const auto r = row * tileResolution + y;
        for (int x = 0; x <= tileResolution; ++x) {
            const auto c = column * tileResolution + x;
            const auto xWorld = terrain.xStart + c * terrain.xStep;
            const auto zWorld = terrain.zStart - r * terrain.zStep;
            mesh.vertices.push_back({{float(xWorld), float(terrain.Height(r, c)), float(zWorld)},
                {0, 1, 0}, {tile.u + tile.scale * x / tileResolution, tile.v + tile.scale * y / tileResolution}});
        }
    }
    for (unsigned y = 0; y < tileResolution; ++y) {
        for (unsigned x = 0; x < tileResolution; ++x) {
            const auto top = firstVertex + y * (tileResolution + 1) + x;
            const auto lower = top + tileResolution + 1;
            mesh.indices.insert(mesh.indices.end(), {top, top + 1, lower, top + 1, lower + 1, lower});
        }
    }
    MaterialUniform material;
    mesh.groups.push_back({firstIndex, unsigned(mesh.indices.size()) - firstIndex, texture, material, DrawPass::Terrain});
}

void AppendShadow(SceneMesh& mesh, const Heightfield& terrain, const SceneFrame& ground, const SceneFrame& ship,
    std::size_t shipVertices, std::size_t shipIndices)
{
    const auto sun = Subtract(ground.ToLocal(SunPosition()), ground.ToLocal(ship.origin));
    if (sun.y <= 0) return;

    const auto firstVertex = unsigned(mesh.vertices.size());
    const auto firstIndex = unsigned(mesh.indices.size());
    for (std::size_t i = 0; i < shipVertices; ++i) {
        const auto& vertex = mesh.vertices[i];
        const auto p = ground.ToLocal(ship.ToGlobal({vertex.position[0], vertex.position[1], vertex.position[2]}));
        // Intersect the light ray with the piecewise planar heightfield.
        // The runway is almost flat and three refinements converge here.
        double distance = 0;
        for (int step = 0; step < 3; ++step) {
            const auto y = terrain.Sample(p.x - distance * sun.x, p.z - distance * sun.z);
            distance = std::max(0.0, (p.y - y) / sun.y);
        }
        const auto x = p.x - distance * sun.x;
        const auto z = p.z - distance * sun.z;
        constexpr double depthClearance = 0.025;
        mesh.vertices.push_back({{float(x), float(terrain.Sample(x, z) + depthClearance), float(z)}, {0, 1, 0}, {0, 0}});
    }
    for (std::size_t i = 0; i < shipIndices; ++i)
        mesh.indices.push_back(firstVertex + mesh.indices[i]);
    MaterialUniform shade;
    shade.diffuse[0] = shade.diffuse[1] = shade.diffuse[2] = 0.015f;
    shade.diffuse[3] = 0.63f;
    mesh.groups.push_back({firstIndex, unsigned(shipIndices), 0, shade, DrawPass::Shadow});
}

} // namespace

void RunwayTerrain::Append(const std::filesystem::path& filename, const SceneFrame& ship, SceneMesh& mesh)
{
    char name[] = "Earth";
    earth_ = oapiGetGbodyByName(name);
    if (!earth_) throw std::runtime_error("Stock Runway 33 terrain requires Earth");

    const auto shipVertices = mesh.vertices.size();
    const auto shipIndices = mesh.indices.size();
    auto archive = ZTreeMgr::OpenArchiveFile(filename, ZTreeMgr::LAYER_SURF);
    if (!archive) throw std::runtime_error("Cannot open stock Earth surface archive: " + filename.string());
    textures_.clear();
    double longitude, latitude, distance;
    oapiGlobalToEqu(earth_, ship.origin, &longitude, &latitude, &distance);

    const auto radius = oapiGetSize(earth_);
    const auto altitude = oapiSurfaceElevation(earth_, longitude, latitude);
    const auto slat = std::sin(latitude);
    const auto clat = std::cos(latitude);
    const auto slng = std::sin(longitude);
    const auto clng = std::cos(longitude);
    local_.axes = {{{-slng, 0, clng}, {clat * clng, slat, clat * slng}, {-slat * clng, clat, -slat * slng}}};
    local_.origin = Scale(local_.axes[1], radius + altitude);

    constexpr auto rows = 1 << (groundLevel - 4);
    const auto topRow = std::clamp(int((pi / 2 - latitude) / tileAngle) - 1, 0, rows - tileCount);
    const auto leftColumn = int((pi + longitude) / tileAngle) - 1;
    const auto leftLongitude = leftColumn * tileAngle - pi;
    const auto topLatitude = pi / 2 - topRow * tileAngle;
    const auto sampleAngle = tileAngle / tileResolution;
    Heightfield terrain;
    terrain.heights.reserve(gridSize * gridSize);
    terrain.xStart = (leftLongitude - longitude) * radius * clat;
    terrain.zStart = (topLatitude - latitude) * radius;
    terrain.xStep = sampleAngle * radius * clat;
    terrain.zStep = sampleAngle * radius;

    for (int row = 0; row < gridSize; ++row) {
        const auto lat = topLatitude - row * sampleAngle;
        const auto z = terrain.zStart - row * terrain.zStep;
        for (int col = 0; col < gridSize; ++col) {
            const auto lng = std::remainder(leftLongitude + col * sampleAngle, 2 * pi);
            const auto x = terrain.xStart + col * terrain.xStep;
            const auto curvature = (x * x + z * z) / (2 * radius);
            terrain.heights.push_back(oapiSurfaceElevation(earth_, lng, lat) - altitude - curvature);
        }
    }

    for (int y = 0; y < tileCount; ++y) {
        for (int x = 0; x < tileCount; ++x) {
            const auto col = (leftColumn + x + 2 * rows) % (2 * rows);
            auto tile = LoadTile(*archive, filename, topRow + y, col);
            const auto texture = unsigned(mesh.textures.size());
            AppendTile(mesh, terrain, y, x, tile, texture);
            textures_.push_back(std::move(tile.image));
            mesh.textures.push_back(&textures_.back());
        }
    }
    AppendShadow(mesh, terrain, Frame(), ship, shipVertices, shipIndices);
    std::clog << "Runway33 stock Earth terrain: " << tileCount * tileCount << " tiles at level " << groundLevel
              << " with Orbiter elevation samples; projected DG-S shadow\n";
}

SceneFrame RunwayTerrain::Frame() const
{
    const auto earth = ObjectFrame(earth_);
    return {earth.ToGlobal(local_.origin),
        {earth.Rotate(local_.axes[0]), earth.Rotate(local_.axes[1]), earth.Rotate(local_.axes[2])}};
}

} // namespace orbiter::vulkan
