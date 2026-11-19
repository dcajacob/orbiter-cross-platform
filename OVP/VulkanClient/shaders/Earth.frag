#version 450
#extension GL_GOOGLE_include_directive : require
#include "EarthAir.glsl"
layout(location=0) in vec2 texcoord;
layout(location=1) in vec3 surfaceNormal;
layout(location=3) in vec3 toEye;
layout(set=2,binding=0) uniform sampler2D surfaceTile;
layout(location=0) out vec4 color;
void main() {
    float day = max(0.0, dot(normalize(surfaceNormal),air.sunlight.xyz));
    vec3 ground = texture(surfaceTile,texcoord).rgb * (0.012+0.988*sqrt(day));
    color = vec4(aerialColor(-normalize(toEye),length(toEye)*0.001,ground),1.0);
}
