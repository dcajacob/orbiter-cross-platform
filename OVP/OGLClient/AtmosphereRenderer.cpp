// Licensed under the MIT License
#include "AtmosphereRenderer.h"
#include "OGLCamera.h"
#include "Renderer.h"
#include "Shader.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace {
constexpr float atmosphereHeightKm = 96.0f;
constexpr float rayleighHeightKm = 8.0f;
constexpr float aerosolHeightKm = 1.2f;
constexpr float ozoneHeightKm = 25.0f;
constexpr float ozoneHalfWidthKm = 15.0f;
const glm::vec3 rayleigh(0.005802f, 0.013558f, 0.033100f);
const glm::vec3 aerosolScatter(0.003996f);
const glm::vec3 aerosolExtinction(0.004440f);
const glm::vec3 ozone(0.000650f, 0.001881f, 0.000085f);

void BindTexture(GLuint &id, GLenum filter)
{
    if (!id) glGenTextures(1, &id);
    glBindTexture(GL_TEXTURE_2D, id);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
}
}

AtmosphereRenderer::~AtmosphereRenderer()
{
    const GLuint textures[] = {depth, lookup, inscatter, viewTransmittance};
    if (depth || lookup) glDeleteTextures(4, textures);
    if (framebuffer) glDeleteFramebuffers(1, &framebuffer);
    if (vao) glDeleteVertexArrays(1, &vao);
}

void AtmosphereRenderer::Prepare(const OGLCamera &camera)
{
    active = false;
    if (!*static_cast<const bool *>(g_client->GetConfigParam(CFGPRM_ATMHAZE)) ||
        !camera.GetWidth() || !camera.GetHeight()) return;
    if (!earth) {
        char name[] = "Earth";
        earth = oapiGetGbodyByName(name);
    }
    if (!earth || camera.GetProxyBody() != earth || !oapiPlanetHasAtmosphere(earth)) return;
    const OBJHANDLE star = oapiGetGbodyByIndex(0);
    const double earthRadius = oapiGetSize(earth);
    if (!star || earthRadius <= 0.0) return;
    VECTOR3 centre{}, starPosition{};
    oapiGetGlobalPos(earth, &centre);
    oapiGetGlobalPos(star, &starPosition);
    const VECTOR3 offset = *camera.GetGPos() - centre;
    const double distance = length(offset);
    if (distance < earthRadius - 10000.0) return;

    radius = float(earthRadius * 0.001);
    altitude = float(std::max(0.001, (distance - earthRadius) * 0.001));
    const VECTOR3 up = offset / distance;
    const VECTOR3 toSun = unit(starPosition - centre);
    position = glm::vec3(up.x, up.y, up.z) * (radius + altitude);
    sun = glm::vec3(toSun.x, toSun.y, toSun.z);
    active = true;
}

void AtmosphereRenderer::BuildTransmittance()
{
    if (lookup && lookupRadius == radius) return;
    // Parameterise by distance to the top of the atmosphere and distance
    // to the ground horizon. This concentrates texels on grazing rays.
    constexpr int cols = 192, rows = 64, samples = 96;
    const double outer = double(radius) + atmosphereHeightKm;
    const double horizon = std::sqrt((outer - radius) * (outer + radius));
    std::vector<glm::vec3> data(cols * rows);
    for (int y = 0; y < rows; ++y) {
        const double rho = horizon * y / (rows - 1);
        const double r = std::sqrt(double(radius) * radius + rho * rho);
        const double shortest = outer - r;
        for (int x = 0; x < cols; ++x) {
            const double distance = shortest + (rho + horizon - shortest) * x / (cols - 1);
            const double project = distance > 0.0
                ? ((outer - r) * (outer + r) - distance * distance) / (2.0 * distance) : 0.0;
            glm::dvec3 column(0.0);
            const double ds = distance / samples;
            for (int i = 0; i < samples; ++i) {
                const double t = (i + 0.5) * ds;
                const double h = std::max(0.0, std::sqrt(r * r + t * (t + 2.0 * project)) - radius);
                column += glm::dvec3(std::exp(-h / rayleighHeightKm), std::exp(-h / aerosolHeightKm),
                                    std::max(0.0, 1.0 - std::abs(h - ozoneHeightKm) / ozoneHalfWidthKm));
            }
            data[y * cols + x] = glm::exp(-float(ds) * (rayleigh * float(column.x) +
                aerosolExtinction * float(column.y) + ozone * float(column.z)));
        }
    }
    BindTexture(lookup, GL_LINEAR);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, cols, rows, 0, GL_RGB, GL_FLOAT, data.data());
    lookupRadius = radius;
}

