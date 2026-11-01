// Licensed under the MIT License
// Observation only: call the unchanged production archive reader. No renderer.
#include "ZTreeMgr.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <vector>

static void write(std::ostream& out, std::uint64_t value, unsigned bytes=4)
{
    for (unsigned i=0;i<bytes;++i) out.put(static_cast<char>((value>>(8*i))&255));
}
int main(int argc,char** argv)
{
    try {
        if (argc!=4) throw std::runtime_error("Expected planet directory, layer number and output path");
        const std::string layerText=argv[2];
        if (layerText.size()!=1 || layerText[0]<'0' || layerText[0]>'5') throw std::runtime_error("Invalid layer");
        std::unique_ptr<ZTreeMgr> archive(ZTreeMgr::CreateFromFile(argv[1],static_cast<ZTreeMgr::Layer>(layerText[0]-'0')));
        if (!archive) throw std::runtime_error("Production archive did not open");
        std::ofstream out(argv[3],std::ios::binary);
        if (!out) throw std::runtime_error("Cannot write observation");
        out.write("OTREE1\r\n",8);
        const auto count=archive->TOC().size();
        write(out,count);
        for (std::uint32_t i=0;i<count;++i) {
            const auto& node=archive->TOC()[i];
            write(out,static_cast<std::uint64_t>(node.pos),8);write(out,node.size);
            for (unsigned c=0;c<4;++c) write(out,node.child[c]);
        }
        struct Query {int level,lat,lng;};
        std::vector<Query> queries{{1,0,0},{2,0,0},{3,0,0},{4,0,0},{4,0,1}};
        for (int level=5;level<=12;++level) {
            const int nlat=1<<(level-4);
            for (int lat : {0,nlat-1}) for (int lng : {0,2*nlat-1}) queries.push_back({level,lat,lng});
        }
        for (auto i : {std::uint32_t(0),std::uint32_t(count/2),std::uint32_t(count-1)})
            queries.push_back({0,static_cast<int>(i),0});
        write(out,queries.size());
        for (const auto& q:queries) {
            const auto index=q.level ? archive->Idx(q.level,q.lat,q.lng) : static_cast<std::uint32_t>(q.lat);
            const auto deflated=index==std::numeric_limits<std::uint32_t>::max() ? 0 : archive->NodeSizeDeflated(index);
            const auto inflated=index==std::numeric_limits<std::uint32_t>::max() ? 0 : archive->NodeSizeInflated(index);
            unsigned char* data=nullptr;
            const auto actual=archive->ReadData(index,&data);
            std::unique_ptr<unsigned char[]> storage(data);
            if (actual!=inflated || (actual && !data)) throw std::runtime_error("Production tile decode failed");
            for (auto value : {static_cast<std::uint32_t>(q.level),static_cast<std::uint32_t>(q.lat),
                static_cast<std::uint32_t>(q.lng),static_cast<std::uint32_t>(index),static_cast<std::uint32_t>(deflated),
                static_cast<std::uint32_t>(inflated),static_cast<std::uint32_t>(actual)}) write(out,value);
            if (actual) out.write(reinterpret_cast<const char*>(data),actual);
        }
        out.close();
        if (!out) throw std::runtime_error("Observation write failed");
        std::cout<<"Observed "<<count<<" production nodes and "<<queries.size()<<" tile queries\n";
        return 0;
    } catch (const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
