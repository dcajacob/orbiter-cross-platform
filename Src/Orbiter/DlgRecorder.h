// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Flight recorder dialog
// ======================================================================

#ifndef __DLGRECORDER_H
#define __DLGRECORDER_H

#ifdef _WIN32
#include "OrbiterAPI.h"
#else
#include "NativeVesselAPI.h"
#endif

class DlgRecorder : public ImGuiDialog {
public:
    DlgRecorder();
    void OnDraw() override;
    void DrawNormalRecording(bool recording);
    void DrawPlaying();

    char m_ScenarioFile[128];
    void GetRecordName (char *str, int maxlen) const;
};

#endif // !__DLGRECORDER_H
