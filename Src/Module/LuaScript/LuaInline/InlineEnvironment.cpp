// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "InlineEnvironment.h"
#include <cstring>
#include <stdexcept>
#include <utility>
#ifdef _WIN32
#include <process.h>
#endif

InlineEnvironment::InlineEnvironment()
    : interp(std::make_unique<Interpreter>())
{
    interp->Initialise();
#ifdef _WIN32
    unsigned id;
    thread = reinterpret_cast<HANDLE>(_beginthreadex(nullptr, 4096, Start, this, 0, &id));
    if (!thread) throw std::runtime_error("Could not start the Orbiter interpreter thread");
#else
    thread = std::thread(&InlineEnvironment::Run, this);
#endif
}

InlineEnvironment::~InlineEnvironment()
{
    terminate = true;
    interp->Terminate();
    interp->EndExec();
#ifdef _WIN32
    if (WaitForSingleObject(thread, 1000) != WAIT_OBJECT_0) {
        oapiWriteLog((char*)"LuaInline: timeout while waiting for interpreter thread");
        TerminateThread(thread, 0);
    }
    CloseHandle(thread);
#else
    thread.join();
#endif
    delete []cmd;
}

#ifdef _WIN32
unsigned int WINAPI InlineEnvironment::Start(void *context)
{
    static_cast<InlineEnvironment*>(context)->Run();
    return 0;
}
#endif

void InlineEnvironment::Advance()
{
    if (failure) std::rethrow_exception(failure);
    interp->EndExec();
    interp->WaitExec();
    if (failure) std::rethrow_exception(failure);
}

void InlineEnvironment::Run()
{
    for (;;) {
        interp->WaitExec();
        if (terminate) break;
        try {
            if (cmd) {
                interp->RunChunk(cmd, static_cast<int>(std::strlen(cmd)));
                delete []std::exchange(cmd, nullptr);
                if (singleCmd) break;
            } else {
                interp->RunChunk("", 0);
            }
        } catch (...) {
            failure = std::current_exception();
            break;
        }
        if (interp->Status() == 1) break;
        interp->EndExec();
    }
    interp->EndExec();
}
