// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef __PSYS_H
#define __PSYS_H
#include "PsysCore.h"
#ifdef _WIN32
// Preserve the existing application's umbrella includes. The shared force
// implementation includes PsysCore.h directly and needs no device/UI headers.
#include "Base.h"
#include "Star.h"
#include "Planet.h"
#include "Vessel.h"
#endif
#endif
