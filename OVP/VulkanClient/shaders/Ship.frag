#version 450
layout(location=0) in vec2 texcoord;
layout(location=1) in float illumination;
layout(set=2,binding=0) uniform sampler2D skin;
layout(set=3,binding=0,std140) uniform Material {
    vec4 diffuse;
    vec4 emission;
} material;
layout(location=0) out vec4 color;
void main() {
    vec4 base = texture(skin, texcoord) * material.diffuse;
    if (base.a < 0.01) discard;
    color = vec4(base.rgb * illumination + material.emission.rgb, base.a);
}
