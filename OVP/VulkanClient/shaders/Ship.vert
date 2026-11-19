#version 450
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec2 uv;
layout(set=1,binding=0,std140) uniform Scene {
    mat4 modelViewProjection;
    vec4 light;
    vec4 eye;
    mat4 shadowTransform;
} scene;
layout(location=0) out vec2 texcoord;
layout(location=1) out vec3 surfaceNormal;
layout(location=2) out float distanceAlongView;
layout(location=3) out vec3 toEye;
layout(location=4) flat out vec3 toLight;
layout(location=5) out vec3 shadowCoord;
void main() {
    shadowCoord = (scene.shadowTransform * vec4(position, 1.0)).xyz;
    gl_Position = scene.modelViewProjection * vec4(position, 1.0);
    distanceAlongView = gl_Position.w;
    surfaceNormal = normal;
    toEye = scene.eye.xyz - position;
    toLight = scene.light.xyz;
    texcoord = uv;
}
