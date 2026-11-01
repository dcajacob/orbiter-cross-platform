// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_CAMERA_DATA_H
#define ORBITER_CAMERA_DATA_H
#include "OrbiterHandles.h"
#define COCKPIT_GENERIC          1
#define COCKPIT_PANELS           2
#define COCKPIT_VIRTUAL          3

#define CAM_COCKPIT              0
#define CAM_TARGETRELATIVE       1
#define CAM_ABSDIRECTION         2
#define CAM_GLOBALFRAME          3
#define CAM_TARGETTOOBJECT       4
#define CAM_TARGETFROMOBJECT     5
#define CAM_GROUNDOBSERVER       6

class OAPIFUNC CameraMode {
friend class Camera;
public:
	CameraMode ();
	static CameraMode *Create (char *str);
	virtual void Init (char *str) = 0;
	virtual void Store (char *str) = 0;
	enum Mode { CM_COCKPIT, CM_TRACK, CM_GROUND };
	OBJHANDLE GetTarget() const { return target; }
	virtual Mode GetMode() const = 0;
	virtual void GetDescr (char *str, int len) = 0;
	void SetTarget (OBJHANDLE hTgt);
	void SetFOV (double FOV);
	double GetFOV () const { return fov; }

protected:
	OBJHANDLE target;  // camera target
	double fov;        // field of view [deg]
};

class OAPIFUNC CameraMode_Cockpit: public CameraMode {
public:
	CameraMode_Cockpit ();
	void Init (char* str = 0);
	void Store (char *str);
	Mode GetMode() const { return CM_COCKPIT; }
	void GetDescr (char *str, int len);
	enum CockpitMode { CM_CURRENT, CM_GENERIC, CM_PANEL2D, CM_VC };
	CockpitMode GetCockpitMode () const { return cmode; }
	int GetPosition () const { return pos; }
	int GetLeaning() const { return lean; }
	bool GetLeaningSmooth() const { return lean_smooth; }

protected:
	CockpitMode cmode;
	int pos;
	int lean;
	bool lean_smooth;
};

class OAPIFUNC CameraMode_Track: public CameraMode {
public:
	CameraMode_Track ();
	void Init (char *str);
	void Store (char *str);
	Mode GetMode() const { return CM_TRACK; }
	void GetDescr (char *str, int len);
	enum TrackMode { TM_CURRENT, TM_RELATIVE, TM_ABSDIR, TM_GLOBAL, TM_TARGETTOREF, TM_TARGETFROMREF };
	TrackMode GetTrackMode () const { return tmode; }
	void SetTrackMode (TrackMode trackmode, OBJHANDLE refobj = 0);
	OBJHANDLE GetRef() const { return ref; }
	void SetPosition (double rd, double ph, double th);
	void GetPosition (double *rd, double *ph, double *th) const;

protected:
	TrackMode tmode;   // camera track mode
	double reldist;    // distance camera-targets (in units of target size)
	double phi, theta; // camera angle [rad]
	OBJHANDLE ref;     // reference object (for TM_TARGETTOREF and TM_TARGETFROMREF only)
};

class OAPIFUNC CameraMode_Ground: public CameraMode {
public:
	CameraMode_Ground ();
	void Init (char *str);
	void Store (char *str);
	Mode GetMode () const { return CM_GROUND; }
	void GetDescr (char *str, int len);
	void SetPosition (double longitude, double latitude, double altitude, OBJHANDLE hRef = 0);
	void GetPosition (double *longitude, double *latitude, double *altitude, OBJHANDLE *hRef) const;
	void SetOrientation (double ph, double th);
	void GetOrientation (double *ph, double *th) const;
	bool GetTgtLock () const { return tgtlock; }
	bool GetAltMode () const { return alt_above_ground; }
	OBJHANDLE GetRef() const { return ref; }

protected:
	OBJHANDLE ref;
	double lng, lat;       // camera position on the ground [rad]
	double alt;            // camera height over ground [m]
	double phi, theta;     // camera direction (free mode only)
	bool alt_above_ground; // true: alt refers to altitude above local terrain elevation; false: alt refers to mean planet radius
	bool tgtlock;          // flag for target lock/free mode
};



#endif
