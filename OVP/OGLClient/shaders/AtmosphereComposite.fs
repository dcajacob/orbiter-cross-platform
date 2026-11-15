#version 330 core

in vec2 ScreenUV;
layout(location = 0, index = 0) out vec4 inscatter;
layout(location = 0, index = 1) out vec4 transmittance;
uniform sampler2D u_Depth;
uniform sampler2D u_Inscatter;
uniform sampler2D u_Transmittance;

void main()
{
    ivec2 size = textureSize(u_Inscatter, 0);
    vec2 position = ScreenUV * vec2(size) - 0.5;
    ivec2 base = ivec2(floor(position));
    vec2 f = fract(position);
    float depth = texture(u_Depth, ScreenUV).r;
    inscatter = vec4(0.0);
    transmittance = vec4(0.0);
    float sum = 0.0;
    // Prevent background haze from spilling onto nearby vessel silhouettes.
    for (int y = 0; y < 2; ++y) {
        for (int x = 0; x < 2; ++x) {
            ivec2 pixel = clamp(base + ivec2(x,y), ivec2(0), size-1);
            float lowDepth = texture(u_Depth, (vec2(pixel) + 0.5) / vec2(size)).r;
            if (abs(lowDepth - depth) > 0.012) continue;
            float weight = (x == 0 ? 1.0-f.x : f.x) * (y == 0 ? 1.0-f.y : f.y);
            inscatter += weight * texelFetch(u_Inscatter, pixel, 0);
            transmittance += weight * texelFetch(u_Transmittance, pixel, 0);
            sum += weight;
        }
    }
    if (sum > 1e-5) {
        inscatter /= sum;
        transmittance /= sum;
    } else {
        transmittance = vec4(1.0);
    }
}
