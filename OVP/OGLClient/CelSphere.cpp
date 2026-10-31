// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ==============================================================
//   ORBITER VISUALISATION PROJECT (OVP)
//   D3D7 Client module
// ==============================================================

// ==============================================================
// CelSphere.cpp
// Class OGLCelestialSphere (implementation)
//
// This class is responsible for rendering the celestial sphere
// background (stars, constellations, grids, labels, etc.)
// ==============================================================

#include "glad.h"
#include "CelSphere.h"
#include "CelSphereAPI.h"
#include <vector>
#include <algorithm>
#include "OGLCamera.h"
#include "Renderer.h"
#include "Scene.h"

#define NSEG 64 // number of segments in celestial grid lines

using namespace oapi;

// ==============================================================
struct VERTEX_XYZ   { float x, y, z; };                   // transformed vertex

const float sphere_r = 1e4f; // the actual render distance for the celestial sphere
	                    	 // is irrelevant, since it is rendered without z-buffer,
	                 		 // but it must be within the fustrum limits - check this
	                		 // in case the near and far planes are dynamically changed!

OGLCelestialSphere::OGLCelestialSphere () : oapi::CelestialSphere(g_client)
{
	m_constellationsShader = Renderer::GetShader("Constellations");
	m_starsShader = Renderer::GetShader("Stars");
	m_eclShader = Renderer::GetShader("Ecliptic");

	LoadGpuStars ();
	LoadGpuConstellationLines ();
	CreateEcliptic ();
}

// ==============================================================

OGLCelestialSphere::~OGLCelestialSphere ()
{
}

// ==============================================================

void OGLCelestialSphere::LoadGpuStars ()
{
    const auto stars=oapi::CelestialSphere::LoadStars();
    struct Vertex { float x,y,z,mag; };
    std::vector<Vertex> vertices;vertices.reserve(stars.size());
    int previous=256,index=0;
    for(const auto &star:stars) {
        vertices.push_back({float(star.pos.x*sphere_r),float(star.pos.y*sphere_r),float(star.pos.z*sphere_r),float(star.brightness)});
        int level=std::clamp(int(star.brightness*128),0,255);
        for(int i=level;i<previous;++i)lvlid[i]=index;
        previous=level;++index;
    }
    for(int i=0;i<previous;++i)lvlid[i]=index;
    nstars=vertices.size();
    m_starsVAO=std::make_unique<VertexArray>();m_starsVAO->Bind();
    m_starsVBO=std::make_unique<VertexBuffer>(vertices.data(),uint32_t(vertices.size()*sizeof(Vertex)));
    glVertexAttribPointer(0,4,GL_FLOAT,GL_FALSE,0,nullptr);glEnableVertexAttribArray(0);m_starsVAO->UnBind();
}

void OGLCelestialSphere::LoadGpuConstellationLines ()
{
    const auto lines=oapi::CelestialSphere::LoadConstellationLines();
    ncline=lines.size()/2;
    VERTEX_XYZ *cnstvtx=new VERTEX_XYZ[lines.size()];
    for(size_t i=0;i<lines.size();++i)cnstvtx[i]={float(lines[i].x*sphere_r),float(lines[i].y*sphere_r),float(lines[i].z*sphere_r)};
	m_constellationsVAO = std::make_unique<VertexArray>();
	m_constellationsVAO->Bind();
	m_constellationsVBO = std::make_unique<VertexBuffer>(cnstvtx, 2 * ncline * sizeof(VERTEX_XYZ));
	glVertexAttribPointer(
	0,                  // attribute 0. No particular reason for 0, but must match the layout in the shader.
	3,                  // size
	GL_FLOAT,           // type
	GL_FALSE,           // normalized?
	0,                  // stride
	(void*)0            // array buffer offset
	);
	Renderer::CheckError("glVertexAttribPointer");
	glEnableVertexAttribArray(0);
	Renderer::CheckError("glEnableVertexAttribArray");
	m_constellationsVAO->UnBind();
	delete[]cnstvtx;
}

void OGLCelestialSphere::RenderStars (OGLCamera *c, VECTOR3 &bgcol)
{
	int bglvl = std::min (255, (int)((std::min(bgcol.x,1.0) + std::min(bgcol.y,1.0) + std::min(bgcol.z,1.0))*128.0));
	int ns = std::min ((int)nstars, lvlid[bglvl]);

	auto vp = c->GetViewProjectionMatrix();
	Renderer::Bind(m_starsShader);
	m_starsShader->SetMat4("u_ViewProjection", *vp);
	m_starsVAO->Bind();
	glDrawArrays(GL_POINTS, 0, ns);
	Renderer::CheckError("glDrawArrays");
	m_starsVAO->UnBind();
	Renderer::Unbind(m_starsShader);
}
void OGLCelestialSphere::RenderConstellations (VECTOR3 &col, OGLCamera *c)
{
	auto vp = c->GetViewProjectionMatrix();
	Renderer::Bind(m_constellationsShader);
	m_constellationsShader->SetMat4("u_ViewProjection", *vp);
	m_constellationsVAO->Bind();
	glDrawArrays(GL_LINES, 0, ncline * 2); // Starting from vertex 0; 3 vertices total -> 1 triangle
	Renderer::CheckError("glDrawArrays");
	m_constellationsVAO->UnBind();
	Renderer::Unbind(m_constellationsShader);
}

void OGLCelestialSphere::CreateEcliptic()
{
	necl = NSEG + 1;

	std::vector<VERTEX_XYZ> vbuf(necl);
	for (int i = 0; i <= NSEG; i++) {
		double lng = 2.0*PI * (double)i/(double)NSEG;
		vbuf[i].x = (float)(sphere_r * cos(lng));
		vbuf[i].z = (float)(sphere_r * sin(lng));
		vbuf[i].y = 0.0f;
	}

	m_eclVAO = std::make_unique<VertexArray>();
	m_eclVAO->Bind();
	m_eclVBO = std::make_unique<VertexBuffer>(vbuf.data(), necl * sizeof(VERTEX_XYZ));
	glVertexAttribPointer(
	0,                  // attribute 0. No particular reason for 0, but must match the layout in the shader.
	3,                  // size
	GL_FLOAT,           // type
	GL_FALSE,           // normalized?
	0,                  // stride
	(void*)0            // array buffer offset
	);
	Renderer::CheckError("glVertexAttribPointer");
	glEnableVertexAttribArray(0);
	Renderer::CheckError("glEnableVertexAttribArray");
	m_eclVAO->UnBind();
}

void OGLCelestialSphere::RenderEcliptic(OGLCamera *c)
{
	auto vp = c->GetViewProjectionMatrix();
	Renderer::Bind(m_eclShader);
	m_eclShader->SetMat4("u_ViewProjection", *vp);
	m_eclVAO->Bind();
	glDrawArrays(GL_LINE_STRIP, 0, necl);
	Renderer::CheckError("glDrawArrays");
	m_eclVAO->UnBind();
	Renderer::Unbind(m_eclShader);
}

bool OGLCelestialSphere::EclDir2WindowPos(const VECTOR3 &dir,int &x,int &y) const {
    return g_client->GetScene()->GetCamera()->Direction2Viewport(dir,x,y);
}
