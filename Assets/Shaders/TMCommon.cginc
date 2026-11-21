#ifndef TM_COMMON_INCLUDED
#define TM_COMMON_INCLUDED

// Shared by every Trader's Madness shader: a faint night fog and a filmic tone curve.
// _TMFogDensity, _TMFogColor and _TMExposure are global values set by the game (unset: no fog, exposure 1).

float _TMFogDensity;
float4 _TMFogColor;
float _TMExposure;

float3 TMFilmic(float3 c)
{
    const float A = 0.22 * 4.0;
    const float B = 0.30 * 2.0;
    const float C = 0.10;
    const float D = 0.20;
    const float E = 0.01;
    const float F = 0.30;
    const float W = 1.0;
    float3 t = ((c * (A * c + C * B) + D * E) / (c * (A * c + B) + D * F)) - E / F;
    float w = ((W * (A * W + C * B) + D * E) / (W * (A * W + B) + D * F)) - E / F;
    return t / w;
}

// colour in linear light -> fogged and tone mapped (the frame buffer turns it into sRGB)
float3 TMFinish(float3 col, float dist)
{
    float ex = _TMExposure > 0.0 ? _TMExposure : 1.0;
    float fog = 1.0 - exp(-dist * _TMFogDensity);
    col = lerp(col * ex, _TMFogColor.rgb, saturate(fog));
    return TMFilmic(max(col, 0.0));
}

#endif
