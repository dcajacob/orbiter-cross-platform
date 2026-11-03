// Compile the actual production heading-tape method against CPU mesh storage.
// Full scenario rendering remains a separate test of its engine integration.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>
using std::ceil;
using std::fabs;
using std::floor;
struct Vertex {float x=0,y=0,tu=0,tv=0;};
struct GroupSpec {std::vector<Vertex> Vtx;std::vector<std::uint16_t> Idx;};
struct HUD {
    struct {double scal=1.25;} renderprm;
    double HRES05=640,hudtexw=512,hudtexh=256;
    GroupSpec mesh;
    GroupSpec* EnsureMeshBuffer(int group,int vertices,int indices) {
        if(group!=0)throw std::runtime_error("Unexpected HUD group");
        mesh.Vtx.resize(vertices);mesh.Idx.resize(indices);return &mesh;
    }
    void AddMesh_HeadingTape(int&,int&,double,bool,double);
};
// HUD_METHOD
int main()
{
    try {
        for(const auto heading:{0.,10.,120.,350.})for(const auto offset:{-90.,-30.,0.,30.,90.,340.}) {
            HUD hud;
            hud.mesh.Vtx.resize(4);hud.mesh.Idx.resize(6);
            hud.mesh.Vtx[0].x=-1234;
            int vertices=4,indices=6;
            hud.AddMesh_HeadingTape(vertices,indices,heading,true,heading+offset);
            if(vertices!=40 || indices!=60 || hud.mesh.Vtx[0].x!=-1234)
                throw std::runtime_error("Heading marker count/append ownership differs");
            for(int i=6;i<indices;++i)if(hud.mesh.Idx[i]<4 || hud.mesh.Idx[i]>=vertices)
                throw std::runtime_error("HUD index points outside appended vertices");
            double wrapped=offset;
            while(std::abs(wrapped)>180)wrapped+=wrapped>0 ? -360 : 360;
            const double expected=640+(wrapped>30 ? 332.5 : wrapped< -30 ? -332.5 : wrapped*(312.5/30));
            const double center=(hud.mesh.Vtx[36].x+hud.mesh.Vtx[38].x)*.5;
            if(std::abs(center-expected)>1e-4)throw std::runtime_error("Heading marker direction/position differs");
            for(int i=4;i<vertices;++i) {
                const auto& v=hud.mesh.Vtx[i];
                if(!std::isfinite(v.x) || !std::isfinite(v.y) || v.tu<0 || v.tu>1 || v.tv<0 || v.tv>1)
                    throw std::runtime_error("Invalid heading vertex or atlas coordinate");
            }
        }
        HUD hud;int vertices=0,indices=0;
        hud.AddMesh_HeadingTape(vertices,indices,0,false,0);
        if(vertices!=32 || indices!=48)throw std::runtime_error("Disabled heading marker was appended");
        std::puts("24 heading marker cases: left/right/inside, wrap, bounds and disabled marker passed");
        return 0;
    }catch(const std::exception& error){std::fprintf(stderr,"%s\n",error.what());return 1;}
}
