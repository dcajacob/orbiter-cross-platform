// Licensed under the MIT License
#ifndef ORBITER_ELEVATION_FILE_TEST_H
#define ORBITER_ELEVATION_FILE_TEST_H
#include "elevmgr.h"
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <limits>
#include <memory>
#include <vector>
namespace elevation_files_test {
void require(bool value,const char* message) {if (!value) throw std::runtime_error(message);}
struct Files final : orbiter::production::ElevationServices {
    std::filesystem::path directory;
    orbiter::production::ElevationSetup Setup(const CelestialBody&) const override {return {2,1,14,1};}
    std::unique_ptr<ZTreeMgr> OpenArchive(const CelestialBody&,bool) override {throw std::logic_error("No archives requested by loose-file test");}
    bool HasLooseLayer(const CelestialBody&,bool) const override {return true;}
    std::filesystem::path LooseTile(const CelestialBody&,bool modified,int,int,int) const override
    {return directory/(modified ? "mod.elv" : "base.elv");}
    double SystemTime() const override {return 0;}
    void Filter(const CelestialBody&,int,int,int,double,std::int16_t*) override {throw std::logic_error("No interpolation in file test");}
};
struct Manager : ElevationManager {
    Manager(CelestialBody& body,Files& files):ElevationManager(&body,files.Setup(body),files) {}
    using ElevationManager::LoadElevationTile;
    using ElevationManager::LoadElevationTile_mod;
};
void word(std::vector<unsigned char>& bytes,std::size_t offset,std::uint64_t value,unsigned size)
{for (unsigned i=0;i<size;++i) bytes.at(offset+i)=static_cast<unsigned char>(value>>(8*i));}
void real(std::vector<unsigned char>& bytes,std::size_t offset,double value)
{std::uint64_t bits;std::memcpy(&bits,&value,8);word(bytes,offset,bits,8);}
std::vector<unsigned char> tile(int type,double scale=1,double offset=0)
{
    std::vector<unsigned char> bytes(100+(type==0 ? 0 : 259*259*(type==8 ? 1 : 2)));
    std::memcpy(bytes.data(),"ELE\1",4);word(bytes,4,100,4);word(bytes,8,static_cast<std::uint32_t>(type),4);
    word(bytes,12,259,4);word(bytes,16,259,4);word(bytes,20,1,4);word(bytes,24,1,4);
    real(bytes,28,scale);real(bytes,36,offset);return bytes;
}
void write(const std::filesystem::path& path,const std::vector<unsigned char>& bytes)
{
    std::ofstream output(path,std::ios::binary);output.exceptions(std::ios::badbit|std::ios::failbit);
    output.write(reinterpret_cast<const char*>(bytes.data()),bytes.size());
}
void run(CelestialBody& body,const std::filesystem::path& directory)
{
    Files files;files.directory=directory/"elevation-files";std::filesystem::create_directories(files.directory);
    Manager manager(body,files);auto base=files.directory/"base.elv";auto mod=files.directory/"mod.elv";
    auto flat=tile(0,1,125);write(base,flat);
    std::unique_ptr<std::int16_t[]> samples(manager.LoadElevationTile(4,0,0,1));
    require(samples && samples[0]==125 && samples[259*259-1]==125,"Flat production elevation offset differs");
    auto bytes=tile(8,.5,10);std::fill(bytes.begin()+100,bytes.end(),4);write(base,bytes);
    samples.reset(manager.LoadElevationTile(4,0,0,.5));
    require(samples && samples[0]==24,"Production elevation scale/offset conversion differs");
    auto signedSamples=tile(-16);
    for (unsigned i=0;i<259*259;++i) word(signedSamples,100+2*i,static_cast<std::uint16_t>(-13),2);
    write(base,signedSamples);samples.reset(manager.LoadElevationTile(4,0,0,1));
    require(samples && samples[0]==-13 && samples[259*259-1]==-13,"Signed production elevation decoding differs");
    auto changes=tile(8,.5,2);std::fill(changes.begin()+100,changes.end(),255);changes[101]=12;write(mod,changes);
    require(manager.LoadElevationTile_mod(4,0,0,1,samples.get()) && samples[0]==-13 && samples[1]==8,
        "Unsigned elevation modification mask/scale differs");
    changes=tile(-16,.5,2);for (unsigned i=0;i<259*259;++i) word(changes,100+2*i,32767,2);
    word(changes,102,static_cast<std::uint16_t>(-6),2);write(mod,changes);
    require(manager.LoadElevationTile_mod(4,0,0,1,samples.get()) && samples[0]==-13 && samples[1]==-1,
        "Signed elevation modification mask/scale differs");
    write(mod,tile(0,1,33));require(manager.LoadElevationTile_mod(4,0,0,1,samples.get()) && samples[0]==33,
        "Flat modification did not replace production tile");
    for (int variant=0;variant<7;++variant) {
        auto invalid=tile(8);
        if (variant==0) invalid.resize(20);
        if (variant==1) invalid[0]='X';
        if (variant==2) word(invalid,12,258,4);
        if (variant==3) word(invalid,8,16,4);
        if (variant==4) real(invalid,28,std::numeric_limits<double>::quiet_NaN());
        if (variant==5) invalid.pop_back();
        if (variant==6) word(invalid,4,99,4);
        write(base,invalid);bool rejected=false;
        try {std::unique_ptr<std::int16_t[]> unused(manager.LoadElevationTile(4,0,0,1));}catch(const std::runtime_error&){rejected=true;}
        require(rejected,"Malformed production elevation tile was accepted");
        require(std::filesystem::remove(base),"Failed elevation parsing leaked an open file");
    }
    require(!manager.LoadElevationTile(4,0,0,1),"Absent optional tile did not permit original parent lookup");
}
}
#endif
