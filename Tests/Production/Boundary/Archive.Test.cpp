// Licensed under the MIT License
#include "ZTreeMgr.h"
#include <array>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
void require(bool condition,const char* message) {if (!condition) throw std::runtime_error(message);}
int main(int argc,char** argv)
{
    try {
        require(argc==3,"Expected archive directory and test mode");
        const std::string mode=argv[2];
        ZTreeMgr archive(argv[1],ZTreeMgr::LAYER_SURF);
        const auto path=std::filesystem::path(argv[1])/"Archive"/"Surf.tree";
        if (mode=="closed") {
            require(!archive.TOC().size() && !archive.Error().empty(),"Invalid archive accepted without error");
            std::unique_ptr<ZTreeMgr> factory(ZTreeMgr::CreateFromFile(argv[1],ZTreeMgr::LAYER_SURF));
            require(!factory,"Invalid archive factory succeeded");
            bool rejected=false;try {ZTreeMgr::OpenArchiveFile(path,ZTreeMgr::LAYER_SURF);}catch(const std::runtime_error&){rejected=true;}
            require(rejected,"Required invalid archive did not fail explicitly");
            if (std::filesystem::exists(path)) require(std::filesystem::remove(path),"Invalid archive handle leaked");
        } else if (mode=="corrupt" || mode=="truncated") {
            require(archive.TOC().size()>0,"Corruption fixture header did not open");
            auto index=std::uint32_t(0);
            if (mode=="truncated") {index=archive.TOC().size()-1;std::filesystem::resize_file(path,48+32*archive.TOC().size());}
            unsigned char* output=reinterpret_cast<unsigned char*>(1);
            require(!archive.ReadData(index,&output) && !output && !archive.Error().empty(),"Corrupt payload returned success/stale memory");
        } else if (mode=="valid") {
            require(archive.TOC().size()==9 && archive.Error().empty(),"Valid archive did not open");
            auto direct=ZTreeMgr::OpenArchiveFile(path,ZTreeMgr::LAYER_SURF);
            require(direct->TOC().size()==archive.TOC().size() && direct->Idx(5,1,1)==archive.Idx(5,1,1),
                "Explicit indexed archive opening changed quadtree mapping");
            for (const auto& q : {std::array<int,3>{0,0,0},{-1,0,0},{35,0,0},{4,-1,0},{4,0,-1},{4,1,0},{4,0,2},{1,0,1},{5,2,0},{5,0,4}})
                require(archive.Idx(q[0],q[1],q[2])==UINT32_MAX,"Invalid coordinate succeeded");
            require(archive.Idx(5,0,0)==5 && archive.Idx(5,0,1)==6 && archive.Idx(5,1,0)==7 && archive.Idx(5,1,1)==8,"Child quadrant ordering changed");
            for (auto index : {UINT32_MAX,archive.TOC().size(),std::uint32_t(3)}) {
                unsigned char* output=reinterpret_cast<unsigned char*>(1);
                require(!archive.ReadData(index,&output) && !output,"Missing tile returned stale memory");
            }
            require(!archive.ReadData(0,nullptr) && !archive.Error().empty(),"Missing output pointer accepted");
            for (unsigned i=0;i<20;++i) {
                std::unique_ptr<ZTreeMgr> loaded(ZTreeMgr::CreateFromFile(argv[1],ZTreeMgr::LAYER_SURF));
                require(bool(loaded),"Repeated load failed");
                unsigned char* output=nullptr;
                require(loaded->ReadData(0,&output)==8196 && !std::memcmp(output,"DDS ",4),"Repeated decode failed");
                loaded->ReleaseData(output);
            }
            auto close=[](std::FILE* file){std::fclose(file);};
            std::unique_ptr<std::FILE,decltype(close)> file(std::tmpfile(),close);
            require(bool(file),"Cannot create header test");TreeFileHeader header;
            require(header.fwrite(file.get())==1 && std::ftell(file.get())==48,"Header write depends on struct layout");
            std::rewind(file.get());TreeFileHeader restored;
            require(restored.fread(file.get()),"Explicit header round trip failed");
        } else throw std::runtime_error("Unknown archive test mode");
        return 0;
    } catch (const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
