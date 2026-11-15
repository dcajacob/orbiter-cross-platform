// Licensed under the MIT License
#pragma once

#include "OGLClient.h"

class OGLCamera;

class AtmosphereRenderer {
public:
    ~AtmosphereRenderer();

    void Prepare(const OGLCamera &camera);
    void Render(const OGLCamera &camera);
    bool Active() const { return active; }
    bool Covers(OBJHANDLE body) const { return active && body == earth; }

private:
    void BuildTransmittance();
    void Resize(int width, int height);

    OBJHANDLE earth = nullptr;
    bool active = false;
    glm::vec3 position{}, sun{};
    float radius = 0.0f, altitude = 0.0f, lookupRadius = 0.0f;
    GLuint depth = 0, lookup = 0, inscatter = 0, viewTransmittance = 0;
    GLuint framebuffer = 0, vao = 0;
    int width = 0, height = 0;
};
