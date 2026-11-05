// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#include "MfdInterpreter.h"
#ifdef _WIN32
#include <process.h>
#else
#include <memory>
#include "Production/NativeRenderApi.h"
#endif

// ==============================================================
// MFD interpreter class implementation

MFDInterpreter::MFDInterpreter (): Interpreter ()
{
	is_term = true;
	lineFirst = lineLast = NULL;
	nline = 0;
}

MFDInterpreter::~MFDInterpreter ()
{
    term_clear();
}

void MFDInterpreter::SetSelf (OBJHANDLE hV)
{
    VESSEL *vessel = oapiGetVesselInterface(hV);
    // Use the SDK's canonical userdata factory, which also registers this
    // interface for the interpreter's existing vessel-validity checks.
    lua_pushvessel(L, vessel);
    lua_setfield(L, LUA_GLOBALSINDEX, "V");
    InitialiseVessel(L, vessel);
}

void MFDInterpreter::LoadAPI ()
{
	Interpreter::LoadAPI();

	static const struct luaL_reg termLib [] = {
		{"out", termOut},
		{"clear", termClear},
		//{"lineup", termLineUp},
		{"SetVerbosity", termSetVerbosity},
		{NULL, NULL}
	};
	luaL_openlib (L, "term", termLib, 0);

	// also replace built-in print so it works as expected in the MFD
	static const struct luaL_Reg printlib[] = {
		{"print", termOut},
		{NULL, NULL}
	};
	lua_getglobal(L, "_G");
	luaL_register(L, NULL, printlib);
}

void MFDInterpreter::term_strout (const char *str, bool iserr)
{
	if (strchr (str, '\n')) {
		char *cbuf = new char[strlen(str)+1];
		strcpy (cbuf, str);
		char *s = strtok (cbuf, "\n");
		while (s) {
			AddLine (s, iserr ? 0x0000FF:0x00FF00);
			s = strtok (NULL, "\n");
		}
		delete []cbuf;
	} else AddLine (str, iserr ? 0x0000FF:0x00FF00);
}

int MFDInterpreter::termOut (lua_State *L)
{
	Interpreter *interp = GetInterpreter (L);
	interp->term_out (L);
	return 0;
}

void MFDInterpreter::term_clear ()
{
	// Clean terminal buffer
	while (lineFirst)
	{
		LineSpec *tmp = lineFirst;
		lineFirst = lineFirst->next;
		delete tmp;
	}
	// Set parameter for a 'clean' terminal
	lineFirst = lineLast = NULL;
	nline = 0;
}

int MFDInterpreter::termClear (lua_State *L)
{
	Interpreter *interp = GetInterpreter(L);
	interp->term_clear();
	return 0;
}

int MFDInterpreter::termSetVerbosity (lua_State *L)
{
	Interpreter *interp = GetInterpreter (L);
	int level = lua_tointeger (L, -1);
	interp->term_setverbosity (level);
	return 0;
}

void MFDInterpreter::AddLine (const char *line, oapi::UInt32 col)
{
	LineSpec *ls = new LineSpec;
	strncpy (ls->buf, line, NCHAR);
	ls->buf[NCHAR-1] = '\0';
	ls->col = col;
	ls->prev = lineLast;
	ls->next = NULL;
	if (lineLast) lineLast->next = ls;
	lineLast = ls;
	if (!lineFirst) lineFirst = ls;
	if (++nline > NLINE) {   // max line buffer size reached: drop first line
		LineSpec *tmp = lineFirst;
		lineFirst = lineFirst->next;
		delete tmp;
		nline--;
	}
}


// ==============================================================
// class InterpreterList::Environment: implementation

InterpreterList::Environment::Environment (OBJHANDLE hV)
{
	cmd[0] = '\0';
	interp = CreateInterpreter (hV);
}

InterpreterList::Environment::~Environment()
{
	if (interp) {
#ifdef _WIN32
		if (hThread) {
			TerminateThread (hThread, 0);
			CloseHandle (hThread);
		}
#else
        // The simulator owns execution while deleting a terminal page. Wake
        // its worker cooperatively before destroying the Lua state or vessel.
        interp->Terminate();
        interp->EndExec();
        if (thread.joinable()) thread.join();
#endif
		delete interp;
	}
}

MFDInterpreter *InterpreterList::Environment::CreateInterpreter (OBJHANDLE hV)
{
#ifdef _WIN32
	unsigned int id;
	interp = new MFDInterpreter ();
	interp->Initialise();
	interp->SetSelf (hV);
	hThread = (HANDLE)_beginthreadex (NULL, 4096, &InterpreterThreadProc, this, 0, &id);
	return interp;
#else
    auto candidate = std::make_unique<MFDInterpreter>();
    candidate->Initialise();
    candidate->SetSelf(hV);
    interp = candidate.get();
    thread = std::thread(&Environment::Run, this);
    return candidate.release();
#endif
}

#ifdef _WIN32
// Interpreter thread function
unsigned int WINAPI InterpreterList::Environment::InterpreterThreadProc (LPVOID context)
{
	InterpreterList::Environment *env = (InterpreterList::Environment*)context;
	MFDInterpreter *interp = (MFDInterpreter*)env->interp;

	// interpreter loop
	for (;;) {
		interp->WaitExec(); // wait for execution permission
		if (interp->Status() == 1) break; // close thread requested
		interp->RunChunk (env->cmd, strlen (env->cmd)); // run command from buffer
		if (interp->Status() == 1) break;
		env->cmd[0] = '\0'; // free buffer
		interp->EndExec();  // return control
	}
	interp->EndExec();  // release mutex (is this necessary?)
	_endthreadex(0);
	return 0;
}

