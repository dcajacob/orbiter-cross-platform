// Licensed under the MIT License
#pragma once

#include "SceneFrame.h"
#include "VulkanScene.h"

#include <memory>

class ZTreeMgr;

namespace orbiter::vulkan {

class RunwayTerrain {
public:
    RunwayTerrain();
    ~RunwayTerrain();
    void Open(const std::filesystem::path& archive, const VECTOR3& origin);
    void Close();
    bool Update(const VECTOR3& position, Scene&);
    SceneFrame Frame() const;
    void ProjectShadow(const SceneFrame& ground, const SceneFrame& ship, const std::vector<Vertex>&,
        std::vector<Vertex>& projected) const;

private:
    struct Tile {
        std::vector<double> heights;
        int divisions = 0;
        double x = 0, z = 0, width = 0, length = 0;

        bool Contains(double east, double north) const;
        double Height(double east, double north) const;
    };

    Tile BuildTile(const TileKey&, TerrainMesh&);
    void RetainTiles(Scene&);
    const Tile* FindTile(double east, double north) const;
    OBJHANDLE earth_ = nullptr;
    SceneFrame local_{};
    double longitude_ = 0, latitude_ = 0, radius_ = 0, altitude_ = 0, eastScale_ = 0;
    TileKey requested_{0, 0, 0};
    std::filesystem::path filename_;
    std::unique_ptr<ZTreeMgr> archive_;
    std::map<TileKey, Tile> tiles_;
    std::set<TileKey> visible_, wanted_;
    std::vector<TileKey> pending_;
    unsigned loaded_ = 0;
    bool switching_ = false;
};

} // namespace orbiter::vulkan
