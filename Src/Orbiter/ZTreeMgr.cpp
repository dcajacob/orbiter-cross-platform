// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "ZTreeMgr.h"
#include <zlib.h>
#include <algorithm>
#include <array>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <utility>

namespace {
void require(bool condition,const char* message) {if (!condition) throw std::runtime_error(message);}
std::uint64_t integer(const unsigned char* bytes,unsigned count=4)
{
    std::uint64_t result=0;
    for (unsigned i=0;i<count;++i) result|=std::uint64_t(bytes[i])<<(i*8);
    return result;
}
void encode(unsigned char* bytes,std::uint64_t value,unsigned count=4)
{for (unsigned i=0;i<count;++i) bytes[i]=static_cast<unsigned char>(value>>(i*8));}
template<class Reader> std::vector<TreeNode> records(std::uint32_t count,Reader read)
{
    std::vector<TreeNode> result;
    std::array<unsigned char,32> bytes;
    for (std::uint32_t i=0;i<count;++i) {
        require(read(bytes.data(),bytes.size()),"Truncated planetary archive table");
        TreeNode node;
        const auto position=integer(bytes.data(),8);
        require(position<=INT64_MAX,"Negative/overflowing planetary archive node offset");
        node.pos=static_cast<std::int64_t>(position);node.size=static_cast<std::uint32_t>(integer(bytes.data()+8));
        for (unsigned child=0;child<4;++child) {
            node.child[child]=static_cast<std::uint32_t>(integer(bytes.data()+12+4*child));
            require(node.child[child]==UINT32_MAX || node.child[child]<count,"Invalid planetary archive child index");
        }
        result.push_back(node); // Four disk padding bytes need not be zero.
    }
    // Reject cycles without recursion, including disconnected corrupt nodes.
    std::vector<unsigned char> visited(count,0);
    std::vector<std::pair<std::uint32_t,unsigned>> stack;
    for (std::uint32_t i=0;i<count;++i) {
        if (visited[i]) continue;
        visited[i]=1;stack.emplace_back(i,0);
        while (!stack.empty()) {
            auto& frame=stack.back();
            if (frame.second==4) {visited[frame.first]=2;stack.pop_back();continue;}
            const auto child=result[frame.first].child[frame.second++];
            if (child==UINT32_MAX || visited[child]==2) continue;
            require(visited[child]==0,"Cycle in planetary archive child graph");
            visited[child]=1;stack.emplace_back(child,0);
        }
    }
    return result;
}
}

TreeFileHeader::TreeFileHeader():magic{'T','X',1,0},size(48),flags(0),dataOfs(48),dataLength(0),nodeCount(0),
    rootPos1(UINT32_MAX),rootPos2(UINT32_MAX),rootPos3(UINT32_MAX),rootPos4{UINT32_MAX,UINT32_MAX} {}
