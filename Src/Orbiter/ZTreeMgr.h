// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef __ZTREEMGR_H
#define __ZTREEMGR_H
#include "Production/Export.h"
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

// In-memory values. Disk records are explicitly decoded, never read through
// compiler layout: 48-byte header, 32-byte node, little-endian integers.
struct TreeNode {
    std::int64_t pos=0;
    std::uint32_t size=0;
    std::uint32_t child[4]={UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX};
};
class ORBITER_PRODUCTION_API TreeFileHeader {
    friend class ZTreeMgr;
public:
    TreeFileHeader();
    std::size_t fwrite(std::FILE* file);
    bool fread(std::FILE* file);
private:
    bool Read(std::istream& stream);
    bool Decode(const unsigned char* bytes);
    unsigned char magic[4];
    std::uint32_t size,flags,dataOfs;
    std::int64_t dataLength;
    std::uint32_t nodeCount,rootPos1,rootPos2,rootPos3,rootPos4[2];
};
class ORBITER_PRODUCTION_API TreeTOC {
    friend class ZTreeMgr;
public:
    TreeTOC()=default;
    std::size_t fread(std::uint32_t count,std::FILE* file);
    std::uint32_t size() const {return static_cast<std::uint32_t>(tree.size());}
    const TreeNode& operator[](std::uint32_t index) const {return tree.at(index);}
    std::uint32_t NodeSizeDeflated(std::uint32_t index) const;
    std::uint32_t NodeSizeInflated(std::uint32_t index) const {return index<size()?tree[index].size:0;}
private:
    void Read(std::uint32_t count,std::istream& stream);
    std::vector<TreeNode> tree;
    std::int64_t totlength=0;
};
class ORBITER_PRODUCTION_API ZTreeMgr {
public:
    enum Layer {LAYER_SURF,LAYER_MASK,LAYER_ELEV,LAYER_ELEVMOD,LAYER_LABEL,LAYER_CLOUD};
    static ZTreeMgr* CreateFromFile(const char* planetPath,Layer layer);
    // Open an already indexed filename, preserving its actual case on disk.
    // Required corrupt/missing archives throw instead of becoming absent layers.
    static std::unique_ptr<ZTreeMgr> OpenArchiveFile(const std::filesystem::path& file,Layer layer);
    ZTreeMgr(const char* planetPath,Layer layer);
    ~ZTreeMgr()=default;
    ZTreeMgr(const ZTreeMgr&)=delete;
    ZTreeMgr& operator=(const ZTreeMgr&)=delete;
    const TreeTOC& TOC() const {return toc;}
    const std::string& Error() const {return error;}
    std::uint32_t Idx(int level,int latitude,int longitude);
    std::uint32_t ReadData(std::uint32_t index,unsigned char** output);
    std::uint32_t ReadData(int level,int latitude,int longitude,unsigned char** output)
    {return ReadData(Idx(level,latitude,longitude),output);}
    void ReleaseData(unsigned char* data);
    std::uint32_t NodeSizeDeflated(std::uint32_t index) const {return toc.NodeSizeDeflated(index);}
    std::uint32_t NodeSizeInflated(std::uint32_t index) const {return toc.NodeSizeInflated(index);}
protected:
    bool OpenArchive();
    std::uint32_t Inflate(const unsigned char* input,std::uint32_t inputSize,unsigned char* output,std::uint32_t outputSize);
private:
    ZTreeMgr(const std::filesystem::path& file,Layer layer,bool direct);
    std::filesystem::path path;
    bool directPath=false;
    Layer layer;
    std::ifstream treef;
    TreeTOC toc;
    std::uint32_t rootPos1=UINT32_MAX,rootPos2=UINT32_MAX,rootPos3=UINT32_MAX,rootPos4[2]={UINT32_MAX,UINT32_MAX};
    std::int64_t dofs=0;
    std::string error;
};
#endif
