// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_CONFIG_FILE_H
#define ORBITER_CONFIG_FILE_H
#include <istream>
#include "Vecmat.h"

// Existing configuration primitives, shared without application/SDK headers.
char *trim_string(char *buffer);
bool GetItemString(std::istream &stream, const char *label, char *value);
bool GetItemInt(std::istream &stream, const char *label, int &value);
bool GetItemBool(std::istream &stream, const char *label, bool &value);
bool GetItemReal(std::istream &stream, const char *label, double &value);
bool GetItemVector(std::istream &stream, const char *label, Vector &value);
bool FindLine(std::istream &stream, const char *line);
#endif
