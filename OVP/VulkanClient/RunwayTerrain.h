// Licensed under the MIT License
#pragma once

#include "SceneFrame.h"
#include "VulkanScene.h"

#include <memory>
#include <deque>
#include <optional>

class ZTreeMgr;
struct ElevationTile;

namespace orbiter::vulkan {

struct TerrainUpdate {
    unsigned staged = 0;
    unsigned imagery = 0;
    bool switched = false;
    bool recentered = false;
};

class RunwayTerrain {
public:
    RunwayTerrain();
    ~RunwayTerrain();
    void Open(const std::filesystem::path& archive, const VECTOR3& origin);
    void Reanchor(const VECTOR3& origin);
    void Close();
    bool NeedsReanchor(const VECTOR3& position) const;
    TerrainUpdate Update(const EarthView& view, unsigned height, Scene&);
    EarthView View(unsigned width, unsigned height) const;
    size_t VisibleCount() const { return visible_.size(); }
    size_t DetailCount() const;
    double LeafArea() const;
    SceneFrame Frame() const;
    VECTOR3 DrapeSurfaceTile(const VECTOR3& local) const;
    VECTOR3 BasePosition(double longitude, double latitude) const;
    SceneFrame BaseFrame(double longitude, double latitude) const;
    void ProjectShadow(const SceneFrame& ground, const SceneFrame& ship, const std::vector<Vertex>&,
        std::vector<Vertex>& projected) const;

private:
    struct Tile {
        TileKey key{};
        VECTOR3 origin{};
        std::vector<std::array<float, 3>> points;
        int divisions = 0;
        bool regionalImagery = false;

        double Height(double lng, double lat, const SceneFrame& ground) const;
    };

    struct Job {
        TileKey key;
        Tile tile;
        std::vector<double> elevations;
        double west, north, angle, radius;
    };
    struct Prepared {
        TileKey key;
        Tile tile;
        TerrainMesh mesh;
    };
    class Loader;
    Job StartTile(const TileKey&) const;
    void SampleRow(Job&);
    static Prepared BuildTile(Job, ZTreeMgr&, const std::filesystem::path&, const std::filesystem::path&);
    void CollectVisible(const TileKey&, std::set<TileKey>&) const;
    void RetainTiles(Scene&);
    const Tile* FindTile(double lng, double lat) const;
    OBJHANDLE earth_ = nullptr;
    SceneFrame local_{};
    double longitude_ = 0, latitude_ = 0, radius_ = 0, altitude_ = 0;
    TileKey requested_{0, 0, 0};
    std::filesystem::path filename_;
    std::filesystem::path imagery_;
    std::unique_ptr<ZTreeMgr> archive_;
    std::vector<ElevationTile>* elevationCache_ = nullptr;
    std::map<TileKey, Tile> tiles_;
    std::set<TileKey> visible_, wanted_;
    const std::array<TileKey, 2> roots_{{{4, 0, 0}, {4, 0, 1}}};
    double selectedAltitude_ = -1, selectedFocal_ = 0;
    std::deque<TileKey> pending_;
    std::optional<Job> sampling_;
    std::unique_ptr<Loader> loader_;
};

} // namespace orbiter::vulkan
