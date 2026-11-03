// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// =======================================================================
// class Instrument_User
// Custom MFD mode

#ifndef __MFD_USER_H
#define __MFD_USER_H

#define STRICT 1
#include "Mfd.h"
#include "MFDAPI.h"

class Instrument_User: public Instrument {
public:
	Instrument_User (Pane *_pane, std::intptr_t _id, const Spec &spec, Vessel *_vessel,
		int _type, const MFDMODE &mode);
	Instrument_User (Pane *_pane, std::intptr_t _id, const Spec &spec, Vessel *_vessel);
	virtual ~Instrument_User();
	int Type() const { return type; }
	char ModeSelKey () const { return selkey; }
	inline bool KeyImmediate (char *kstate) { return mfd->ConsumeKeyImmediate (kstate); }
	inline bool KeyBuffered (oapi::UInt32 key) { return mfd->ConsumeKeyBuffered (key); }
	inline bool ProcessButton (int bt, int event) { return mfd->ConsumeButton (bt, event); }
	inline const char *BtnLabel (int bt) const { return mfd->ButtonLabel (bt); }
	inline int BtnMenu (const MFDBUTTONMENU **menu) const { return (mfd ? mfd->ButtonMenu (menu) : 0); }
	void UpdateDraw (oapi::Sketchpad *skp);
	void UpdateDraw (oapi::SdkDrawContext hDC);

protected:
	bool ReadParams (std::ifstream &ifs);
	void WriteParams (std::ostream &ofs) const;

private:
	bool OpenMode(MFDMODESPECEX *spec);
	int type;
	char *name;
	char selkey;
	MFD *mfd; // pointer to module interface
	MFD2 *mfd2; // pointer to version 2 interface (0 if not applicable)
	oapi::CockpitMessageResult (*msgproc)(oapi::UInt,oapi::UInt,oapi::CockpitUnsignedParam,oapi::CockpitSignedParam);
};

#endif // !__MFD_USER_H
