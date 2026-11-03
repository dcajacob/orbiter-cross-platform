// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#define INTERPRETER_IMPLEMENTATION
#include "Interpreter.h"

void Interpreter::WaitExec (oapi::UInt32 timeout)
{
	// Called by orbiter thread or interpreter thread to wait its turn
	// Orbiter waits for the script for 1 second to return
#ifdef _WIN32
	WaitForSingleObject (hWaitMutex, timeout); // wait for synchronisation mutex
	WaitForSingleObject (hExecMutex, timeout); // wait for execution mutex
	ReleaseMutex (hWaitMutex);              // release synchronisation mutex
#else
	execution.Wait(timeout);
#endif
}

void Interpreter::EndExec ()
{
	// called by orbiter thread or interpreter thread to hand over control
#ifdef _WIN32
	ReleaseMutex (hExecMutex);
#else
	execution.Release();
#endif
}

void Interpreter::frameskip (lua_State *L)
{
	if (status != 1) {
		EndExec();
		WaitExec();
	}
	// A shutdown can be requested while proc.skip is waiting for its turn.
	if (status == 1) {
		lua_pushboolean(L, 1);
		lua_setfield (L, LUA_GLOBALSINDEX, "wait_exit");
	}
}

int Interpreter::ProcessChunk (const char *chunk, int n)
{
	WaitExec();
	int res = RunChunk (chunk, n);
	EndExec();
	return res;
}
