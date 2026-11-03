// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#include <iostream>
#include <fstream>
#include <stdio.h>
#include <time.h>
#include <filesystem>
#include <cstring>
#include <cstdlib>
#include <string>
#ifdef _WIN32
#include "Mesh.h"
#else
#include "Production/MeshData.h"
#include <strings.h>
#endif

using namespace std;

struct Param {
	std::string meshname;
	std::string outname;
	std::string suffix;
	bool outlua;
};

struct ResourceCounts {
    std::size_t groups, materials, textures;
};

static bool startsWith(const char* line, const char* keyword, std::size_t length)
{
#ifdef _WIN32
    return _strnicmp(line, keyword, length) == 0;
#else
    return strncasecmp(line, keyword, length) == 0;
#endif
}

void PrintUsage()
{
	std::cout << "Scans a mesh file and generates a header file containing mesh group\n";
	std::cout << "identifiers.\n\n";
	std::cout << "Usage: meshc /I <meshfile> /O <header file> /P <suffix> [/L]\n";
	std::cout << "  <meshfile>:    Orbiter mesh file to be scanned\n";
	std::cout << "  <header file>: Output header file name\n";
	std::cout << "  <suffix>:      Variable name suffix\n";
	std::cout << "  /L:            Optional argument, output a Lua file when provided\n\n";
	std::cout << "Any mandatory parameters not provided on the command line are queried interactively.\n\n";
}

void ParseError()
{
	std::cerr << "Error parsing command line." << std::endl;
	std::cerr << "Terminating." << std::endl;
	exit(1);
}

void ParseArgs(int argc, char *argv[], Param *param)
{
	param->meshname.clear();
	param->outname.clear();
	param->suffix.clear();
	param->outlua = false;

	for (int i = 1; i < argc; i++) {
		char *a = argv[i];

		if (a[0] != '/')
			ParseError();
		switch (a[1]) {
		case 'I':
			if (i == argc-1)
				ParseError();
			param->meshname = argv[++i];
			break;
		case 'O':
			if (i == argc - 1)
				ParseError();
			param->outname = argv[++i];
			break;
		case 'P':
			if (i == argc - 1)
				ParseError();
			param->suffix = argv[++i];
			break;
		case 'L':
			param->outlua = true;
			break;
		case 'H':
			PrintUsage();
			exit(0);
		default:
			ParseError();
		}
	}
}

static void outC(const Param& param, const ResourceCounts& counts)
{
	char cbuf[256], label[256];
	struct tm* now;
	time_t aclock;
	time(&aclock);
	now = localtime(&aclock);

	ofstream ofs(param.outname);
	ofs.exceptions(ios::badbit | ios::failbit);
	ofs << "// ========================================================\n";
	ofs << "// Mesh resource file for " << param.meshname << endl;
	ofs << "// Generated with meshc on " << asctime(now);
	ofs << "// ========================================================\n";

	ofs << "\n// Number of mesh groups:\n";
	ofs << "#define NGRP" << param.suffix << " " << counts.groups << endl;

	ofs << "\n// Number of materials:\n";
	ofs << "#define NMAT" << param.suffix << " " << counts.materials << endl;

	ofs << "\n// Number of textures:\n";
	ofs << "#define NTEX" << param.suffix << " " << counts.textures << endl;

	ifstream ifs(param.meshname);
	int grp = 0;
	bool havelabel = false;
	while (ifs.getline(cbuf, 256)) {
		if (startsWith(cbuf, "GEOM", 4))
			grp++;
		else if (startsWith(cbuf, "LABEL", 5)) {
			if (!havelabel) {
				ofs << "\n// Named mesh groups:\n";
				havelabel = true;
			}
			sscanf(cbuf + 5, "%250s", label);
			ofs << "#define GRP_" << label << param.suffix << ' ' << grp << endl;
		}
	}
	ifs.close();
}
static void outLua(const Param& param, const ResourceCounts& counts)
{
	char cbuf[256], label[256];
	struct tm* now;
	time_t aclock;
	time(&aclock);
	now = localtime(&aclock);

	ofstream ofs(param.outname);
	ofs.exceptions(ios::badbit | ios::failbit);
	ofs << "-----------------------------------------------------------\n";
	ofs << "-- Mesh resource file for " << param.meshname << endl;
	ofs << "-- Generated with meshc on " << asctime(now);
	ofs << "-- example usage:\n";
	ofs << "-- local meshres = require 'meshres.lua'\n";
	ofs << "-- print(meshres.NTEX)\n";
	ofs << "-----------------------------------------------------------\n";
	ofs << "local module={GRP={}}\n";

	ofs << "\n-- Number of mesh groups:\n";
	ofs << "module.NGRP" << param.suffix << " = " << counts.groups << endl;

	ofs << "\n-- Number of materials:\n";
	ofs << "module.NMAT" << param.suffix << " = " << counts.materials << endl;

	ofs << "\n-- Number of textures:\n";
	ofs << "module.NTEX" << param.suffix << " = " << counts.textures << endl;

	ifstream ifs(param.meshname);
	int grp = 0;
	bool havelabel = false;
	while (ifs.getline(cbuf, 256)) {
		if (startsWith(cbuf, "GEOM", 4))
			grp++;
		else if (startsWith(cbuf, "LABEL", 5)) {
			if (!havelabel) {
				ofs << "\n-- Named mesh groups:\n";
				havelabel = true;
			}
			sscanf(cbuf + 5, "%250s", label);
			ofs << "module.GRP." << label << param.suffix << " = " << grp << endl;
		}
	}
	ofs << "\nreturn module\n";
	ifs.close();
}

int main (int argc, char *argv[]) try
{
	Param param;

	cout << "+-----------------------------------------------------------------------+\n";
	cout << "|                   meshc: Mesh compiler for ORBITER                    |\n";
	cout << "|        Build: " << __DATE__ << "      (c) 2001-2026 Martin Schweiger         |\n";
	cout << "+-----------------------------------------------------------------------+\n\n";

	ParseArgs(argc, argv, &param);

	if (param.meshname.empty()) {
		cout << "Mesh file name:\n";
		cout << ">> ";
		cin >> param.meshname;
		cout << endl;
	}

	if (param.suffix.empty()) {
		cout << "Variable suffix ('-' for none):\n>> ";
		cin >> param.suffix;
		cout << endl;
	}
	if (param.suffix == "-") param.suffix.clear();

	if (param.outname.empty()) {
		cout << "Output file name ('-' for default meshres.h):\n>> ";
		cin >> param.outname;
		cout << endl;
	}
	if (param.outname == "-") param.outname = "meshres.h";

    cout << "Current directory is " << std::filesystem::current_path().string() << endl;
    cout << "Reading mesh from " << param.meshname << endl;
    ifstream ifs(param.meshname);
    ResourceCounts counts;
#ifdef _WIN32
    Mesh mesh;
    ifs >> mesh;
    counts = {static_cast<std::size_t>(mesh.nGroup()), mesh.nMaterial(), mesh.nTexture()};
#else
    const auto mesh = orbiter::production::LoadMeshData(ifs);
    counts = {mesh.groups.size(), mesh.materials.size(), mesh.textures.size()};
#endif
    if (!ifs) {
        cerr << "Error reading mesh file." << endl;
        return 1;
    }
    if (!counts.groups) cout << "Warning: mesh contains no groups." << endl;

	if(param.outlua)
		outLua(param, counts);
	else
		outC(param, counts);

	cout << "Wrote mesh parameters to " << param.outname << endl << endl;

	return 0;
} catch (const std::exception& error) {
    cerr << "meshc: " << error.what() << endl;
    return 1;
}
