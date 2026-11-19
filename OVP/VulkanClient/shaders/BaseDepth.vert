#version 450
layout(location=0) in vec3 position;
layout(set=1,binding=0,std140) uniform Shadow { mat4 transform; } shadow;
void main() {
    vec3 uvz = (shadow.transform * vec4(position, 1.0)).xyz;
    gl_Position = vec4(uvz.x * 2.0 - 1.0, 1.0 - uvz.y * 2.0, uvz.z, 1.0);
}
