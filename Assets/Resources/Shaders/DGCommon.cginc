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

half3 DG_Fog(half3 col, float3 wpos)
{
    float d = distance(wpos, _WorldSpaceCameraPos.xyz);
    half f = saturate((d - _DG_Fog.x) * _DG_Fog.y) * _DG_Fog.z;
    return lerp(col, _DG_FogCol.rgb, f);
}
#endif
