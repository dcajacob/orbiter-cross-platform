// Optional engineering observations. Disabled unless ogl-evidence.enabled exists.
#pragma once
#include "GraphicsAPI.h"
namespace Evidence {
void Begin();
void Visual(const char *event,OBJHANDLE object);
void Draw(unsigned vertices,unsigned indices);
void Object(OBJHANDLE object);
void Asset(const char *path);
void Rendered();
void Frame();
void Presented();
void End(bool contextDeleted);
}
