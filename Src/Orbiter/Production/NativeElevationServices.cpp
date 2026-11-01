// Licensed under the MIT License
#include "NativeElevationServices.h"
#include "Celbody.h"
#include "TimeData.h"
#include "ZTreeMgr.h"
#include <cstdio>
#include <stdexcept>
#include <utility>
namespace orbiter::production {
NativeElevationServices::NativeElevationServices(const ResourceResolver& index,const TimeData& clock,SetupQuery setup,
    const std::vector<std::string>& requiredArchives):textures(index),time(clock),query(std::move(setup))
{
    if (!query) throw std::invalid_argument("Production planet elevation settings are required");
    for (const auto& name:requiredArchives) textures.Resolve(name);
}
ElevationSetup NativeElevationServices::Setup(const CelestialBody& body) const {return query(body);}
std::unique_ptr<ZTreeMgr> NativeElevationServices::OpenArchive(const CelestialBody& body,bool modified)
{
    const auto relative=std::string(body.Name())+"/Archive/"+(modified ? "Elev_mod.tree" : "Elev.tree");
    if (!textures.Contains(relative)) return {};
    return ZTreeMgr::OpenArchiveFile(textures.Resolve(relative),modified ? ZTreeMgr::LAYER_ELEVMOD : ZTreeMgr::LAYER_ELEV);
}
bool NativeElevationServices::HasLooseLayer(const CelestialBody& body,bool modified) const
{return textures.ContainsDirectory(std::string(body.Name())+(modified ? "/Elev_mod" : "/Elev"));}
std::filesystem::path NativeElevationServices::LooseTile(const CelestialBody& body,bool modified,int level,int latitude,int longitude) const
{
    char indices[96];
    const int length=std::snprintf(indices,sizeof(indices),"/%02d/%06d/%06d.elv",level,latitude,longitude);
    if (length<0 || length>=sizeof(indices)) throw std::runtime_error("Invalid production elevation tile index");
    const auto relative=std::string(body.Name())+(modified ? "/Elev_mod" : "/Elev")+indices;
    return textures.Contains(relative) ? textures.Resolve(relative) : std::filesystem::path();
}
double NativeElevationServices::SystemTime() const {return time.SysT0;}
}
