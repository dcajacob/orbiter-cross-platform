#version 450
layout(location=0) in vec4 vertex;
layout(location=0) out vec2 uv;
layout(set=1,binding=0,std140) uniform Viewport { vec2 pixelScale; };
void main() {
    gl_Position = vec4(vertex.xy * pixelScale + vec2(-1,1), 0, 1);
    uv = vertex.zw;
}