bool TreeFileHeader::Decode(const unsigned char* bytes)
{
    if (std::memcmp(bytes,magic,4) || integer(bytes+4)!=48 || (integer(bytes+8)&~std::uint64_t(1))) return false;
    const auto length=integer(bytes+16,8);
    if (length>INT64_MAX) return false;
    flags=static_cast<std::uint32_t>(integer(bytes+8));dataOfs=static_cast<std::uint32_t>(integer(bytes+12));
    dataLength=static_cast<std::int64_t>(length);nodeCount=static_cast<std::uint32_t>(integer(bytes+24));
    rootPos1=static_cast<std::uint32_t>(integer(bytes+28));rootPos2=static_cast<std::uint32_t>(integer(bytes+32));
    rootPos3=static_cast<std::uint32_t>(integer(bytes+36));
    for (unsigned i=0;i<2;++i) rootPos4[i]=static_cast<std::uint32_t>(integer(bytes+40+4*i));
    return true;
}
bool TreeFileHeader::Read(std::istream& stream)
{std::array<unsigned char,48> bytes;return bool(stream.read(reinterpret_cast<char*>(bytes.data()),bytes.size())) && Decode(bytes.data());}
bool TreeFileHeader::fread(std::FILE* file)
{std::array<unsigned char,48> bytes;return file && std::fread(bytes.data(),1,bytes.size(),file)==bytes.size() && Decode(bytes.data());}
std::size_t TreeFileHeader::fwrite(std::FILE* file)
{
    std::array<unsigned char,48> bytes{};
    std::copy(magic,magic+4,bytes.begin());encode(bytes.data()+4,48);encode(bytes.data()+8,flags);
    encode(bytes.data()+12,dataOfs);encode(bytes.data()+16,static_cast<std::uint64_t>(dataLength),8);
    const std::uint32_t values[]={nodeCount,rootPos1,rootPos2,rootPos3,rootPos4[0],rootPos4[1]};
    for (unsigned i=0;i<6;++i) encode(bytes.data()+24+4*i,values[i]);
    return file && std::fwrite(bytes.data(),bytes.size(),1,file)==1 ? 1:0;
}
void TreeTOC::Read(std::uint32_t count,std::istream& stream)
{tree=records(count,[&](unsigned char* data,std::size_t size){return bool(stream.read(reinterpret_cast<char*>(data),size));});}
std::size_t TreeTOC::fread(std::uint32_t count,std::FILE* file)
{
    if (!file) return 0;
    try {tree=records(count,[&](unsigned char* data,std::size_t size){return std::fread(data,1,size,file)==size;});return count;}
    catch (const std::exception&) {return 0;}
}
std::uint32_t TreeTOC::NodeSizeDeflated(std::uint32_t index) const
{
    if (index>=size()) return 0;
    const auto length=(index+1<size()?tree[index+1].pos:totlength)-tree[index].pos;
    return length>=0 && std::uint64_t(length)<=UINT32_MAX?static_cast<std::uint32_t>(length):0;
}
ZTreeMgr* ZTreeMgr::CreateFromFile(const char* planetPath,Layer layer)
{auto manager=std::make_unique<ZTreeMgr>(planetPath,layer);return manager->TOC().size()?manager.release():nullptr;}
ZTreeMgr::ZTreeMgr(const char* planetPath,Layer value):path(planetPath?planetPath:""),layer(value)
{if (!planetPath || !*planetPath) error="Empty planetary archive directory";else OpenArchive();}
bool ZTreeMgr::OpenArchive()
{
    try {
        const char* names[]={"Surf","Mask","Elev","Elev_mod","Label","Cloud"};
        require(layer>=LAYER_SURF && layer<=LAYER_CLOUD,"Invalid planetary archive layer");
        treef.open(path/"Archive"/(std::string(names[layer])+".tree"),std::ios::binary);
        require(bool(treef),"Missing/unreadable planetary archive");
        treef.seekg(0,std::ios::end);
        const auto fileEnd=treef.tellg();
        require(fileEnd>=0,"Cannot measure planetary archive");
        treef.seekg(0);
        TreeFileHeader header;
        require(header.Read(treef),"Invalid/truncated/unsupported planetary archive header");
        const std::uint64_t minimum=48+std::uint64_t(header.nodeCount)*32;
        require(header.nodeCount>0 && minimum<=header.dataOfs,"Invalid planetary archive table extent");
        const auto fileSize=static_cast<std::uint64_t>(fileEnd);
        require(header.dataOfs<=fileSize && std::uint64_t(header.dataLength)<=fileSize-header.dataOfs,
            "Planetary archive data extent exceeds file");
        for (auto root : {header.rootPos1,header.rootPos2,header.rootPos3,header.rootPos4[0],header.rootPos4[1]})
            require(root==UINT32_MAX || root<header.nodeCount,"Invalid planetary archive root index");
        TreeTOC candidate;candidate.Read(header.nodeCount,treef);candidate.totlength=header.dataLength;
        for (std::uint32_t i=0;i<candidate.size();++i) {
            const auto position=candidate[i].pos;
            const auto next=i+1<candidate.size()?candidate[i+1].pos:header.dataLength;
            require(position<=next && next<=header.dataLength && std::uint64_t(next-position)<=UINT32_MAX,
                "Invalid planetary archive node extent");
            require(!candidate[i].size || next>position,"Missing compressed planetary archive node");
        }
        toc=std::move(candidate);dofs=header.dataOfs;
        rootPos1=header.rootPos1;rootPos2=header.rootPos2;rootPos3=header.rootPos3;
        rootPos4[0]=header.rootPos4[0];rootPos4[1]=header.rootPos4[1];
        error.clear();return true;
    } catch (const std::exception& failure) {
        error=failure.what();treef.close();toc=TreeTOC();return false;
    }
}
std::uint32_t ZTreeMgr::Idx(int lvl,int ilat,int ilng)
{
    // Bound shifts/indices before applying the original quadtree ordering.
    if (!toc.size() || lvl<1 || lvl>34 || ilat<0 || ilng<0) return UINT32_MAX;
    if (lvl<4 && (ilat || ilng)) return UINT32_MAX;
    if (lvl>=4 && (std::uint64_t(ilat)>=(std::uint64_t(1)<<(lvl-4)) ||
        std::uint64_t(ilng)>=(std::uint64_t(2)<<(lvl-4)))) return UINT32_MAX;
    if (lvl<=4) {
        return (lvl==1?rootPos1:lvl==2?rootPos2:lvl==3?rootPos3:rootPos4[ilng]);
    } else {
        int plvl=lvl-1;
        int pilat=ilat/2;
        int pilng=ilng/2;
        std::uint32_t pidx=Idx(plvl,pilat,pilng);
        if (pidx==UINT32_MAX) return pidx;
        int cidx=((ilat&1)<<1)+(ilng&1);
        return toc[pidx].child[cidx];
    }
}
std::uint32_t ZTreeMgr::ReadData(std::uint32_t index,unsigned char** output)
{
    if (!output) {error="Missing planetary archive output pointer";return 0;}
    *output=nullptr;
    if (index>=toc.size() || !toc.NodeSizeInflated(index)) return 0;
    try {
        const auto inflated=toc.NodeSizeInflated(index),compressed=toc.NodeSizeDeflated(index);
        treef.clear();treef.seekg(dofs+toc[index].pos);
        require(bool(treef),"Planetary archive seek failed");
        std::vector<unsigned char> input(compressed);
        require(bool(treef.read(reinterpret_cast<char*>(input.data()),input.size())),"Truncated planetary archive payload");
        std::unique_ptr<unsigned char[]> result(new unsigned char[inflated]);
        require(Inflate(input.data(),compressed,result.get(),inflated)==inflated,"Corrupt planetary archive payload/size");
        *output=result.release();error.clear();return inflated;
    } catch (const std::exception& failure) {error=failure.what();return 0;}
}
std::uint32_t ZTreeMgr::Inflate(const unsigned char* input,std::uint32_t inputSize,unsigned char* output,std::uint32_t outputSize)
{
    // uLong is 32 bits on Windows, 64 bits on native LP64 Linux.
    uLongf actual=outputSize;uLong consumed=inputSize;
    if (uncompress2(output,&actual,input,&consumed)!=Z_OK || actual!=outputSize || consumed!=inputSize) return 0;
    return static_cast<std::uint32_t>(actual);
}
void ZTreeMgr::ReleaseData(unsigned char* data) {delete[] data;}
