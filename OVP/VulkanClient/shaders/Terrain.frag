#version 450
layout(location=0) in vec2 texcoord;
layout(location=2) in float distanceAlongView;
layout(location=5) in vec3 shadowCoord;
layout(set=2,binding=0) uniform sampler2D skin;
layout(set=2,binding=1) uniform sampler2DShadow baseShadow;
layout(location=0) out vec4 color;
void main() {
    if (any(lessThan(shadowCoord.xy, vec2(0))) || any(greaterThan(shadowCoord.xy, vec2(1)))) discard;
    float shade = 1.0 - texture(baseShadow, vec3(shadowCoord.xy, max(shadowCoord.z, 0.0)));
    if (shade <= 0.0 || texture(skin, texcoord).a < 0.01) discard;
    float haze = smoothstep(4000.0, 65000.0, distanceAlongView);
    color = vec4(haze * vec3(0.42, 0.61, 0.80), 0.58 * shade);
}
