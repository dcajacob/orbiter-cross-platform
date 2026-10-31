// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ==============================================================
//   ORBITER VISUALISATION PROJECT (OVP)
//   D3D7 Client module
// ==============================================================

// ==============================================================
// CelSphere.h
// Class OGLCelestialSphere (interface)
//
// This class is responsible for rendering the celestial sphere
// background (stars, constellations, grids, labels, etc.)
// ==============================================================

#ifndef ORBITER_OGL_CELSPHERE_H
#define ORBITER_OGL_CELSPHERE_H

#include "OGLClient.h"
#include "CelSphereAPI.h"
//#include "Baseobj.h"
#include <stdint.h>
#include "Shader.h"
#include "VertexBuffer.h"

class OGLCamera;
/**
 * \brief Rendering methods for the background celestial sphere.
 *
 * Loads star and constellation information from data bases and uses them to
 * celestial sphere background.
 */
class OGLCelestialSphere : public oapi::CelestialSphere {
public:
	OGLCelestialSphere ();
	~OGLCelestialSphere ();

	void RenderConstellations (VECTOR3 &col, OGLCamera *c);
	void RenderStars (OGLCamera *c, VECTOR3 &bgcol);
	void RenderEcliptic (OGLCamera *c);
	void Show();
protected:
	void LoadGpuConstellationLines ();
	void LoadGpuStars ();
	void CreateEcliptic ();
	bool EclDir2WindowPos(const VECTOR3 &dir, int &x, int &y) const override;
	// Load constellation line data from file

private:
	// Constellations
	size_t ncline;         // number of constellation lines
	Shader *m_constellationsShader;
	std::unique_ptr<VertexBuffer> m_constellationsVBO;
	std::unique_ptr<VertexArray> m_constellationsVAO;

	// Stars
	size_t nstars;         // number of constellation lines
	Shader *m_starsShader;
	std::unique_ptr<VertexBuffer> m_starsVBO;
	std::unique_ptr<VertexArray> m_starsVAO;

	// Ecliptic
	size_t necl;         // number of constellation lines
	Shader *m_eclShader;
	std::unique_ptr<VertexBuffer> m_eclVBO;
	std::unique_ptr<VertexArray> m_eclVAO;

	int lvlid[256];       // star brightness hash table
};

#endif // !ORBITER_OGL_CELSPHERE_H
