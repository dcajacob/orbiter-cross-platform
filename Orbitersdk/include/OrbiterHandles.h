// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_HANDLES_H
#define ORBITER_HANDLES_H

// Orbiter-owned opaque handles, independent of operating-system window handles.
/// \brief Handle for objects (vessels, stations, planets)
typedef void *OBJHANDLE;

/// \brief Handle for vessel superstructures
typedef void *SUPERVESSELHANDLE;

/// \brief Handle for visuals
typedef void *VISHANDLE;

/// \brief Handle for meshes
typedef void *MESHHANDLE;

/// \brief Handle for graphics-client-specific meshes
typedef int *DEVMESHHANDLE;
//struct DEVMESHHANDLE {
//	DEVMESHHANDLE() { hMesh = NULL; }
//	DEVMESHHANDLE(MESHHANDLE h) { hMesh = h; }
//	DWORD id;
//	MESHHANDLE hMesh;
//	operator int() { return (int)hMesh; }
//};

/// \brief Handle for bitmap surfaces and textures (panels and panel items)
typedef void *SURFHANDLE;

/// \brief Handle for 2D instrument panels
typedef void *PANELHANDLE;

/// \brief Handle for file streams
typedef void *FILEHANDLE;

/// \brief Handle for script interpreters
typedef void *INTERPRETERHANDLE;

/// \brief Handle for thrusters
typedef void *THRUSTER_HANDLE;

/// \brief Handle for logical thruster groups
typedef void *THGROUP_HANDLE;

/// \brief Propellant resource handle
typedef void *PROPELLANT_HANDLE;

/// \brief Handle for particle streams
typedef void *PSTREAM_HANDLE;

/// \brief Handle for vessel docking ports
typedef void *DOCKHANDLE;

/// \brief Handle vor vessel passive attachment points
typedef void *ATTACHMENTHANDLE;

/// \brief Handle for vessel airfoils
typedef void *AIRFOILHANDLE;

/// \brief Handle for vessel aerodynamic control surfaces
typedef void *CTRLSURFHANDLE;

/// \brief Handle for a navigation radio transmitter (VOR, ILS, IDS, XPDR)
typedef void *NAVHANDLE;

/// \brief Handle for animation components
typedef void *ANIMATIONCOMPONENT_HANDLE;

/// \brief Handle for custom items added to Launchpad "Extra" list
typedef void *LAUNCHPADITEM_HANDLE;

/// \brief Handle for onscreen annotation objects
typedef void *NOTEHANDLE;

/// \brief Handle for elevation query managers
typedef void *ELEVHANDLE;

#endif
