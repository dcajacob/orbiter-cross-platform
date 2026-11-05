// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#ifndef __LUAMFD_H
#define __LUAMFD_H

#include "MfdInterpreter.h"
#include "MFDAPI.h"

// ==============================================================
// MFD class interface

class ScriptMFD: public MFD2 {
public:
	ScriptMFD (oapi::UInt32 w, oapi::UInt32 h, VESSEL *vessel);
	~ScriptMFD();
	char *ButtonLabel (int bt) override;
	int ButtonMenu (const MFDBUTTONMENU **menu) const;
	bool ConsumeKeyBuffered (oapi::UInt32 key) override;
	bool ConsumeButton (int bt, int event) override;
	bool Update (oapi::Sketchpad *skp) override;
	bool Input (const char *line);
	void QueryCommand ();
	void CreateInterpreter ();
	void DeleteInterpreter ();
	void SetPage (oapi::UInt32 newpg);
	static bool ScriptInput (void *id, char *str, void *data);
	static oapi::CockpitMessageResult MsgProc (oapi::UInt msg, oapi::UInt mfd, oapi::CockpitUnsignedParam wparam, oapi::CockpitSignedParam lparam);

protected:
	void SetFontSize (double size);

private:
	InterpreterList::VesselInterp *vi;
	OBJHANDLE hVessel;      // vessel object handle
#ifdef _WIN32
	HANDLE interpTh;        // interpreter thread handle
#endif
	oapi::Font *hFont;      // font handle
	oapi::UInt32 pg;               // current page
	oapi::UInt32 fw, fh;           // character width, height
	oapi::UInt32 nchar;            // characters per line displayed
	oapi::UInt32 nline;            // max number of lines displayed
};

#endif // !__LUAMFD_H
