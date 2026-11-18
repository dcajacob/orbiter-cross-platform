#version 330 core
#include Common.inc
#include LogDepth.inc

layout(location = 0) out vec4 color;

in vec2 TexCoord;
in vec3 Normal;
in vec3 FragPos;
in float flogz;

in vec4 eyeSpacePosition;

uniform vec4 u_SurfaceUV;
uniform sampler2D u_NightMask;
uniform vec3 u_NightUV;
uniform float u_NightBrightness;
uniform sampler2D u_CloudWest, u_CloudEast;
uniform vec3 u_WestUV, u_EastUV;
uniform float u_CloudSplit, u_CloudShadowOpacity;

void main()
{
	vec4 cTex = texture(colorTexture, TexCoord);
    if(u_lighting == 1) {
        vec3 norm = normalize(Normal);
        vec3 viewDir = normalize( - FragPos);

        vec3 l = vec3(0.0);
        for(int i = 0; i < NR_LIGHTS; i++) {
            vec3 diffuse;
            vec3 specular;
            CalcLight(diffuse, specular,
                      lights[i], norm, FragPos, viewDir, u_Material.specular_power);

            l+= diffuse;
            if(u_Material.specular_power!=0)
                l+=specular;
        }

        cTex.rgb*=l;//clamp(l, 0.0, 1.0);
    }
	vec2 patchUV = (TexCoord - u_SurfaceUV.xy) * u_SurfaceUV.zw;
	float sunHeight = dot(normalize(Normal), -lights[0].dvDirection);
	if (u_CloudShadowOpacity > 0.0 && sunHeight > 0.0) {
		bool west = patchUV.x < u_CloudSplit;
		vec3 transform = west ? u_WestUV : u_EastUV;
		if (transform.z > 0.0) {
			vec2 uv = transform.xy + transform.z * patchUV;
			float coverage = west ? texture(u_CloudWest, uv).a : texture(u_CloudEast, uv).a;
			cTex.rgb *= 1.0 - coverage * u_CloudShadowOpacity;
		}
	}
	if (u_NightBrightness > 0.0) {
		// Fade the emissive RGB mask across twilight; its alpha is the water mask.
		float darkness = 1.0 - smoothstep(-0.32, 0.12, sunHeight);
		cTex.rgb += texture(u_NightMask, u_NightUV.xy + patchUV * u_NightUV.z).rgb * darkness * u_NightBrightness;
	}
	cTex.rgb += u_bgcol;

	if(u_FogDensity != 0.0) {
		float fogCoordinate = abs(eyeSpacePosition.z / eyeSpacePosition.w);
		float fogfactor = exp(-u_FogDensity * fogCoordinate);
		fogfactor = 1.0 - clamp(fogfactor, 0.0, 1.0);
		cTex.rgb = mix(cTex, u_FogColor, fogfactor).rgb;
	}

	color.rgb = lumaBasedReinhardToneMapping(cTex.rgb);
	color.a = cTex.a;
//    color = min(cTex,1);
	gl_FragDepth = FS_LOGZ(flogz);


	/*
	vec3 norm = normalize(Normal);
    float diff = max(dot(norm, -u_SunDir), 0.0);
//    vec4 diffuse = (diff * u_Material.diffuse);

	color = vec4(diff * texture(colorTexture, TexCoord).rgb, texture(colorTexture, TexCoord).a) + vec4(u_bgcol,0);

	if(u_FogDensity != 0.0) {
		float fogCoordinate = abs(eyeSpacePosition.z / eyeSpacePosition.w);
		float fogfactor = exp(-u_FogDensity * fogCoordinate);
		fogfactor = 1.0 - clamp(fogfactor, 0.0, 1.0);
		color = vec4(mix(color, u_FogColor, fogfactor).rgb, color.a);
	}

	//color = vec4(fogfactor,fogfactor,fogfactor,1.0);

	//color = mix(color, u_FogColor, fogfactor);
	//color = vec4(1.0,1.0,0.5,1.0);
	*/
}
