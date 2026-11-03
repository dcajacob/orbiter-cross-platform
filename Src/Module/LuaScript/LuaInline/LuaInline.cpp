// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ==============================================================
//           ORBITER MODULE: LUA Inline Interpreter
//                  Part of the ORBITER SDK
//            Copyright (C) 2007-2026 Martin Schweiger
//                   All rights reserved
//
// LuaInline.cpp
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

#define STRICT
#define ORBITER_MODULE
#include "orbitersdk.h"
#include "LuaInline.h"

// ==============================================================
// class InterpreterList: implementation

InterpreterList::InterpreterList (HINSTANCE hDLL): Module (hDLL)
{
	list = nullptr;
	nlist = nbuf = 0;
}

InterpreterList::~InterpreterList ()
{
	while (nlist) DelInterpreter(list[0]);
	delete []list;
}

void InterpreterList::clbkSimulationStart (RenderMode mode)
{
}

void InterpreterList::clbkSimulationEnd ()
{
	while (nlist) DelInterpreter(list[0]);
}

void InterpreterList::clbkPostStep (double simt, double simdt, double mjd)
{
	DWORD i;
	for (i = 0; i < nlist; i++) // prune all finished interpreters
		if (!list[i]->interp) DelInterpreter (list[i--]);

	for (i = 0; i < nlist; i++) { // let the interpreter do some work
		if (list[i]->interp->IsBusy() || list[i]->cmd || list[i]->interp->nJobs()) {
			list[i]->Advance();
		}
	}
}

void InterpreterList::clbkDeleteVessel (OBJHANDLE hVessel)
{
	Interpreter::DeleteVessel(hVessel);
}

InterpreterList::Environment *InterpreterList::AddInterpreter ()
{
	if (nlist == nbuf) { // increase buffer size
		Environment **tmp = new Environment*[nbuf + 16];
		if (nlist) {
			memcpy (tmp, list, nlist*sizeof(Environment*));
			delete []list;
		}
		list = tmp;
		nbuf += 16;
	}

	Environment *env = new Environment;
	list[nlist++] = env;
	return env;
}

int InterpreterList::DelInterpreter (InterpreterList::Environment *env)
{
	// remove interpreter from list
	DWORD i, j;
	for (i = 0; i < nlist; i++)
		if (list[i] == env) break;
	if (i == nlist) return 2; // interpreter not found
	for (j = i+1; j < nlist; j++)
		list[j-1] = list[j];
	nlist--;

	// delete interpreter
	delete env;
	return 0;
}

// ==============================================================
// API interface

static InterpreterList *g_IList = nullptr;

DLLCLBK void InitModule (HINSTANCE hDLL)
{
	g_IList = new InterpreterList (hDLL);
	oapiRegisterModule (g_IList);
}

DLLCLBK void ExitModule (HINSTANCE hDLL)
{
	if (g_IList) {
		delete g_IList;
		g_IList = nullptr;
	}
}

// interpreter-specific callback functions
DLLCLBK INTERPRETERHANDLE opcNewInterpreter ()
{
	if (g_IList) {
		InterpreterList::Environment *env = g_IList->AddInterpreter();
		return (INTERPRETERHANDLE)env;
	} else {
		return NULL;
	}
}

DLLCLBK int opcDelInterpreter (INTERPRETERHANDLE hInterp)
{
	if (g_IList)
		return g_IList->DelInterpreter ((InterpreterList::Environment*)hInterp);
	else
		return 1;
}

DLLCLBK INTERPRETERHANDLE opcRunInterpreter (const char *cmd)
{
	if (g_IList) {
		InterpreterList::Environment *env = g_IList->AddInterpreter();
		env->cmd = new char[strlen(cmd)+10];
		sprintf (env->cmd, "run('%s')", cmd);
		return (INTERPRETERHANDLE)env;
	} else {
		return NULL;
	}
}

DLLCLBK bool opcAsyncScriptCmd (INTERPRETERHANDLE hInterp, const char *cmd)
{
	InterpreterList::Environment *env = (InterpreterList::Environment*)hInterp;
	char *str;
	if (env->cmd) { // command still waiting: append new command
		str = new char[strlen(env->cmd)+strlen(cmd)+2];
		strcpy(str,env->cmd);
		strcat(str,";");
		strcat(str,cmd);
		char *tmp = env->cmd;
		env->cmd = str;
		delete []tmp;
	} else {
		str = new char[strlen(cmd)+1];
		strcpy (str, cmd);
		env->cmd = str;
	}
	return true;
}

DLLCLBK bool opcExecScriptCmd (INTERPRETERHANDLE hInterp, const char *cmd)
{
	InterpreterList::Environment *env = (InterpreterList::Environment*)hInterp;
	char *str = new char[strlen(cmd)+1];
	char *cmd_async = 0;
	strcpy (str, cmd);
	if (env->cmd) // asynchronous request is waiting
		cmd_async = env->cmd;
	env->cmd = str;
	while (env->cmd) {
		// wait until command has been executed
		env->Advance();
	}
	if (cmd_async) // restore the asynchronous request
		env->cmd = cmd_async;
	return true;
}

DLLCLBK lua_State *opcGetLua (INTERPRETERHANDLE hInterp)
{
	InterpreterList::Environment *env = (InterpreterList::Environment*)hInterp;
	return env->interp->GetState();
}

