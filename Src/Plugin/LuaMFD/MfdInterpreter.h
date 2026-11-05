// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#ifndef __MFDINTERPRETER_H
#define __MFDINTERPRETER_H

#include "Interpreter.h"
#ifndef _WIN32
#include <exception>
#include <thread>
#endif

#define NCHAR 80 // characters per line in console buffer
#define NLINE 50 // number of buffered lines

class InterpreterList;

// ==============================================================
// MFD interpreter class interface

class MFDInterpreter: public Interpreter {
public:
	struct LineSpec {
		char buf[NCHAR];
		oapi::UInt32 col;
		LineSpec *prev, *next;
	};

	MFDInterpreter ();
	~MFDInterpreter () override;
	void SetSelf (OBJHANDLE hV);
	void LoadAPI();
	void AddLine (const char *line, oapi::UInt32 col);
	inline LineSpec *FirstLine() const { return lineFirst; }
	inline oapi::UInt32 LineCount() const { return nline; }
	void term_strout (const char *str, bool iserr=false);
	void term_clear ();

protected:
	static int termOut (lua_State *L);
	static int termLineUp (lua_State *L);
	static int termSetVerbosity (lua_State *L);
	static int termClear (lua_State *L);

private:
	LineSpec *lineFirst, *lineLast;
	oapi::UInt32 nline;
};

// ==============================================================
// Interpreter repository

class InterpreterList {
public:
	struct Environment {
		Environment (OBJHANDLE hV);
		~Environment();
		MFDInterpreter *CreateInterpreter (OBJHANDLE hV);
		MFDInterpreter *interp;
#ifdef _WIN32
		HANDLE hThread;
#else
        std::thread thread;
        std::exception_ptr failure;
        void Advance();
        void Run();
#endif
		char cmd[1024];
#ifdef _WIN32
		static unsigned int WINAPI InterpreterThreadProc (LPVOID context);
#endif
	};
	struct VesselInterp {
		OBJHANDLE hVessel;
		Environment **env;
		oapi::UInt32 nenv;
	} *list;
	oapi::UInt32 nlist;
	oapi::UInt32 nbuf;

	InterpreterList();
	~InterpreterList();

	void Update (double simt, double simdt, double mjd);

	Environment *AddInterpreter (OBJHANDLE hV);
	bool DeleteInterpreter (OBJHANDLE hV, oapi::UInt32 idx);
	bool DeleteInterpreters (OBJHANDLE hV);
	void DeleteList ();
	VesselInterp *FindVesselInterp (OBJHANDLE hV);
	Environment *FindInterpreter (OBJHANDLE hV, oapi::UInt32 idx);
	oapi::UInt32 InterpreterCount (OBJHANDLE hV);
};

#endif // !__MFDINTERPRETER_H