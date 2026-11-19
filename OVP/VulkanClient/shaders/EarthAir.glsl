// Earth-fixed positions in kilometres. Integrate the same density profile
// along surface and sky rays so both sides of the limb share one atmosphere.
layout(set=3,binding=0,std140) uniform Atmosphere {
    vec4 eyeRadius;
    vec4 sunlight;
    vec4 right, up, forward;
} air;
vec3 aerialColor(vec3 ray, float distanceKm, vec3 background) {
    vec3 eye = air.eyeRadius.xyz;
    float radius = air.eyeRadius.w;
    float b = dot(eye, ray);
    float impact = length(cross(eye, ray));
    float top = radius + 80.0;
    if (impact >= top) return background;
    float halfChord = sqrt((top-impact)*(top+impact));
    float start = max(0.0, -b-halfChord);
    float finish = min(distanceKm, -b+halfChord);
    if (finish <= start) return background;
    float stepKm = (finish-start)/8.0;
    vec3 extinction = vec3(0.0058, 0.0135, 0.0331);
    vec3 transmission = vec3(1), scatter = vec3(0);
    for (int i = 0; i < 8; ++i) {
        vec3 point = eye + ray * (start + (float(i)+0.5)*stepKm);
        float elevation = max(0.0, length(point)-radius);
        float sunHeight = dot(normalize(point), air.sunlight.xyz);
        float day = smoothstep(-0.09, 0.10, sunHeight + sqrt(2.0*elevation/radius));
        vec3 atten = exp(-extinction * (exp(-elevation/8.0)*stepKm));
        scatter += transmission * (1.0-atten) * day;
        transmission *= atten;
    }
    float mu = dot(ray, air.sunlight.xyz);
    return background*transmission + sqrt(max(scatter,vec3(0))) * vec3(0.61,0.75,0.99) * (0.78+0.22*mu*mu);
}
