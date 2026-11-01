// Licensed under the MIT License
// Read-only queries of the original production world's elevation manager.
#include "Orbitersdk.h"
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <locale>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct Point { double longitude, latitude; };
class Observer final : public oapi::Module {
public:
    explicit Observer(HINSTANCE instance):oapi::Module(instance) {}
    void clbkSimulationStart(RenderMode) override {
        try {
            std::ifstream input("elevation-points.csv");input.imbue(std::locale::classic());
            std::string header;std::getline(input,header);
            if (header != "longitude_deg,latitude_deg") throw std::runtime_error("Elevation query header differs");
            std::vector<Point> points;Point point;char comma;
            while (input >> point.longitude >> comma >> point.latitude) {
                if (comma != ',' || !std::isfinite(point.longitude) || !std::isfinite(point.latitude))
                    throw std::runtime_error("Invalid elevation query");
                points.push_back(point);
            }
            if (!input.eof() || points.size()!=85) throw std::runtime_error("Incomplete elevation query list");
            int mode=0;std::ifstream settings("elevation-mode.txt");settings >> mode;
            if (mode!=1 && mode!=2) throw std::runtime_error("Invalid elevation mode label");
            std::ofstream output("elevation.csv",std::ios::binary);
            output.imbue(std::locale::classic());output.exceptions(std::ios::badbit|std::ios::failbit);
            output << std::setprecision(17)
                << "mode,body,requested_level,cache,index,longitude_deg,latitude_deg,elevation_m,nx,ny,nz,loaded_level\n";
            for (const char* name:{"Earth","Moon","Mars"}) {
                const auto body=oapiGetGbodyByName(const_cast<char*>(name));
                if (!body || oapiGetObjectType(body)!=OBJTP_PLANET)
                    throw std::runtime_error("Required production planet is missing");
                for (int external:{0,1}) {
                    auto release=[](std::vector<ElevationTile>* cache) { if (cache) ReleaseTileCache(cache); };
                    std::unique_ptr<std::vector<ElevationTile>,decltype(release)> cache(external ? InitTileCache(8) : nullptr,release);
                    if (external && !cache) throw std::runtime_error("Elevation cache allocation failed");
                    for (int requested:{8,12,16,0}) for (std::size_t i=0;i<points.size();++i) {
                        const auto& p=points[i];VECTOR3 normal={0,0,0};int level=-1;
                        const double elevation=oapiSurfaceElevationEx(body,p.longitude*RAD,p.latitude*RAD,
                            requested,cache.get(),&normal,&level);
                        if (!std::isfinite(elevation) || !std::isfinite(normal.x) ||
                            !std::isfinite(normal.y) || !std::isfinite(normal.z))
                            throw std::runtime_error("Nonfinite original terrain observation");
                        output << mode << ',' << name << ',' << requested << ',' << external << ',' << i << ','
                            << p.longitude << ',' << p.latitude << ',' << elevation << ','
                            << normal.x << ',' << normal.y << ',' << normal.z << ',' << level << '\n';
                    }
                }
            }
            output.close();
        } catch (const std::exception& error) {
            oapiWriteLog(const_cast<char*>(error.what()));std::exit(1);
        }
    }
};
Observer* observer=nullptr;
}
DLLCLBK void InitModule(HINSTANCE instance) {observer=new Observer(instance);oapiRegisterModule(observer);}
DLLCLBK void ExitModule(HINSTANCE) {delete observer;observer=nullptr;}
