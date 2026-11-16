#ifndef MOULIKA_COMMON_INCLUDED
#define MOULIKA_COMMON_INCLUDED

// Shared by every Moulika shader: the night fog and the filmic tone curve of the Godot version
// (Environment: fog density 0.018, fog colour (0.02, 0.025, 0.04), tonemap FILMIC, white 1.0).
// _MFogDensity and _MFogColor are global values set by the game; unset they mean "no fog".

float _MFogDensity;
float4 _MFogColor;

float3 MoulikaFilmic(float3 c)
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
float3 MoulikaFinish(float3 col, float dist)
{
    float fog = 1.0 - exp(-dist * _MFogDensity);
    col = lerp(col, _MFogColor.rgb, saturate(fog));
    return MoulikaFilmic(max(col, 0.0));
}

#endif
