// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_VESSEL_RECORDER_STATE_H
#define ORBITER_PRODUCTION_VESSEL_RECORDER_STATE_H
class Vessel;
// Existing process-global recorder stream state, shared by the unchanged
// Windows system recorder and the production vessel recorder.
extern double Tofs,MJDofs,RecordingSpeed,WarpDelay;
extern Vessel* vfocus;
#endif
