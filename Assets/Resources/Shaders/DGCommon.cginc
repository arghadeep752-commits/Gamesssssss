// DANGA - shared lighting for all world shaders (built-in pipeline, OpenGL ES 3).
#ifndef DG_COMMON
#define DG_COMMON
#include "UnityCG.cginc"

float4 _DG_SunDir;        // xyz: direction TO the sun (world), w: sun strength 0..1
float4 _DG_SunCol;        // rgb
float4 _DG_SkyCol;        // rgb: ambient from above
float4 _DG_GroundCol;     // rgb: ambient from below
float4 _DG_FogCol;        // rgb: fog / horizon colour
float4 _DG_Fog;           // x: start, y: 1/(end-start), z: max fog, w: height falloff
float4 _DG_Misc;          // x: night 0..1, y: time, z: wetness, w: emissive boost
sampler2D _DG_LightMap;   // ground shadows (world xz -> uv)
float4 _DG_LMRect;        // x: half size of the world

half3 DG_Ambient(half3 n)
{
    half t = n.y * 0.5h + 0.5h;
    return lerp(_DG_GroundCol.rgb, _DG_SkyCol.rgb, t);
}

half3 DG_Light(half3 n, half ao)
{
    half ndl = saturate(dot(n, _DG_SunDir.xyz));
    return (DG_Ambient(n) * ao + _DG_SunCol.rgb * ndl * _DG_SunDir.w * (0.35h + 0.65h * ao));
}

half DG_GroundShadow(float3 wpos)
{
    float2 uv = (wpos.xz + _DG_LMRect.x) / (2.0 * _DG_LMRect.x);
    half s = tex2D(_DG_LightMap, uv).r;
    return lerp(1.0h, s, saturate(_DG_SunDir.w * 1.2h));
}

// A light film-style grade in every world shader (no extra post-processing pass on the phone):
// a bit more colour, a gentle S-curve in gamma space, slightly warm.
half3 DG_Grade(half3 c)
{
    half l = dot(c, half3(0.2126h, 0.7152h, 0.0722h));
    c = max(lerp(l.xxx, c, 1.12h), 0.0h);
    half3 g = sqrt(saturate(c));
    g = lerp(g, g * g * (3.0h - 2.0h * g), 0.25h);
    return g * g * half3(1.02h, 1.0h, 0.97h);
}

half3 DG_Fog(half3 col, float3 wpos)
{
    float d = distance(wpos, _WorldSpaceCameraPos.xyz);
    half f = saturate((d - _DG_Fog.x) * _DG_Fog.y) * _DG_Fog.z;
    return DG_Grade(lerp(col, _DG_FogCol.rgb, f));
}
#endif
