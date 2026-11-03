// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#pragma once
#include "Interpreter.h"
#include <exception>
#include <memory>
#ifndef _WIN32
#include <thread>
#endif

struct InlineEnvironment {
    InlineEnvironment();
    ~InlineEnvironment();
    InlineEnvironment(const InlineEnvironment&) = delete;
    InlineEnvironment& operator=(const InlineEnvironment&) = delete;

    void Advance();

    std::unique_ptr<Interpreter> interp;
    bool singleCmd = false;
    char *cmd = nullptr;

private:
    void Run();
    bool terminate = false;
    std::exception_ptr failure;
#ifdef _WIN32
    HANDLE thread = nullptr;
    static unsigned int WINAPI Start(void *context);
#else
    std::thread thread;
#endif
};
