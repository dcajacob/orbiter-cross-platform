// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// File access and original sample conversion are separate from interpolation.
#include "elevmgr.h"
#include "Celbody.h"
#include <climits>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <memory>
#include <stdexcept>

static constexpr int elev_stride=259;
#pragma pack(push,1)

struct ELEVFILEHEADER { // file header for patch elevation data file
	char id[4];            // ID string + version ('E','L','E',1)
	std::int32_t hdrsize;           // header size (100 expected)
	std::int32_t dtype;             // data format (0=flat, no data block; 8=uint8; -8=int8; 16=uint16; -16=int16)
	std::int32_t xgrd,ygrd;         // data grid size (259 x 259 expected)
	std::int32_t xpad,ypad;         // horizontal, vertical padding width (1, 1 expected)
	double scale;          // data scaling factor (1.0 expected)
	double offset;         // data offset (elevation = raw value * scale + offset)
	double latmin, latmax; // latitude range [rad]
	double lngmin, lngmax; // longitude range [rad]
	double emin, emax, emean; // min, max, mean elevation [m]
};

#pragma pack(pop)

static_assert(sizeof(ELEVFILEHEADER)==100,"Elevation disk header width changed");
static_assert(sizeof(std::int16_t)==2 && sizeof(double)==8);
namespace {
using File=std::unique_ptr<FILE,decltype(&std::fclose)>;
File openTile(const std::filesystem::path& path)
{
    if (path.empty() || !std::filesystem::exists(path)) return File(nullptr,&std::fclose);
    File file(std::fopen(path.string().c_str(),"rb"),&std::fclose);
    if (!file) throw std::runtime_error("Cannot read production elevation tile: "+path.string());
    return file;
}
void validate(const ELEVFILEHEADER& header)
{
    if (std::memcmp(header.id,"ELE\1",4) || header.hdrsize<100 || header.hdrsize>1048576 ||
        (header.dtype!=0 && header.dtype!=8 && header.dtype!=-16) ||
        header.xgrd!=259 || header.ygrd!=259 || header.xpad!=1 || header.ypad!=1 ||
        !std::isfinite(header.scale) || !std::isfinite(header.offset))
        throw std::runtime_error("Invalid or unsupported production elevation tile header");
}
void readSamples(void* target,std::size_t width,std::size_t count,FILE* file)
{
    if (std::fread(target,width,count,file)!=count) throw std::runtime_error("Truncated production elevation tile");
}
void readHeader(FILE* file,ELEVFILEHEADER& header)
{
    readSamples(&header,sizeof(header),1,file);validate(header);
    if (std::fseek(file,0,SEEK_END)) throw std::runtime_error("Cannot measure production elevation tile");
    const auto length=std::ftell(file);
    const std::size_t payload=header.dtype==0 ? 0 : 259*259*(header.dtype==8 ? 1 : 2);
    if (length<0 || static_cast<unsigned long long>(length)<static_cast<unsigned long long>(header.hdrsize)+payload)
        throw std::runtime_error("Truncated production elevation tile");
    if (std::fseek(file,header.hdrsize,SEEK_SET)) throw std::runtime_error("Cannot seek production elevation payload");
}
void validateBlock(const unsigned char* bytes,std::size_t length)
{
    if (!bytes || length<sizeof(ELEVFILEHEADER)) throw std::runtime_error("Truncated production elevation archive header");
    ELEVFILEHEADER header;std::memcpy(&header,bytes,sizeof(header));validate(header);
    const std::size_t payload=header.dtype==0 ? 0 : 259*259*(header.dtype==8 ? 1 : 2);
    if (static_cast<std::size_t>(header.hdrsize)>length || payload>length-header.hdrsize)
        throw std::runtime_error("Truncated production elevation archive payload");
}
}

bool ElevationManager::HasElevationTile(int lvl, int ilat, int ilng) const
{
	if (mode) {
		if (tilesource & 0x0001 && bDirExists) {
			const auto path=services->LooseTile(*cbody,false,lvl,ilat,ilng);
			if (!path.empty() && std::filesystem::exists(path)) return true;
		}
		if (treeMgr[0]) {
			if (treeMgr[0]->Idx(lvl, ilat, ilng) != orbiter::production::UInt32(-1)) return true;
		}
	}
	return false;
}

