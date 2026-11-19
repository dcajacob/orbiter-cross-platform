#version 450
layout(location=0) in vec2 texcoord;
layout(location=1) in vec3 surfaceNormal;
layout(location=2) in float distanceAlongView;
layout(location=5) in vec3 shadowCoord;
layout(set=2,binding=0) uniform sampler2D skin;
layout(set=2,binding=1) uniform sampler2DShadow baseShadow;
layout(location=0) out vec4 color;
void main() {
    float sun = 1.0;
    if (all(greaterThanEqual(shadowCoord.xy, vec2(0))) && all(lessThanEqual(shadowCoord.xy, vec2(1))))
        sun = texture(baseShadow, vec3(shadowCoord.xy, max(shadowCoord.z, 0.0)));
    vec4 ground = texture(skin, texcoord);
    ground.rgb *= (0.45 + 0.55 * max(normalize(surfaceNormal).y, 0.0)) * mix(0.42, 1.0, sun);
    color = vec4(mix(ground.rgb, vec3(0.42, 0.61, 0.80), smoothstep(4000.0, 65000.0, distanceAlongView)), ground.a);
}
