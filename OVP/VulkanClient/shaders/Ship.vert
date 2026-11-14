#version 450
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec2 uv;
layout(set=1,binding=0,std140) uniform Scene {
    mat4 modelViewProjection;
    vec4 light;
} scene;
layout(location=0) out vec2 texcoord;
layout(location=1) out float illumination;
void main() {
    gl_Position = scene.modelViewProjection * vec4(position, 1.0);
    illumination = 0.45 + 0.55 * max(dot(normalize(normal), scene.light.xyz), 0.0);
    texcoord = uv;
}
