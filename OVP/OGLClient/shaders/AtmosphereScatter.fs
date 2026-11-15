#version 330 core

in vec2 ScreenUV;
layout(location = 0) out vec4 inscatter;
layout(location = 1) out vec4 transmittance;
uniform sampler2D u_Depth;
uniform sampler2D u_SunTransmittance;
uniform bool u_AerialPerspective;
uniform vec3 u_Camera;
uniform vec3 u_Sun;
uniform vec3 u_Planet; // radius, camera altitude, atmosphere height in km
uniform vec3 u_Rayleigh;
uniform vec3 u_AerosolScatter;
uniform vec3 u_AerosolExtinction;
uniform vec3 u_Ozone;
uniform vec4 u_DensityProfile;
uniform mat4 u_RayToWorld;

const float PI = 3.14159265;

vec2 sphereInterval(float projection, float height)
{
    float constant = (u_Planet.y - height) * (2.0 * u_Planet.x + u_Planet.y + height);
    float discriminant = projection * projection - constant;
    if (discriminant <= 0.0) return vec2(1e20, -1e20);
    float extent = sqrt(discriminant);
    float farRoot = -projection - (projection > 0.0 ? extent : -extent);
    float nearRoot = farRoot != 0.0 ? constant / farRoot : 0.0;
    return vec2(min(nearRoot, farRoot), max(nearRoot, farRoot));
}

vec3 sunlight(float mu, float height, float horizon)
{
    float r = u_Planet.x + height;
    float toHorizon = sqrt(height * (2.0 * u_Planet.x + height));
    float cutoff = -toHorizon / r;
    // Cover the partial solar disc at the edge of Earth's shadow.
    float visible = smoothstep(cutoff - 0.00465, cutoff + 0.00465, mu);
    if (visible <= 0.0) return vec3(0.0);
    float projection = max(mu, cutoff) * r;
    float heightToTop = u_Planet.z - height;
    float cap = heightToTop * (r + u_Planet.x + u_Planet.z);
    float root = sqrt(projection * projection + cap);
    float distance = projection > 0.0 ? cap / max(root + projection, 0.001) : root - projection;
    vec2 uv = vec2((distance - heightToTop) / (horizon + toHorizon - heightToTop), toHorizon / horizon);
    vec2 size = vec2(textureSize(u_SunTransmittance, 0));
    return visible * textureLod(u_SunTransmittance, (0.5 + clamp(uv, 0.0, 1.0) * (size - 1.0)) / size, 0.0).rgb;
}

float sampleFraction(float fraction, float lowest)
{
    // Place more samples near the densest point on the segment, including
    // grazing rays whose lowest altitude lies between the endpoints.
    float shift = fraction - lowest;
    float wing = shift < 0.0 ? lowest : 1.0 - lowest;
    return lowest + shift * abs(shift) / max(wing, 1e-5);
}

void main()
{
    inscatter = vec4(0.0);
    transmittance = vec4(1.0);
    float depth = texture(u_Depth, ScreenUV).r;
    if (!u_AerialPerspective && depth < 1.0) return;
    vec3 direction = (u_RayToWorld * vec4(ScreenUV * 2.0 - 1.0, 0.0, 1.0)).xyz;
    float rayScale = length(direction);
    vec3 ray = direction / rayScale;
    float projection = dot(u_Camera, ray);
    vec2 atmosphere = sphereInterval(projection, u_Planet.z);
    float start = max(atmosphere.x, 0.0);
    float end = atmosphere.y;
    vec2 ground = sphereInterval(projection, 0.0);
    if (ground.x > 0.0) end = min(end, ground.x);
    if (depth < 1.0)
        end = min(end, (exp2(depth * log2(1e11 + 1.0)) - 1.0) * rayScale * 0.001);
    float span = end - start;
    if (span < 0.001) return;

    float horizon = sqrt(u_Planet.z * (2.0 * u_Planet.x + u_Planet.z));
    float lowest = clamp((-projection - start) / span, 0.0, 1.0);
    float angle = dot(ray, u_Sun);
    float phaseRayleigh = 3.0 * (1.0 + angle * angle) / (16.0 * PI);
    const float g = 0.76;
    float phaseAerosol = (1.0 - g*g) / (4.0 * PI * pow(1.0 + g*g - 2.0*g*angle, 1.5));
    vec3 radiance = vec3(0.0);
    vec3 viewT = vec3(1.0);
    const int steps = 12;
    float previous = 0.0;
    for (int i = 0; i < steps; ++i) {
        float next = sampleFraction(float(i + 1) / float(steps), lowest);
        float ds = span * (next - previous);
        float t = start + span * (0.5 * (previous + next));
        previous = next;
        vec3 point = u_Camera + t * ray;
        float height = clamp(length(point) - u_Planet.x, 0.0, u_Planet.z);
        vec2 density = exp(-height / u_DensityProfile.xy);
        float ozoneDensity = max(0.0, 1.0 - abs(height - u_DensityProfile.z) / u_DensityProfile.w);
        vec3 molecular = u_Rayleigh * density.x;
        vec3 aerosol = u_AerosolScatter * density.y;
        vec3 sigma = molecular + u_AerosolExtinction * density.y + u_Ozone * ozoneDensity;
        vec3 through = exp(-ds * sigma);
        float sunCosine = dot(point, u_Sun) / (u_Planet.x + height);
        vec3 source = sunlight(sunCosine, height, horizon) *
                      (phaseRayleigh * molecular + phaseAerosol * aerosol);
        // Approximate higher-order scattering as diffuse illumination from
        // the lit sky. This also supplies a twilight floor inside the shadow.
        float skyLight = smoothstep(-0.145, 0.035, sunCosine);
        source += skyLight * vec3(0.009, 0.014, 0.023) * (molecular + aerosol);
        radiance += viewT * source * ((1.0 - through) / max(sigma, vec3(1e-7)));
        viewT *= through;
    }
    // The surrounding OpenGL passes already write display-range colour.
    inscatter = vec4(pow(1.0 - exp(-7.0 * radiance), vec3(0.72)), 0.0);
    transmittance = vec4(viewT, 1.0);
}