void AtmosphereRenderer::Resize(int w, int h)
{
    if (w == width && h == height) return;
    width = w;
    height = h;
    BindTexture(depth, GL_NEAREST);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, w, h, 0, GL_DEPTH_COMPONENT, GL_UNSIGNED_INT, nullptr);
    BindTexture(inscatter, GL_NEAREST);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, (w+1)/2, (h+1)/2, 0, GL_RGBA, GL_HALF_FLOAT, nullptr);
    BindTexture(viewTransmittance, GL_NEAREST);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, (w+1)/2, (h+1)/2, 0, GL_RGBA, GL_HALF_FLOAT, nullptr);

    if (!framebuffer) glGenFramebuffers(1, &framebuffer);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, framebuffer);
    glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, inscatter, 0);
    glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, GL_TEXTURE_2D, viewTransmittance, 0);
    const GLenum attachments[] = {GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1};
    glDrawBuffers(2, attachments);
    if (glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
        throw std::runtime_error("Cannot create the OpenGL atmosphere target");
}

void AtmosphereRenderer::Render(const OGLCamera &camera)
{
    if (!active) return;
    GLint draw = 0, read = 0, unit = 0, oldVAO = 0, viewport[4]{}, binding[3]{};
    glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &draw);
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &read);
    glGetIntegerv(GL_ACTIVE_TEXTURE, &unit);
    glGetIntegerv(GL_VERTEX_ARRAY_BINDING, &oldVAO);
    glGetIntegerv(GL_VIEWPORT, viewport);
    for (int i = 2; i >= 0; --i) {
        glActiveTexture(GL_TEXTURE0+i);
        glGetIntegerv(GL_TEXTURE_BINDING_2D, &binding[i]);
    }
    BuildTransmittance();
    Resize(camera.GetWidth(), camera.GetHeight());
    if (!vao) glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    glBindFramebuffer(GL_READ_FRAMEBUFFER, draw);
    glBindTexture(GL_TEXTURE_2D, depth);
    glCopyTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 0, 0, width, height);
    glBindFramebuffer(GL_READ_FRAMEBUFFER, read);

    Renderer::PushBool(Renderer::DEPTH_TEST, false);
    Renderer::PushBool(Renderer::CULL_FACE, false);
    Renderer::PushBool(Renderer::BLEND, false);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, framebuffer);
    glViewport(0, 0, (width+1)/2, (height+1)/2);
    Shader *scatter = Renderer::GetShader("AtmosphereScatter");
    Renderer::Bind(scatter);
    scatter->SetInt("u_Depth", 0);
    scatter->SetInt("u_SunTransmittance", 1);
    scatter->SetInt("u_AerialPerspective", *static_cast<const bool *>(g_client->GetConfigParam(CFGPRM_ATMFOG)));
    scatter->SetVec3("u_Camera", position);
    scatter->SetVec3("u_Sun", sun);
    scatter->SetVec3("u_Planet", glm::vec3(radius, altitude, atmosphereHeightKm));
    scatter->SetVec3("u_Rayleigh", rayleigh);
    scatter->SetVec3("u_AerosolScatter", aerosolScatter);
    scatter->SetVec3("u_AerosolExtinction", aerosolExtinction);
    scatter->SetVec3("u_Ozone", ozone);
    scatter->SetVec4("u_DensityProfile", glm::vec4(rayleighHeightKm, aerosolHeightKm, ozoneHeightKm, ozoneHalfWidthKm));
    scatter->SetMat4("u_RayToWorld", glm::inverse(*camera.GetViewProjectionMatrix()));
    glActiveTexture(GL_TEXTURE1);
    glBindTexture(GL_TEXTURE_2D, lookup);
    glDrawArrays(GL_TRIANGLES, 0, 3);

    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, draw);
    glViewport(viewport[0], viewport[1], viewport[2], viewport[3]);
    glBindTexture(GL_TEXTURE_2D, inscatter);
    glActiveTexture(GL_TEXTURE2);
    glBindTexture(GL_TEXTURE_2D, viewTransmittance);
    Renderer::PopBool();
    Renderer::PushBool(Renderer::BLEND, true);
    Renderer::PushBlendFunc(GL_ONE, GL_SRC1_COLOR);
    Shader *composite = Renderer::GetShader("AtmosphereComposite");
    Renderer::Bind(composite);
    composite->SetInt("u_Depth", 0);
    composite->SetInt("u_Inscatter", 1);
    composite->SetInt("u_Transmittance", 2);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    Renderer::PopBlendFunc();
    Renderer::PopBool(3);
    glBindVertexArray(oldVAO);
    for (int i = 0; i < 3; ++i) {
        glActiveTexture(GL_TEXTURE0+i);
        glBindTexture(GL_TEXTURE_2D, binding[i]);
    }
    glActiveTexture(unit);
    Renderer::CheckError("Atmospheric scattering");
}
