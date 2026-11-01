// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifdef _WIN32
#define OAPI_IMPLEMENTATION
#include "OrbiterAPI.h"
#endif
#include "Vessel.h"
#include <cstring>
#include <cstdio>

LightEmitter *Vessel::AddPointLight (const VECTOR3 &pos, double range, double att0, double att1, double att2, COLOUR4 col_diff, COLOUR4 col_spec, COLOUR4 col_ambi)
{
	LightEmitter **tmp = new LightEmitter*[nemitter+1];
	if (nemitter) {
		memcpy (tmp, emitter, nemitter*sizeof(LightEmitter*));
		delete []emitter;
	}
	emitter = tmp;
	LightEmitter *pl = new PointLight ((OBJHANDLE)this, pos, range, att0, att1, att2, col_diff, col_spec, col_ambi);
	emitter[nemitter++] = pl;
	return pl;
}

LightEmitter *Vessel::AddSpotLight (const VECTOR3 &pos, const VECTOR3 &dir, double range, double att0, double att1, double att2, double umbra, double penumbra, COLOUR4 col_diff, COLOUR4 col_spec, COLOUR4 col_ambi)
{
	LightEmitter **tmp = new LightEmitter*[nemitter+1];
	if (nemitter) {
		memcpy (tmp, emitter, nemitter*sizeof(LightEmitter*));
		delete []emitter;
	}
	emitter = tmp;
	LightEmitter *pl = new SpotLight ((OBJHANDLE)this, pos, dir, range, att0, att1, att2, umbra, penumbra, col_diff, col_spec, col_ambi);
	emitter[nemitter++] = pl;
	return pl;
}

bool Vessel::DelLightEmitter (LightEmitter *le)
{
	oapi::UInt32 i, j, k;
	for (i = 0; i < nemitter; i++) {
		if (emitter[i] == le) {
			LightEmitter **tmp;
			if (nemitter > 1) {
				tmp = new LightEmitter*[nemitter-1];
				for (j = k = 0; j < nemitter; j++)
					if (j != i) tmp[k++] = emitter[j];
			} else tmp = NULL;
			delete []emitter;
			emitter = tmp;
			delete le;
			nemitter--;
			return true;
		}
	}
	return false;
}

void Vessel::ClearLightEmitters ()
{
	if (!nemitter) return; // nothing to do
	for (oapi::UInt32 i = 0; i < nemitter; i++) {
		if (emitter[i]) delete emitter[i];
	}
	delete []emitter;
	nemitter = 0;
}

void Vessel::LightEmitterState (LightEmitter *le, int param, void *value)
{
	oapi::UInt32 idx;
	char cbuf[256];
	for (idx = 0; idx < nemitter; idx++)
		if (emitter[idx] == le) break;
	if (idx == nemitter) return;
	switch (param) {
	case 0: { // activation state
		bool active = *(bool*)value;
		sprintf (cbuf, "%d ACTIVATE %d", idx, active);
		FRecorder_SaveEvent ("LIGHTSOURCE", cbuf);
	} break;
	}
}

void Vessel::ShiftLightEmitters (const VECTOR3 &ofs)
{
	oapi::UInt32 i;
	for (i = 0; i < nemitter; i++) {
		emitter[i]->ShiftExplicitPosition (ofs);
	}
}
