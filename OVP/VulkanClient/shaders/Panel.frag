#version 450
layout(location=0) in vec2 uv;
layout(location=0) out vec4 color;
layout(set=2,binding=0) uniform sampler2D panel;
layout(set=3,binding=0,std140) uniform Paint { float opacity; };
void main() {
    color = texture(panel, uv);
    color.a *= opacity;
}
