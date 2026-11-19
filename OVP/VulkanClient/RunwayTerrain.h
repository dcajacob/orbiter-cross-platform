// Licensed under the MIT License
#pragma once

#include "SceneFrame.h"
#include "VulkanScene.h"

#include <memory>
#include <deque>

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
    void Close();
    bool NeedsReanchor(const VECTOR3& position) const;
    TerrainUpdate Update(const VECTOR3& position, Scene&);
    size_t VisibleCount() const { return visible_.size(); }
    size_t DetailCount() const;
    SceneFrame Frame() const;
    VECTOR3 DrapeSurfaceTile(const VECTOR3& local) const;
    VECTOR3 BasePosition(double longitude, double latitude) const;
    SceneFrame BaseFrame(double longitude, double latitude) const;
    void ProjectShadow(const SceneFrame& ground, const SceneFrame& ship, const std::vector<Vertex>&,
        std::vector<Vertex>& projected) const;

private:
    struct Tile {
        std::vector<double> heights;
        int divisions = 0;
        bool regionalImagery = false;
        double x = 0, z = 0, width = 0, length = 0;

        bool Contains(double east, double north) const;
        double Height(double east, double north) const;
    };

    Tile BuildTile(const TileKey&, TerrainMesh&);
    void CollectVisible(const TileKey&, std::set<TileKey>&) const;
    void RetainTiles(Scene&);
    std::array<double, 2> GridPosition(double east, double height, double north) const;
    const Tile* FindTile(double east, double north) const;
    OBJHANDLE earth_ = nullptr;
    SceneFrame local_{};
    double longitude_ = 0, latitude_ = 0, radius_ = 0, altitude_ = 0, eastScale_ = 0;
    TileKey requested_{0, 0, 0};
    std::filesystem::path filename_;
    std::filesystem::path imagery_;
    std::unique_ptr<ZTreeMgr> archive_;
    std::vector<ElevationTile>* elevationCache_ = nullptr;
    std::map<TileKey, Tile> tiles_;
    std::set<TileKey> visible_, wanted_;
    std::vector<TileKey> roots_;
    std::deque<TileKey> pending_;
};

} // namespace orbiter::vulkan
