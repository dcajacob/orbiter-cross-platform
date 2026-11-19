#version 450
layout(location=0) in vec2 texcoord;
layout(location=1) in vec3 surfaceNormal;
layout(location=2) in float distanceAlongView;
layout(location=3) in vec3 toEye;
layout(location=4) flat in vec3 toLight;
layout(set=2,binding=0) uniform sampler2D skin;
layout(set=3,binding=0,std140) uniform Material {
    vec4 diffuse;
    vec4 emission;
    vec4 ambient;
    vec4 specular;
} material;
layout(location=0) out vec4 color;
void main() {
    vec4 texel = texture(skin, texcoord);
    float alpha = texel.a * material.diffuse.a;
    if (alpha < 0.01) discard;
    vec3 lit;
    if (material.emission.a == 0.0) {
        vec3 n = normalize(surfaceNormal);
        float incidence = max(dot(n, toLight), 0.0);
        lit = texel.rgb * (0.45 * material.ambient.rgb + 0.55 * incidence * material.diffuse.rgb)
            + material.emission.rgb;
        if (incidence > 0.0 && material.specular.w > 0.0) {
            float highlight = max(dot(reflect(-toLight, n), normalize(toEye)), 0.0);
            lit += 0.55 * material.specular.rgb * pow(highlight, material.specular.w);
        }
    } else {
        float haze = smoothstep(4000.0, 65000.0, distanceAlongView);
        float illumination = 0.45 + 0.55 * max(dot(normalize(surfaceNormal), toLight), 0.0);
        lit = texel.rgb * material.diffuse.rgb * illumination;
        if (material.emission.a == 1.0) lit = mix(lit, vec3(0.42, 0.61, 0.80), haze);
        if (material.emission.a == 2.0) alpha *= 1.0 - haze;
    }
    color = vec4(lit, alpha);
}