std::int16_t *ElevationManager::LoadElevationTile (int lvl, int ilat, int ilng, double tgt_res) const
{
	std::int16_t *elev = 0;
	std::unique_ptr<std::int16_t[]> owned;
	std::int16_t ofs;

	if (mode) {
		int i;
		const int ndat = elev_stride*elev_stride;
		double scale, offset;
		if (tilesource & 0x0001 && bDirExists) {
			const auto path=services->LooseTile(*cbody,false,lvl,ilat,ilng);
			if (auto file = openTile(path)) {
				FILE* f=file.get();
				owned.reset(new std::int16_t[ndat]);elev=owned.get();
				ELEVFILEHEADER hdr;
				readHeader(f,hdr);
				scale  = hdr.scale;
				offset = hdr.offset;
				switch (hdr.dtype) {
				case 0: // flat tile, defined by offset
					for (i = 0; i < ndat; i++) elev[i] = 0;
					break;
				case 8: {
					std::unique_ptr<std::uint8_t[]> temporary(new std::uint8_t[ndat]);
					std::uint8_t *tmp=temporary.get();
					readSamples(tmp,sizeof(std::uint8_t),ndat,f);
					for (i = 0; i < ndat; i++)
						elev[i] = (std::int16_t)tmp[i];
					tmp = NULL;
					}
					break;
				case -16:
					readSamples(elev,sizeof(std::int16_t),ndat,f);
					break;
				}
			}
		}
		if (!elev && treeMgr[0]) {
			unsigned char *buf;
			orbiter::production::UInt32 ndata = treeMgr[0]->ReadData(lvl, ilat, ilng, &buf);
			std::unique_ptr<unsigned char[]> buffer(buf);
			if (!ndata && !treeMgr[0]->Error().empty()) throw std::runtime_error(treeMgr[0]->Error());
			if (ndata) {
				validateBlock(buf,ndata);
				unsigned char *p = buf;
				owned.reset(new std::int16_t[ndat]);elev=owned.get();
				ELEVFILEHEADER *phdr = (ELEVFILEHEADER*)p;
				p += phdr->hdrsize;
				scale  = phdr->scale;
				offset = phdr->offset;
				switch (phdr->dtype) {
				case 0: // flat tile, defined by offset
					for (i = 0; i < ndat; i++) elev[i] = 0;
					break;
				case 8:
					for (i = 0; i < ndat; i++)
						elev[i] = (std::int16_t)(*p++);
					break;
				case -16:
					memcpy(elev, p, ndat*sizeof(std::int16_t));
					p += ndat*sizeof(std::int16_t);
					break;
				}
			}
		}
		if (elev) {
			if (scale != tgt_res) { // rescale the data
				double rescale = scale/tgt_res;
				for (i = 0; i < ndat; i++)
					elev[i] = (std::int16_t)(elev[i]*rescale);
			}
			if (offset) {
				std::int16_t sofs = (std::int16_t)(offset/tgt_res);
				for (i = 0; i < ndat; i++)
					elev[i] += sofs;
			}
		}
	}
	return owned.release();
}

bool ElevationManager::LoadElevationTile_mod (int lvl, int ilat, int ilng, double tgt_res, std::int16_t *elev) const
{
	if (mode) {
		int i;
		const int ndat = elev_stride*elev_stride;
		double rescale;
		std::int16_t offset;
		bool do_shift, do_rescale;
		if (tilesource & 0x0001 && bModExists) {
			const auto path=services->LooseTile(*cbody,true,lvl,ilat,ilng);
			if (auto file = openTile(path)) {
				FILE* f=file.get();
				ELEVFILEHEADER hdr;
				readHeader(f,hdr);
				rescale = (do_rescale = (hdr.scale != tgt_res)) ? hdr.scale/tgt_res : 1.0;
				offset  = (do_shift   = (hdr.offset != 0.0)) ? (std::int16_t)(hdr.offset/tgt_res) : 0;
				switch (hdr.dtype) {
				case 0: // overwrite the entire tile with a flat offset
					for (i = 0; i < ndat; i++) elev[i] = offset;
					break;
				case 8: {
					const std::uint8_t mask = UCHAR_MAX;
					std::unique_ptr<std::uint8_t[]> temporary(new std::uint8_t[ndat]);
					std::uint8_t *tmp=temporary.get();
					readSamples(tmp,sizeof(std::uint8_t),ndat,f);
					for (i = 0; i < ndat; i++) {
						if (tmp[i] != mask) {
							elev[i] = (std::int16_t)(do_rescale ? (std::int16_t)(tmp[i]*rescale) : (std::int16_t)tmp[i]);
							if (do_shift) elev[i] += offset;
						}
					}
					tmp = NULL;
					}
					break;
				case -16: {
					const std::int16_t mask = SHRT_MAX;
					std::unique_ptr<std::int16_t[]> temporary(new std::int16_t[ndat]);
					std::int16_t *tmp=temporary.get();
					std::int16_t ofs = (std::int16_t)hdr.offset;
					readSamples(tmp,sizeof(std::int16_t),ndat,f);
					for (i = 0; i < ndat; i++) {
						if (tmp[i] != mask) {
							elev[i] = (do_rescale ? (std::int16_t)(tmp[i]*rescale) : tmp[i]);
							if (do_shift) elev[i] += offset;
						}
					}
					tmp = NULL;
					}
					break;
				}
				return true;
			}
		}
		if (treeMgr[1]) {
			unsigned char *buf;
			orbiter::production::UInt32 ndata = treeMgr[1]->ReadData(lvl, ilat, ilng, &buf);
			std::unique_ptr<unsigned char[]> buffer(buf);
			if (!ndata && !treeMgr[1]->Error().empty()) throw std::runtime_error(treeMgr[1]->Error());
			if (ndata) {
				validateBlock(buf,ndata);
				unsigned char *p = buf;
				ELEVFILEHEADER *phdr = (ELEVFILEHEADER*)p;
				p += phdr->hdrsize;
				std::int16_t ofs = (std::int16_t)phdr->offset;
				rescale = (do_rescale = (phdr->scale != tgt_res)) ? phdr->scale/tgt_res : 1.0;
				offset  = (do_shift   = (phdr->offset != 0.0)) ? (std::int16_t)(phdr->offset/tgt_res) : 0;
				switch (phdr->dtype) {
				case 0:
					for (i = 0; i < ndat; i++) elev[i] = offset;
					break;
				case 8: {
					const std::uint8_t mask = UCHAR_MAX;
					for (i = 0; i < ndat; i++) {
						if (p[i] != mask) {
							elev[i] = (std::int16_t)(do_rescale ? p[i]*rescale : p[i]);
							if (do_shift) elev[i] += offset;
						}
					}
					} break;
				case -16: {
					const std::int16_t mask = SHRT_MAX;
					std::int16_t *buf16 = (std::int16_t*)p;
					for (i = 0; i < ndat; i++) {
						if (buf16[i] != mask) {
							elev[i] = (do_rescale ? (std::int16_t)(buf16[i]*rescale) : buf16[i]);
							if (do_shift) elev[i] += offset;
						}
					}
					} break;
				}
				return true;
			}
		}
	}
	return false;
}
