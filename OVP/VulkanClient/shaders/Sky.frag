#version 450
#extension GL_GOOGLE_include_directive : require
#include "EarthAir.glsl"
layout(location=0) in vec2 screen;
layout(location=0) out vec4 color;
void main() {
    vec3 ray = normalize(air.forward.xyz + screen.x*air.right.xyz + screen.y*air.up.xyz);
    color = vec4(aerialColor(ray,1e10,vec3(0)),1);
}