#else
void InterpreterList::Environment::Advance()
{
    if (failure) std::rethrow_exception(failure);
    interp->EndExec();
    interp->WaitExec();
    if (failure) std::rethrow_exception(failure);
}

void InterpreterList::Environment::Run()
{
    for (;;) {
        interp->WaitExec();
        if (interp->Status() == 1) break;
        try {
            interp->RunChunk(cmd, static_cast<int>(std::strlen(cmd)));
            cmd[0] = '\0';
        } catch (...) {
            failure = std::current_exception();
            break;
        }
        if (interp->Status() == 1) break;
        interp->EndExec();
    }
    interp->EndExec();
}
#endif

// ==============================================================
// Interpreter repository implementation

InterpreterList::InterpreterList ()
{
	nlist = nbuf = 0;
}

InterpreterList::~InterpreterList ()
{
	DeleteList();
}

void InterpreterList::Update (double simt, double simdt, double mjd)
{
	oapi::UInt32 i, j;
	for (i = 0; i < nlist; i++) {
		for (j = 0; j < list[i].nenv; j++) {
			Environment *env = list[i].env[j];
			if (env->interp->IsBusy() || env->cmd[0] || env->interp->nJobs()) { // let the interpreter do some work
#ifdef _WIN32
				env->interp->EndExec();
				env->interp->WaitExec();
#else
                env->Advance();
#endif
			}
			env->interp->PostStep (simt, simdt, mjd);
		}
	}
}

InterpreterList::Environment *InterpreterList::AddInterpreter (OBJHANDLE hV)
{
#ifndef _WIN32
    // Finish fallible Lua setup before publishing a vessel/page or its array.
    auto pending = std::make_unique<Environment>(hV);
#endif
	VesselInterp *vi = FindVesselInterp (hV);

	if (!vi) { // no interpreters defined for this vessel yet
		if (nlist == nbuf) { // increase buffer size
			VesselInterp *tmp = new VesselInterp[nbuf+16];
			if (nbuf) {
				memcpy (tmp, list, nbuf*sizeof(VesselInterp));
				delete []list;
			}
			list = tmp;
			nbuf += 16;
		}
		vi = list + nlist++;
		vi->hVessel = hV;
		vi->nenv = 0;
	}

	// add the new interpreter to the vessel's interpreter list
	Environment **tmp = new Environment*[vi->nenv+1];
	if (vi->nenv) {
		memcpy (tmp, vi->env, vi->nenv*sizeof(Environment*));
		delete []vi->env;
	}
	vi->env = tmp;

#ifdef _WIN32
	Environment *env = new Environment (hV);
#else
    Environment *env = pending.release();
#endif
	vi->env[vi->nenv++] = env;
	
	return env;
}

bool InterpreterList::DeleteInterpreter (OBJHANDLE hV, oapi::UInt32 idx)
{
	VesselInterp *vi = FindVesselInterp (hV);
	if (!vi || idx >= vi->nenv) return false;
	if (vi->nenv <= 1) return false; // can't delete the last interpreter

	Environment *env = vi->env[idx];
	delete env;

	Environment **tmp = NULL;
	if (vi->nenv > 1) {
		oapi::UInt32 i, j;
		tmp = new Environment*[vi->nenv-1];
		for (i = j = 0; i < vi->nenv; i++)
			if (i != idx) tmp[j++] = vi->env[i];
	}
	delete []vi->env;
	vi->env = tmp;
	vi->nenv--;
	return true;
}

bool InterpreterList::DeleteInterpreters (OBJHANDLE hV)
{
	VesselInterp *vi = FindVesselInterp (hV);
	if (!vi) return false;

	oapi::UInt32 i;
	for (i = 0; i < vi->nenv; i++) {
		Environment *env = vi->env[i];
		delete env;
	}
	if (vi->nenv) {
		delete []vi->env;
		vi->env = 0;
		vi->nenv = 0;
	}
#ifndef _WIN32
    vi->hVessel = nullptr;
#endif
	return true;
}

void InterpreterList::DeleteList ()
{
	oapi::UInt32 i, j;
	for (j = 0; j < nlist; j++) {
		VesselInterp *vi = list+j;
		for (i = 0; i < vi->nenv; i++) {
			Environment *env = vi->env[i];
			delete env;
		}
		if (vi->nenv) delete []vi->env;
	}
	if (nbuf) delete []list;
	nbuf = nlist = 0;
}

InterpreterList::VesselInterp *InterpreterList::FindVesselInterp (OBJHANDLE hV)
{
	oapi::UInt32 i;
	for (i = 0; i < nlist; i++)
		if (list[i].hVessel == hV) return list+i;
	return NULL;
}

InterpreterList::Environment *InterpreterList::FindInterpreter (OBJHANDLE hV, oapi::UInt32 idx)
{
	VesselInterp *vi = FindVesselInterp (hV);
	if (!vi) return NULL;
	return (vi->nenv > idx ? vi->env[idx] : NULL);
}

oapi::UInt32 InterpreterList::InterpreterCount (OBJHANDLE hV)
{
	VesselInterp *vi = FindVesselInterp (hV);
	return (vi ? vi->nenv : 0);
}
