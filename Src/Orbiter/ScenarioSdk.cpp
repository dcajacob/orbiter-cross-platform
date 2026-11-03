// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifdef _WIN32
#define OAPI_IMPLEMENTATION
#include "Orbitersdk.h"
#else
#include "NativeVesselAPI.h"
#endif
#include "Config.h"
#include "ConfigFile.h"
#include "Production/Text.h"
#include <fstream>
#include <iomanip>
#include <sstream>
using std::ifstream;
using std::ofstream;
using std::endl;

namespace {
// Floating point output stream formatter
struct FltFormatter
{
	int precision;
	double value;
	FltFormatter (int precision, double value);
	friend std::ostream& operator<< (std::ostream& os, const FltFormatter& v);
};

struct FltFormat
{
	int precision;
	FltFormat (int precision = 6);
	FltFormatter operator() (double value) const;
};

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
}

void oapiWriteScenario_string (FILEHANDLE file, char *item, char *string)
{
	ofstream &ofs = *(ofstream*)file;
	ofs << "  " << item << ' ' << string << endl;
}

void oapiWriteScenario_int (FILEHANDLE file, char *item, int i)
{
	ofstream &ofs = *(ofstream*)file;
	ofs << "  " << item << ' ' << i << endl;
}

void oapiWriteScenario_float (FILEHANDLE file, char *item, double d)
{
	ofstream &ofs = *(ofstream*)file;
	FltFormat f{ 6 }; // default precision: 6
	ofs << "  " << item << ' ' << f(d) << endl;
}

void oapiWriteScenario_vec (FILEHANDLE file, char *item, const VECTOR3 &vec)
{
	ofstream &ofs = *(ofstream*)file;
	FltFormat f{ 6 }; // default precision: 6
	ofs << "  " << item << ' ' << f(vec.x) << ' ' << f(vec.y) << ' ' << f(vec.z) << endl;
}

bool oapiReadScenario_nextline (FILEHANDLE file, char *&line)
{
	ifstream &ifs = *(ifstream*)file;
	char *cbuf = readline(ifs);
	if (!cbuf) return false;
	line = trim_string (cbuf);
	if (!orbiter::production::CompareText(line, "END")) return false;
	return true;
}

void oapiWriteItem_string (FILEHANDLE file, char *item, char *string)
{
	ofstream &ofs = *(ofstream*)file;
	ofs << item << " = " << string << endl;
}

void oapiWriteItem_float (FILEHANDLE file, char *item, double d)
{
	ofstream &ofs = *(ofstream*)file;
	ofs << item << " = " << d << endl;
}

void oapiWriteItem_int (FILEHANDLE file, char *item, int i)
{
	ofstream &ofs = *(ofstream*)file;
	ofs << item << " = " << i << endl;
}

void oapiWriteItem_bool (FILEHANDLE file, char *item, bool b)
{
	ofstream &ofs = *(ofstream*)file;
	ofs << item << " = " << (b ? "TRUE":"FALSE") << endl;
}

void oapiWriteItem_vec (FILEHANDLE file, char *item, const VECTOR3 &vec)
{
	ofstream &ofs = *(ofstream*)file;
	ofs << item << " = " << vec.x << ' ' << vec.y << ' ' << vec.z << endl;
}

bool oapiReadItem_string (FILEHANDLE f, char *item, char *string)
{
	return GetItemString (*(ifstream*)f, item, string);
}

bool oapiReadItem_float (FILEHANDLE f, char *item, double &val)
{
	return GetItemReal (*(ifstream*)f, item, val);
}

bool oapiReadItem_int (FILEHANDLE f, char *item, int &val)
{
	return GetItemInt (*(ifstream*)f, item, val);
}

bool oapiReadItem_bool (FILEHANDLE f, char *item, bool &val)
{
	return GetItemBool (*(ifstream*)f, item, val);
}

bool oapiReadItem_vec (FILEHANDLE f, char *item, VECTOR3 &val)
{
	Vector vec;
	bool res = GetItemVector (*(ifstream*)f, item, vec);
	val.x = vec.x;
	val.y = vec.y;
	val.z = vec.z;
	return res;
}
