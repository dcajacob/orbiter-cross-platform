// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "ConfigFile.h"
#include "Production/Text.h"
#include <cstring>
#ifndef _WIN32
#include <strings.h>
#endif
using namespace std;
namespace {
int CompareKey(const char *a, const char *b) {
#ifdef _WIN32
    return _stricmp(a,b);
#else
    return strcasecmp(a,b);
#endif
}
}

char *trim_string (char *cbuf)
{
	char *c;

	// strip comments starting with ';'
	for (c = cbuf; *c; c++) {
		if (*c == ';') {
			*c = '\0';
			break;
		}
	}
	// Text streams on POSIX retain CR in Windows-authored configuration files.
	if (c > cbuf && c[-1] == '\r') *--c = '\0';
	// Strip trailing white space without stepping before the buffer.
	while (c > cbuf && (c[-1] == ' ' || c[-1] == '\t')) *--c = '\0';
	// skip leading white space
	for (c = cbuf; *c; c++)
		if (*c != ' ' && *c != '\t') return c;

	// should never get here
	return c;
}

bool GetItemString (istream &is, const char *label, char *val)
{
	char cbuf[512], *cl, *cv;
	int i;

	is.clear();
	is.seekg (0, ios::beg);

	while (is.getline (cbuf, 512)) {
		cl = trim_string(cbuf);
		if (!CompareKey(cl, "END_PARSE")) return false;
		
		for (i = 0; cl[i] && cl[i] != '='; i++);
		cv = (cl[i] ? cl+(i+1) : cl+i);
		for (cl[i--] = '\0'; i >= 0 && (cl[i] == ' ' || cl[i] == '\t'); i--)
			cl[i] = '\0';
		if (!CompareKey (cl, label)) {
			while (*cv == ' ' || *cv == '\t') cv++;
			if (*cv) {
				strcpy (val, cv);
				return true;
			} else {
				return false;
			}
		}
	}

	is.clear();
	return false;
}


bool GetItemReal (istream &is, const char *label, double &val)
{
	char g_cbuf[1024];
	if (!GetItemString (is, label, g_cbuf)) return false;
	return (sscanf (g_cbuf, "%lf", &val) == 1);
}


bool GetItemVector (istream &is, const char *label, Vector &val)
{
	char g_cbuf[1024];
	double x, y, z;
	if (!GetItemString (is, label, g_cbuf)) return false;
	if (sscanf (g_cbuf, "%lf%lf%lf", &x, &y, &z) != 3) return false;
	val.Set (x,y,z);
	return true;
}


bool FindLine (istream &is, const char *line)
{
	char g_cbuf[1024];
	const int g_buflen = sizeof(g_cbuf);
	bool ok = false;
	is.seekg (0); // rewind stream
	if (is.good()) {
		int len = strlen(line);
		for (;;) {
			if (!is.getline (g_cbuf, g_buflen)) {
				if (is.eof()) break;               // EOF
				else is.clear();                   // heal stream to continue after truncation error
			}
			if (!orbiter::production::ComparePrefix (g_cbuf, line, len)) {  // found string
				ok = true;
				break;
			}
		}
	}
	if (!ok) { // reset stream
		is.clear();
		is.seekg(0);
	}
	return ok;
}

