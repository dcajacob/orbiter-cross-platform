// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ==============================================================
//           ORBITER MODULE: LUA Inline Interpreter
//                  Part of the ORBITER SDK
//            Copyright (C) 2007-2026 Martin Schweiger
//                   All rights reserved
//
// LuaInline.h
// This library is loaded by the Orbiter core on demand to provide
// interpreter instances to modules via API requests.
//
// Notes:
// * LuaInline.dll must be placed in the Orbiter root directory
//   (not in the Modules subdirectory). It is loaded automatically
//   by Orbiter when required. It must not be loaded manually via
//   the Launchpad "Modules" tab.
// * LuaInline.dll depends on LuaInterpreter.dll and Lua5.1.dll
//   which must also be present in the Orbiter root directory.
// ==============================================================

#ifndef __LUAINLINE_H
#define __LUAINLINE_H

#include "InlineEnvironment.h"

// ==============================================================
// class InterpreterList: interface

class InterpreterList
#ifdef _WIN32
    : public oapi::Module
#endif
{
public:
	using Environment = InlineEnvironment;

#ifdef _WIN32
	InterpreterList (HINSTANCE hDLL);

	void clbkSimulationEnd () override;
	void clbkPostStep (double simt, double simdt, double mjd) override;
	void clbkSimulationStart (RenderMode mode) override;
	void clbkDeleteVessel (OBJHANDLE hVessel) override;
#else
    InterpreterList ();
    void clbkSimulationEnd ();
    void clbkPostStep (double simt, double simdt, double mjd);
    void clbkDeleteVessel (OBJHANDLE hVessel);
#endif
    ~InterpreterList ();
	
	Environment *AddInterpreter ();
	int DelInterpreter (Environment *env);

private:

	Environment **list;     // interpreter list
	oapi::UInt32 nlist;            // list size
	oapi::UInt32 nbuf;             // buffer size
};

#endif // !__LUAINLINE_H
