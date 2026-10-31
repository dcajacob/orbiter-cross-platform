// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_CONFIG_FILE_H
#define ORBITER_CONFIG_FILE_H
#include <istream>

// Existing configuration primitives, shared without application/SDK headers.
char *trim_string(char *buffer);
bool GetItemString(std::istream &stream, const char *label, char *value);
#endif
