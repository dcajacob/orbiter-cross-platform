// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#include "tilelabel.h"
#include "RendererFiles.h"
#ifndef _WIN32
#include "Production/Text.h"
#endif
#include "OGLCamera.h"
#include <cstdlib>
#include <limits>
#include <memory>
#include <sstream>
#include <fstream>
#include "Scene.h"
#include "surfmgr2.h"
#include <cstring>

namespace {
int CompareLabelText(const char* left, const char* right)
{
#ifdef _WIN32
	return _stricmp(left, right);
#else
	return orbiter::production::CompareText(left, right);
#endif
}
}

TileLabel *TileLabel::Create(const SurfTile *stile)
{
	auto label = std::make_unique<TileLabel>(stile);
	label->Read();  // read label list from tile file

	const int lvlshift = 5;
	SurfTile *ancestor = 0;
	if (stile->lvl >= lvlshift) {
		QuadTreeNode<SurfTile> *nd4 = stile->node->Ancestor(lvlshift);
		if (nd4) ancestor = nd4->Entry();
	} else if (stile->lvl >= lvlshift-3) {
		ancestor = stile->smgr->GlobalTile(stile->lvl-lvlshift);
	}
	if (ancestor) label->ExtractAncestorData(ancestor);

	if (label->nlabel || label->nrenderlabel) {
		return label.release();
	}
	return nullptr;
}

TileLabel::TileLabel(const SurfTile *stile)
: tile(stile)
{
	nlabel = nrenderlabel = 0;
	nbuf = nrenderbuf = 0;
}

TileLabel::~TileLabel()
{
	if (nbuf) {
		for (int i = 0; i < nlabel; i++)
			delete label[i];
		delete []label;
	}
	if (nrenderbuf) {
		delete []renderlabel;
		// delete the list, not the labels themselves, since they are just
		// references to ancestor entries
	}
}

void TileLabel::ReadLabels(std::istream &input)
{
	std::string type, altitude, name;
	double lat, lng;
	while ((input >> type >> lat >> lng >> altitude) && std::getline(input, name)) {
		if (!name.empty() && name.back() == '\r') name.pop_back();
		auto entry = std::make_unique<TLABEL>();
		entry->lat = lat * RAD;
		entry->lng = lng * RAD;
		entry->alt = !CompareLabelText(altitude.c_str(), "nan")
			? std::numeric_limits<double>::quiet_NaN() : std::atof(altitude.c_str());
		entry->labeltype = type.front();
		entry->pos = _V(0, 0, 0);
		entry->label = new char[name.size() + 1];
		std::memcpy(entry->label, name.c_str(), name.size() + 1);
		if (nlabel == nbuf) {
			TLABEL **next = new TLABEL*[nbuf + 16];
			if (nlabel) {
				std::memcpy(next, label, nlabel * sizeof(*next));
				delete []label;
			}
			label = next;
			nbuf += 16;
		}
		label[nlabel++] = entry.release();
	}
}

bool TileLabel::Read()
{
	const int level = tile->lvl + 4;
	if (tile->mgr->Cprm().tileLoadFlags & 0x0001) {
		char name[512], path[512];
		std::snprintf(name, sizeof(name), "%s/Label/%02d/%06d/%06d.lab",
			tile->mgr->CbodyName(), level, tile->ilat, tile->ilng);
		std::string resolved;
		if (g_client->PlanetTexturePath(name, path) && RendererResolveFilePath(path, resolved)) {
			std::ifstream loose(resolved);
			ReadLabels(loose);
		}
	}
	auto *archive = tile->smgr->ZTreeManager(4);
	if (!nlabel && archive) {
		uint8_t *raw = nullptr;
		const int size = archive->ReadData(level, tile->ilat, tile->ilng, &raw);
		std::unique_ptr<uint8_t[]> bytes(raw);
		if (size > 0) {
			std::istringstream packed(std::string(reinterpret_cast<const char*>(bytes.get()), size));
			ReadLabels(packed);
		}
	}
	return nlabel > 0;
}

bool TileLabel::ExtractAncestorData (const SurfTile *atile)
{
	if (!atile) return false;
	TileLabel *atl = atile->label;
	if (atl && atl->nlabel) {
		TLABEL **alabel = atl->label;
		double lat, lng, latmin, latmax, lngmin, lngmax;
		tile->Extents(&latmin, &latmax, &lngmin, &lngmax);
		for (int i = 0; i < atl->nlabel; i++) {
			lat = alabel[i]->lat;
			lng = alabel[i]->lng;
			if (lat >= latmin && lat < latmax && lng >= lngmin && lng < lngmax) {
				if (nrenderlabel == nrenderbuf) { // grow buffer
					TLABEL **tmp = new TLABEL*[nrenderbuf+=16];
					if (nrenderlabel) {
						memcpy(tmp, renderlabel, nrenderlabel*sizeof(TLABEL*));
						delete []renderlabel;
					}
					renderlabel = tmp;
				}
				renderlabel[nrenderlabel++] = alabel[i];
				if (!alabel[i]->pos.x && !alabel[i]->pos.y && !alabel[i]->pos.z) {
					if (isnan(alabel[i]->alt))
						alabel[i]->alt = Elevation(lat, lng, latmin, latmax, lngmin, lngmax, tile->mgr->ElevRes());
					double rad = tile->mgr->CbodySize() + alabel[i]->alt;
					oapiEquToLocal(tile->mgr->Cbody(), lng, lat, rad, &alabel[i]->pos);
				}
			}
		}
	}
	return (nrenderlabel > 0);
}

