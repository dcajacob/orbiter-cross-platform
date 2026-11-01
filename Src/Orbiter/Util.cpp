// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#include "Util.h"
#include <shlobj.h>
#include <sstream>
#include <iomanip>
#include <unordered_map>
#include <algorithm>

double rand1()
{
	static double irmax = 1.0/(double)RAND_MAX;
	return (double)rand()*irmax;
}

bool MakePath (const char *fname)
{
	char cbuf[256];
	int i, len = strlen(fname);
	for (i = len; i > 0; i--)
		if (fname[i-1] == '\\') break;
	if (!i) return false;
	if (fname[0] != '\\' && fname[1] != ':') {
		GetCurrentDirectory (256, cbuf);
		len = strlen(cbuf);
		cbuf[len++] = '\\';
	} else len = 0;
	strncpy_s (cbuf+len, 256-len, fname, i);
	int res = SHCreateDirectoryEx (NULL, cbuf, NULL);
	return res == ERROR_SUCCESS;
}

bool iequal(const std::string& s1, const std::string& s2)
{
	unsigned int len = s1.size();
	if (s2.size() != len)
		return false;
	for (unsigned int i = 0; i < len; i++) {
		if (tolower(s1[i]) != tolower(s2[i]))
			return false;
	}
	return true;
}


RECT GetClientPos (HWND hWnd, HWND hChild)
{
	RECT r;
	POINT p;
	GetWindowRect (hChild, &r);
	p.x = r.left, p.y = r.top; ScreenToClient (hWnd, &p);
	r.left = p.x, r.top = p.y;
	p.x = r.right, p.y = r.bottom; ScreenToClient (hWnd, &p);
	r.right = p.x, r.bottom = p.y;
	return r;
}

void SetClientPos (HWND hWnd, HWND hChild, RECT &r)
{
	MoveWindow (hChild, r.left, r.top, r.right-r.left, r.bottom-r.top, true);
}


// ------------------------------------------------------------------------------
// Floating point output stream formatter
// ------------------------------------------------------------------------------

FltFormatter::FltFormatter (int precision, double value)
	: precision(precision)
	, value(value)
{
}

std::ostream& operator<< (std::ostream& os, const FltFormatter& v)
{
	std::stringstream ss;
	ss << std::setprecision(v.precision) << std::fixed << v.value;
	std::string str;
	ss.str().swap(str);
	str.resize(str.find_last_not_of("0") + 1);
//	if (str[str.length() - 1] == '.') { str.resize(str.length() - 1); } // results in "1"   instead of "1."
	if (str[str.length() - 1] == '.') { str.push_back('0'); }           // results in "1.0" instead of "1."
	os << str;
	return os;
}

FltFormat::FltFormat (int precision /* = 6 */)
	: precision(precision)
{
}

FltFormatter FltFormat::operator() (double value) const {
	return FltFormatter(precision, value);
}
