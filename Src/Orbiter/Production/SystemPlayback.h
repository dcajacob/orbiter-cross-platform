// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#pragma once
#include "Text.h"
#include "CameraModeOwner.h"
#include "VesselServices.h"
#include "VesselRecorderState.h"
#include "RigidBodyServices.h"
#include "SurfaceServices.h"
#include "../Camera.h"
#include "../Config.h"
#include "../PsysCore.h"
#include "../TimeData.h"
#include <istream>
#include <cstring>
#include <cstdio>

namespace orbiter::production {
template<class Focus, class Jump, class End>
void PlaySystemEvents(std::istream& stream, double& nextEvent, const TimeData& clock,
    Camera& camera, Focus setFocus, Jump jumpTo, End endSession)
{
	const auto& options = GetSurfaceServices().Configuration().CfgRecPlayPrm;
	// scan system event stream
	while (stream.good() && clock.SimT1 > nextEvent) {
		char cbuf[1024+12]{}, *s; // allow the original command offsets on an empty payload
		int i;
		stream.getline (cbuf, 1024);
		if (!stream && !stream.eof()) break;
		if (auto *cr = strchr(cbuf, '\r')) *cr = 0;
		s = strtok (cbuf, " \t");
		if (s) {
			if (!ComparePrefix (s, "TACC", 4)) {
				if (sscanf (s+5, "%lf%lf", &RecordingSpeed, &WarpDelay) < 2)
					WarpDelay = 0.0;
				if (options.bReplayWarp)
						GetVesselServices().PlaybackWarp(RecordingSpeed,WarpDelay);
			} else if (!ComparePrefix (s, "CAMERA", 6)) {
				s = strtok (NULL, " \t\n");
				if (options.bReplayCam && s && !ComparePrefix (s, "PRESET", 6)) {
					if (sscanf (s+7, "%d", &i) == 1) camera.RecallPreset (i);
				} else if (options.bReplayCam && s && !ComparePrefix (s, "SET", 3)) {
					OwnedCameraMode cm(CameraMode::Create(s+4));
					if (cm) camera.SetCMode(cm.get());
				}
			} else if (!ComparePrefix (s, "FOCUS", 5)) {
				s = strtok (NULL, " \t\n");
				vfocus = s ? GetRigidBodyServices().World()->GetVessel (s, true) : nullptr;
				if (vfocus && options.bReplayFocus)
					setFocus(vfocus);
			} else if (!ComparePrefix (s, "NOTE", 4)) {
				GetVesselServices().PlaybackNote(s);
			} else if (!ComparePrefix (s, "JUMPTOTIME", 10)) {
				double jumptime;
				if (sscanf (s+11, "%lf", &jumptime) == 1 && jumptime > clock.SimT0) {
					double tgtmjd = clock.MJD0 + (jumptime-clock.SimT0)/86400.0;
					jumpTo(tgtmjd);
				}
			} else if (!ComparePrefix (s, "ENDSESSION", 10)) {
				endSession();
			}
		}
		stream >> nextEvent;
	}
}
}
