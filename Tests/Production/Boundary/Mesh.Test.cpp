// Licensed under the MIT License
#include "Mesh.h"
#include "Production/ResourceResolver.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace orbiter::production;
void require(bool value,const char* message) { if (!value) throw std::runtime_error(message); }
struct Environment {
    ResourceResolver files;
    int allocations=0,releases=0;
    std::vector<std::string> textures;
    int textureToken=1;
    explicit Environment(const std::filesystem::path& root) : files(root) {}
    MeshServices services()
    {
        MeshServices result;
        result.context=this;
        result.path=[](void* c,const char* name) {
            return static_cast<Environment*>(c)->files.Resolve(std::string(name)+".msh");
        };
        result.loadTexture=[](void* c,const char* name,UInt32 flags)->MeshSurface {
            require(flags==8 || flags==10,"Texture acquisition flags changed");
            static_cast<Environment*>(c)->textures.emplace_back(name);
            return nullptr; // explicitly headless: retain declarations, allocate no GPU resource
        };
        result.releaseTexture=[](void* c,MeshSurface handle) {
            auto& env=*static_cast<Environment*>(c);
            require(handle==&env.textureToken,"Wrong opaque host resource released"); ++env.releases;
        };
        result.error=[](void*,const char* message) { throw std::runtime_error(message); };
        result.allocation=[](void* c,const char*,int) { ++static_cast<Environment*>(c)->allocations; };
        return result;
    }
};
int main(int argc,char** argv)
{
    try {
        require(argc==2,"Expected stock mesh root");
        Environment env(argv[1]);
        struct Binding {
            MeshServices previous;
            explicit Binding(MeshServices s) : previous(BindMeshServices(s)) {}
            ~Binding() { BindMeshServices(previous); }
        } binding(env.services());
        {
            MeshManager manager;
            bool first=false;
            const Mesh* original=manager.LoadMesh("ShuttlePB",&first);
            require(first && original && original->nGroup()==7 && original->nMaterial()==2 && original->nTexture()==2,
                "Actual production mesh did not load stock ShuttlePB");
            require(manager.LoadMesh("ShuttlePB",&first)==original && !first,"Production mesh cache changed identity");
            require(env.textures.size()==2 && env.textures[0]=="shuttlepb.dds" && env.textures[1]=="shuttlepbwing.dds",
                "Production texture resource requests changed");
            require(original->TextureSources().size()==2 && original->TextureSources()[0].name=="shuttlepb.dds",
                "CPU texture source metadata missing");
            Mesh copy(*original);
            auto* group=copy.GetGroup(0);
            const float x=group->Vtx[0].x;
            copy.TranslateGroup(0,2,4,8);
            require(group->Vtx[0].x==x+2 && const_cast<Mesh*>(original)->GetGroup(0)->Vtx[0].x==x,
                "Production mesh copy did not own its geometry");
            require(copy.GetMaterial(0)->diffuse.r==.9f,
                "SDK material values changed");
            bool rejected=false;
            try { manager.LoadMesh("MissingRequiredAsset"); } catch (const std::exception&) { rejected=true; }
            require(rejected,"Missing production mesh was silently replaced");
        }
        {
            // A partial group followed by truncated input must never enter the
            // production cache. Exercise its real error callback and ownership.
            auto services=env.services();
            const auto corrupt=std::filesystem::temp_directory_path()/"orbiter-boundary-corrupt.msh";
            struct Cleanup { std::filesystem::path file; ~Cleanup() { std::error_code ec;std::filesystem::remove(file,ec); } } cleanup{corrupt};
            std::ofstream(corrupt)<<"MSHX1\nGROUPS 2\nNONORMAL\nGEOM 3 1\n0 0 0\n1 0 0\n0 1 0\n0 1 2\nGEOM 3 1\n0 0 0\n";
            services.path=[](void*,const char*) { return std::filesystem::temp_directory_path()/"orbiter-boundary-corrupt.msh"; };
            Binding invalid(services);
            MeshManager manager;
            bool rejected=false;
            try { manager.LoadMesh("Corrupt"); } catch (const std::exception&) { rejected=true; }
            require(rejected,"Truncated geometry entered the production mesh cache");
        }
        {
            auto* v=new NTVERTEX[3]{{0,0,0,0,0,1,0,0},{1,0,0,0,0,1,1,0},{0,1,0,0,0,1,0,1}};
            auto* indices=new UInt16[3]{0,1,2};
            Mesh mesh(v,3,indices,3);
            require(mesh.GetFlags()==0,"Mesh flags are not initialized");
            MATERIAL material{}; material.diffuse={.25f,.5f,.75f,1};material.power=7;
            require(mesh.AddMaterial(material)==0 && mesh.GetMaterial(0)->power==7,"SDK material storage changed");
            material.power=2;require(mesh.GetMaterial(0)->power==7,"Material data aliases its caller");
            MeshGroupEdit edit{};NTVERTEX delta{};delta.x=.5f;UInt16 selected=1;
            edit.flags=MeshEdit::VTXCRDADDX|MeshEdit::SETUSERFLAG;edit.UsrFlag=0x80000001u;
            edit.Vtx=&delta;edit.nVtx=1;edit.vIdx=&selected;
            require(mesh.EditGroup(0,&edit)==0 && mesh.GetGroup(0)->Vtx[1].x==1.5f && mesh.GetGroup(0)->UsrFlag==0x80000001u,
                "Indexed mesh editing changed");
            NTVERTEX out[2]{};UInt16 permutation[2]{1,99};MeshGroupRequest request{};
            request.nVtx=2;request.Vtx=out;request.VtxPerm=permutation;
            require(mesh.GetGroup(0,&request)==1 && out[0].x==1.5f && out[1].x==0,"Mesh request bounds behavior changed");
            const MeshTransform4 transform{2,0,0,0,0,2,0,0,0,0,2,0,1,2,3,1};
            mesh.Transform(transform);
            require(mesh.GetGroup(0)->Vtx[1].x==4 && mesh.GetGroup(0)->Vtx[1].y==2 && mesh.GetGroup(0)->Vtx[1].nz==1,
                "Production mesh transform or normals changed");
            mesh.AddTexture(&env.textureToken);
        }
        {
            // Empty panel groups own zero-length arrays too. Replacing those
            // buffers must release them, including empty-to-empty appends.
            const NTVERTEX vertices[3]{{0,0,0,0,0,1,0,0},{1,0,0,0,0,1,1,0},{0,1,0,0,0,1,0,1}};
            const UInt16 indices[3]{0,1,2};
            for(unsigned pass=0;pass<4;++pass) {
                Mesh mesh;
                const auto group=mesh.AddGroup(nullptr,0,nullptr,0,0,0,0,0,true);
                for(unsigned repeat=0;repeat<3;++repeat)
                    require(mesh.AddGroupBlock(group,nullptr,0,nullptr,0),"Empty group append failed");
                require(mesh.AddGroupBlock(group,vertices,3,indices,3) &&
                        mesh.AddGroupBlock(group,vertices,3,indices,3),"Panel geometry append failed");
                const auto* got=mesh.GetGroup(group);
                require(got->nVtx==6 && got->nIdx==6,"Panel geometry counts changed");
                for(unsigned i=0;i<6;++i) {
                    require(got->Idx[i]==i,"Panel index offsets changed");
                    require(got->Vtx[i].x==vertices[i%3].x && got->Vtx[i].y==vertices[i%3].y &&
                            got->Vtx[i].z==vertices[i%3].z && got->Vtx[i].nz==1,
                            "Panel vertices changed while replacing owned arrays");
                }
            }
        }
        require(env.releases==1 && env.allocations>0,"Host resource lifetime callbacks were not routed");
        std::cout<<"Original production Mesh: stock data, copies, edits, transforms, materials, cache and host resources passed\n";
        return 0;
    } catch (const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
