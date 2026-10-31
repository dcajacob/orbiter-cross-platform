// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_MESH_READER_H
#define ORBITER_PRODUCTION_MESH_READER_H
#include <istream>
#include <cstring>
#include <cstdio>
#include <cstdint>
#include <cinttypes>
#include <cctype>
#include <memory>
#include <limits>

namespace orbiter::production {
using NameBuffer = char[256];
inline bool ReadMeshLine(std::istream& input, char (&line)[256])
{
    if (!input.getline(line, 256)) return false;
    const auto length = std::strlen(line);
    if (length && line[length-1] == '\r') line[length-1] = '\0';
    return true;
}
inline int ComparePrefix(const char* a, const char* b, std::size_t count)
{
    for (std::size_t i = 0; i < count; ++i) {
        auto lower = [](unsigned char c) { return c >= 'A' && c <= 'Z' ? c + 32 : c; };
        const int x = lower(static_cast<unsigned char>(a[i]));
        const int y = lower(static_cast<unsigned char>(b[i]));
        if (x != y || !x) return x - y;
    }
    return 0;
}

// Original production MSHX1 parser, with resource acquisition supplied by a sink.
// The Windows sink retains SDK/Direct3D types; the native sink owns CPU data.
// Numeric records and group order are shared, not reparsed by a second loader.
template<class Sink>
std::istream& ReadMesh(std::istream& is, Sink& mesh)
{
	using Vertex = typename Sink::Vertex;
	using Index = typename Sink::Index;
	using Material = typename Sink::Material;
	char cbuf[256];
	int i, j, g, ngrp, nvtx, ntri, nidx, nmtrl, mtrl_idx, ntex, tex_idx, flag, res;
	std::uint32_t uflag;
	std::uint16_t zbias;
	Material mtrl;
	bool term, staticmesh = false;

	auto fail = [&]() -> std::istream& { is.setstate(std::ios::failbit); return is; };
	mesh.Clear();

	if (!ReadMeshLine(is, cbuf)) return is;
	if (strcmp (cbuf, "MSHX1")) return fail();

	for (;;) {
		if (!ReadMeshLine(is, cbuf)) return is;
		if (!ComparePrefix (cbuf, "GROUPS", 6)) {
			if (sscanf (cbuf+6, "%d", &ngrp) != 1 || ngrp <= 0) return fail();
			break;
		} else if (!ComparePrefix (cbuf, "STATICMESH", 10)) {
			staticmesh = true;
		}
	}

	for (g = 0, term = false; g < ngrp && !term; g++) {

		// set defaults
		std::unique_ptr<Vertex[]> ownedVertices;
		std::unique_ptr<Index[]> ownedIndices;
		Vertex *vtx = nullptr;
		Index *idx = nullptr;
		mtrl_idx = -2; // original SPEC_INHERIT
		tex_idx  = -2;
		zbias    = 0;
		flag     = (staticmesh ? 0x04 : 0);
		uflag    = 0;
		bool bnormal = true, calcnml = false;
		bool flipidx = false;
		nvtx = ntri = 0;

		for (;;) {
			if (!ReadMeshLine(is, cbuf)) return is;
			if (!ComparePrefix (cbuf, "MATERIAL", 8)) {       // read material index
				sscanf (cbuf+8, "%d", &mtrl_idx);
				mtrl_idx--;
			} else if (!ComparePrefix (cbuf, "TEXTURE", 7)) { // read texture index
				sscanf (cbuf+7, "%d", &tex_idx);
				tex_idx--;
			} else if (!ComparePrefix (cbuf, "ZBIAS", 5)) {   // read z-bias
				sscanf (cbuf+5, "%hu", &zbias);
			} else if (!ComparePrefix (cbuf, "TEXWRAP", 7)) { // read wrap flags
				char uvstr[10] = "";
				sscanf (cbuf+7, "%9s", uvstr);
				if (uvstr[0] == 'U' || uvstr[1] == 'U') flag |= 0x01;
				if (uvstr[0] == 'V' || uvstr[1] == 'V') flag |= 0x02;
			} else if (!ComparePrefix (cbuf, "NONORMAL", 8)) {
				bnormal = false; calcnml = true;
			} else if (!ComparePrefix (cbuf, "FLAG", 4)) {
				sscanf (cbuf+4, "%" SCNx32, &uflag);
			} else if (!ComparePrefix (cbuf, "FLIP", 4)) {
				flipidx = true;
			} else if (!ComparePrefix (cbuf, "LABEL", 5)) {
				// ignore group labels here
			} else if (!ComparePrefix (cbuf, "STATIC", 6)) {
				flag |= 0x04;
			} else if (!ComparePrefix (cbuf, "DYNAMIC", 7)) {
				flag ^= 0x04;
			} else if (!ComparePrefix (cbuf, "GEOM", 4)) {    // read geometry
				if (sscanf (cbuf+4, "%d%d", &nvtx, &ntri) != 2 || nvtx <= 0 ||
					nvtx > 65536 || ntri <= 0 || ntri > std::numeric_limits<int>::max()/3) return fail();
				nidx = ntri*3;
				ownedVertices.reset(new Vertex[nvtx]);
				vtx = ownedVertices.get();
				std::memset(vtx, 0, sizeof(Vertex)*nvtx);
				for (i = 0; i < nvtx; i++) {
					Vertex &v = vtx[i];
					if (!ReadMeshLine(is, cbuf)) return is;
					if (bnormal) {
						j = sscanf (cbuf, "%f%f%f%f%f%f%f%f",
							&v.x, &v.y, &v.z, &v.nx, &v.ny, &v.nz, &v.tu, &v.tv);
						if (j < 6) {
							calcnml = true;
							// sscanf wrote UV coords into normal fields - relocate them
							v.tu = v.nx;
							v.tv = v.ny;
							// Zero the normal so CalcNormals() will recalculate this vertex
							v.nx = 0.0f;
							v.ny = 0.0f;
							v.nz = 0.0f;
						}
					} else {
						j = sscanf (cbuf, "%f%f%f%f%f",
							&v.x, &v.y, &v.z, &v.tu, &v.tv);
					}
					if (j < 3) return fail(); // stock untextured groups contain positions only
				}
				ownedIndices.reset(new Index[nidx]);
				idx = ownedIndices.get();
				std::memset(idx, 0, sizeof(Index)*nidx);
				for (i = j = 0; i < ntri; i++) {
					if (!ReadMeshLine(is, cbuf)) return is;
					if (sscanf(cbuf, "%" SCNu16 "%" SCNu16 "%" SCNu16, idx+j, idx+j+1, idx+j+2) != 3 ||
						idx[j] >= nvtx || idx[j+1] >= nvtx || idx[j+2] >= nvtx) return fail();
					j += 3;
				}
				if (flipidx)
					for (i = 0; i < ntri; i++) {
						Index tmp = idx[i*3+1]; idx[i*3+1] = idx[i*3+2]; idx[i*3+2] = tmp;
					}

				break;
			}
		}
		if (nvtx && nidx) {
			mesh.AddGroup (ownedVertices.release(), nvtx, ownedIndices.release(), nidx, mtrl_idx, tex_idx, zbias);
			mesh.SetGroupFlags(g, flag, uflag);
			if (calcnml) mesh.CalcNormals (g, true);
			if (flag & 0x04) mesh.StaticGroup(g);
		}
	}

	// read material list
	if (ReadMeshLine(is, cbuf) && !strncmp (cbuf, "MATERIALS", 9) && (sscanf (cbuf+9, "%d", &nmtrl) == 1)) {
		if (nmtrl < 0) return fail();
		std::unique_ptr<NameBuffer[]> matname(new NameBuffer[nmtrl]);
		NameBuffer mnm;
		for (i = 0; i < nmtrl; i++) {
			if (!ReadMeshLine(is, cbuf)) return is;
			sscanf (cbuf, "%255s", matname[i]);
		}
		for (i = 0; i < nmtrl; i++) {
			std::memset(&mtrl, 0, sizeof(Material));
			if (!ReadMeshLine(is, cbuf)) return is;
			sscanf (cbuf+8, "%255s", mnm);
			if (!ReadMeshLine(is, cbuf)) return is;
			sscanf (cbuf, "%f%f%f%f", &mtrl.diffuse.r, &mtrl.diffuse.g, &mtrl.diffuse.b, &mtrl.diffuse.a);
			if (!ReadMeshLine(is, cbuf)) return is;
			sscanf (cbuf, "%f%f%f%f", &mtrl.ambient.r, &mtrl.ambient.g, &mtrl.ambient.b, &mtrl.ambient.a);
			if (!ReadMeshLine(is, cbuf)) return is;
			res = sscanf (cbuf, "%f%f%f%f%f", &mtrl.specular.r, &mtrl.specular.g, &mtrl.specular.b, &mtrl.specular.a, &mtrl.power);
			if (res < 5) mtrl.power = 0.0;
			if (!ReadMeshLine(is, cbuf)) return is;
			sscanf (cbuf, "%f%f%f%f", &mtrl.emissive.r, &mtrl.emissive.g, &mtrl.emissive.b, &mtrl.emissive.a);
			mesh.AddMaterial (mtrl);
		}

	}

	// read texture list
	mesh.ReleaseTextures ();
	if (ReadMeshLine(is, cbuf) && !strncmp (cbuf, "TEXTURES", 8) && (sscanf (cbuf+8, "%d", &ntex) == 1)) {
		if (ntex < 0) return fail();
		mesh.CreateTextures(ntex);
		NameBuffer texname = {}, flagstr;
		for (i = 0; i < ntex; i++) {
			if (!ReadMeshLine(is, cbuf)) return is;
			flagstr[0] = '\0';
			sscanf (cbuf, "%255s%255s", texname, flagstr);

			if (texname[0] != '0' || texname[1] != '\0') {
				bool uncompress = (std::toupper(static_cast<unsigned char>(flagstr[0])) == 'D');
				mesh.LoadTexture(i, texname, 8 | (uncompress ? 2:0));
			}
		}
	}

	mesh.Setup();
	is.clear();
	return is;
}

}
#endif
