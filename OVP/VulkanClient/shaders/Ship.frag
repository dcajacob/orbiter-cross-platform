#version 450
layout(location=0) in vec2 texcoord;
layout(location=1) in vec3 surfaceNormal;
layout(location=2) in float distanceAlongView;
layout(location=3) in vec3 toEye;
layout(location=4) flat in vec3 toLight;
layout(set=2,binding=0) uniform sampler2D skin;
layout(set=2,binding=1) uniform sampler2D flightdeckFinish;
layout(set=3,binding=0,std140) uniform Material {
    vec4 diffuse;
    vec4 emission;
    vec4 ambient;
    vec4 specular;
} material;
layout(location=0) out vec4 color;
void main() {
    vec4 texel = texture(skin, texcoord);
    // Live MFD surfaces already contain the instrument color. The HUD uses
    // black as its transparent background on the combiner glass.
    float cockpit = material.ambient.w;
    if (cockpit < -1.5) {
        color = vec4(texel.rgb, 1.0);
        return;
    }
    if (cockpit < -0.5) {
        float ink = max(max(texel.r, texel.g), texel.b);
        vec2 px = max(fwidth(texcoord), 1.0 / vec2(textureSize(skin, 0)));
        vec3 surround = max(max(texture(skin,texcoord + vec2(px.x,0)).rgb, texture(skin,texcoord - vec2(px.x,0)).rgb),
                            max(texture(skin,texcoord + vec2(0,px.y)).rgb, texture(skin,texcoord - vec2(0,px.y)).rgb));
        float coverage = max(ink, 0.72 * max(max(surround.r, surround.g), surround.b));
        if (coverage < 0.005) discard;
        color = vec4(texel.rgb / coverage, coverage);
        return;
    }
    float alpha = texel.a * material.diffuse.a;
    if (cockpit == 2.0) {
        float grazing = pow(1.0 - abs(dot(normalize(surfaceNormal), normalize(toEye))), 5.0);
        color = vec4(material.diffuse.rgb * 0.06, alpha * (0.20 + 0.45 * grazing));
        return;
    }
    if (alpha < 0.01) discard;
    vec3 lit;
    if (material.emission.a == 0.0) {
        vec3 n = normalize(surfaceNormal);
        float incidence = max(dot(n, toLight), 0.0);
        vec3 lamp = cockpit > 0.5 ? texel.rgb : vec3(1.0);
        if (cockpit == 3.0 || cockpit == 5.0) {
            float ink = max(max(texel.r, texel.g), texel.b);
            lamp *= mix(0.04, 1.0, smoothstep(0.4, 0.75, ink));
        }
        lit = texel.rgb * (0.45 * material.ambient.rgb + 0.55 * incidence * material.diffuse.rgb)
            + material.emission.rgb * lamp;
        if (incidence > 0.0 && material.specular.w > 0.0) {
            float highlight = max(dot(reflect(-toLight, n), normalize(toEye)), 0.0);
            float power = material.specular.w;
            vec3 reflectance = material.specular.rgb;
            if (cockpit >= 4.0) {
                vec4 finish = texture(flightdeckFinish, texcoord);
                power = clamp(2.0 / max(0.002, pow(finish.b, 4.0)) - 2.0, 1.0, 256.0);
                reflectance = mix(reflectance, texel.rgb, finish.a);
            }
            lit += 0.55 * reflectance * pow(highlight, power);
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