double TileLabel::Elevation(double lat, double lng, double latmin, double latmax, double lngmin, double lngmax, double elev_res) const
{
	int16_t *elev = tile->ggelev;
	if (!elev) return 0.0;

	int blockRes = tile->mgr->GridRes();
	int16_t *elev_base = elev+TILE_ELEVSTRIDE+1; // strip padding
	double latidx = (lat-latmin) * blockRes/(latmax-latmin);
	double lngidx = (lng-lngmin) * blockRes/(lngmax-lngmin);
	int lat0 = (int)latidx;
	int lng0 = (int)lngidx;
	elev = elev_base + lat0*TILE_ELEVSTRIDE + lng0;
	double w_lat = latidx-lat0;
	double w_lng = lngidx-lng0;
	double e01 = elev[0]*(1.0-w_lng) + elev[1]*w_lng;
	double e02 = elev[TILE_ELEVSTRIDE]*(1.0-w_lng) + elev[TILE_ELEVSTRIDE+1]*w_lng;
	double e = e01*(1.0-w_lat) + e02*w_lat;
	return e*elev_res;
}

void TileLabel::Render(oapi::Sketchpad *skp, oapi::Font **labelfont, int *fontidx)
{
	if (!nrenderlabel) return; // nothing to render

	const int symscale[4] = {5, 6, 8, 10};
	int i;
	oapi::UInt32 col, pcol = 0;
	char symbol;
	int x, y, nl, scale;
	const RendererHost::LABELTYPE *lspec;
	VECTOR3 sp, dir;
	bool active = false;
	const OBJHANDLE &hPlanet = tile->mgr->Cbody();
	OGLCamera *cam = g_client->GetScene()->GetCamera();
	VECTOR3 Ppl;
	oapiGetGlobalPos(hPlanet, &Ppl); // planet global position
	VECTOR3 Pcam;
	oapiCameraGlobalPos (&Pcam);
	MATRIX3 Rpl;
	oapiGetRotationMatrix(hPlanet, &Rpl); // planet rotation matrix
	VECTOR3 campos = tmul(Rpl, Pcam - Ppl); // camera pos in planet frame

	for (i = 0; i < nrenderlabel; i++) {
		VECTOR3 camlabelpos = campos-renderlabel[i]->pos;
		if (dotp (renderlabel[i]->pos, camlabelpos) >= 0.0) {
			double fontscale = 1e4/length(camlabelpos)*(13-std::min(tile->lvl,12)*1);
			int idx = std::max(0, std::min(3, (int)fontscale));
			if (idx != *fontidx) {
				skp->SetFont(labelfont[idx]);
				*fontidx = idx;
			}
			scale = symscale[idx];
			sp = mul(Rpl, renderlabel[i]->pos) + Ppl - Pcam;
			dir = unit(sp);
			if (cam->Direction2Viewport(dir, x, y)) {

				symbol = 0; // undefined
				if ((nl = g_client->GetSurfaceMarkerLegend(hPlanet, &lspec))) {
					for (int j = 0; j < nl; j++) {
						if (renderlabel[i]->labeltype == lspec[j].labelId) {
							symbol = lspec[j].markerId;
							col = lspec[j].col;
							active = lspec[j].active;
							break;
						}
					}
				}
				if (!active) continue;

				if (!symbol) { // default
					symbol = 'S';
					col = 0x00ffffff;
				}
				if (col != pcol) {
					skp->SetTextColor(col);
					pcol = col;
				}
				switch (symbol) {
				case 'O': // circle
					skp->Ellipse(x-scale, y-scale, x+scale+1, y+scale+1);
					break;
				case 'D': // Delta
					skp->MoveTo(x, y-scale);
					skp->LineTo(x-scale, y+scale+1);
					skp->LineTo(x+scale+1, y+scale+1);
					skp->LineTo(x, y-scale);
					break;
				case 'N': // Nabla
					skp->MoveTo(x, y+scale+1);
					skp->LineTo(x-scale, y-scale);
					skp->LineTo(x+scale+1, y-scale);
					skp->LineTo(x, y+scale+1);
					break;
				default:
					skp->Rectangle(x-scale, y-scale, x+scale+1, y+scale+1);
					break;
				}
				skp->Text(x+scale+2, y-scale-1, renderlabel[i]->label, strlen(renderlabel[i]->label));
			}
		}
	}
}
