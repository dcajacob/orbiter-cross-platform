#version 450
layout(location=0) in vec2 texcoord;
layout(location=1) in float illumination;
layout(location=2) in float distanceAlongView;
layout(set=2,binding=0) uniform sampler2D skin;
layout(set=3,binding=0,std140) uniform Material {
    vec4 diffuse;
    vec4 emission;
} material;
layout(location=0) out vec4 color;
void main() {
    vec4 base = texture(skin, texcoord) * material.diffuse;
    if (base.a < 0.01) discard;
    vec3 lit = base.rgb * illumination + material.emission.rgb;
    float haze = smoothstep(4000.0, 65000.0, distanceAlongView);
    // Ground and shadow use the fourth emission component as a draw-mode tag.
    if (material.emission.a == 1.0) lit = mix(lit, vec3(0.42, 0.61, 0.80), haze);
    if (material.emission.a == 2.0) base.a *= 1.0 - haze;
    color = vec4(lit, base.a);
}
