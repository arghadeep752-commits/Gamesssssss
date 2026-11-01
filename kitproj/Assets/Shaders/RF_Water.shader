Shader "RealFPS/Water"
{
    // URP lake surface: two scrolling normal maps, sky reflection from the HDRI panorama
    // (no reflection camera, no screen-space effects), depth-tinted body colour from a
    // pre-computed lake depth map, sun glints and fog. One pass, alpha-blended.
    Properties
    {
        _ShallowColor ("Shallow colour", Color) = (0.30, 0.38, 0.30, 1)
        _DeepColor ("Deep colour", Color) = (0.035, 0.085, 0.095, 1)
        _NormalMap ("Normal map", 2D) = "bump" {}
        _DepthTex ("Depth (R)", 2D) = "black" {}
        _DepthRect ("Depth rect (xMin, zMin, 1/width, 1/depth)", Vector) = (0, 0, 1, 1)
        _MaxDepth ("Depth of R=1 (m)", Float) = 8
        _Sky ("Sky panorama", 2D) = "white" {}
        _SkyRotation ("Sky rotation", Float) = 0
        _Wave ("Wave tiling A, B, strength", Vector) = (0.045, 0.12, 0.42, 0)
        _WaveSpeed ("Wave speed", Vector) = (0.011, 0.007, -0.009, 0.013)
        _SunPower ("Sun glint power", Float) = 420
        _SunStrength ("Sun glint strength", Float) = 2.2
        _ReflectStrength ("Reflection strength", Range(0, 1.5)) = 0.95
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent-50" "RenderType" = "Transparent" "IgnoreProjector" = "True" }
        LOD 200

        Pass
        {
            Name "Water"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Back

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _NormalMap_ST;
                float4 _DepthRect;
                float4 _Wave;
                float4 _WaveSpeed;
                half4 _ShallowColor;
                half4 _DeepColor;
                float _MaxDepth;
                float _SkyRotation;
                float _SunPower;
                float _SunStrength;
                float _ReflectStrength;
            CBUFFER_END

            TEXTURE2D(_NormalMap);
            SAMPLER(sampler_NormalMap);
            TEXTURE2D(_DepthTex);
            SAMPLER(sampler_DepthTex);
            TEXTURE2D(_Sky);
            SAMPLER(sampler_Sky);

            struct Attributes
            {
                float4 positionOS : POSITION;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                half fogFactor : TEXCOORD1;
            };

            Varyings vert(Attributes input)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(input.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.fogFactor = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            // Same mapping as the Skybox/Panoramic shader (including its rotation).
            half3 SampleSky(float3 d, float lod)
            {
                float a = radians(_SkyRotation);
                float s = sin(a);
                float c = cos(a);
                float3 r = normalize(float3(c * d.x + s * d.z, d.y, -s * d.x + c * d.z));
                float2 uv = float2(0.5 - atan2(r.z, r.x) / (2.0 * PI), 1.0 - acos(clamp(r.y, -1.0, 1.0)) / PI);
                return SAMPLE_TEXTURE2D_LOD(_Sky, sampler_Sky, uv, lod).rgb;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float2 uv1 = i.positionWS.xz * _Wave.x + _Time.y * _WaveSpeed.xy;
                float2 uv2 = i.positionWS.xz * _Wave.y + _Time.y * _WaveSpeed.zw;
                half3 n1 = UnpackNormal(SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, uv1));
                half3 n2 = UnpackNormal(SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, uv2));
                float3 V = _WorldSpaceCameraPos - i.positionWS;
                float dist = length(V);
                V /= max(dist, 1e-3);
                float2 nxy = (n1.xy + n2.xy) * _Wave.z * (0.25 + 0.75 * saturate(1.0 - dist / 260.0));
                float3 N = normalize(float3(nxy.x, 1.0, nxy.y));

                float3 R = reflect(-V, N);
                R.y = abs(R.y);
                half3 sky = SampleSky(R, saturate(dist / 140.0) * 3.0) * _ReflectStrength;
                half fres = 0.02h + 0.98h * pow(1.0h - saturate(dot(N, V)), 5.0h);

                float2 duv = (i.positionWS.xz - _DepthRect.xy) * _DepthRect.zw;
                half depth = SAMPLE_TEXTURE2D(_DepthTex, sampler_DepthTex, duv).r * _MaxDepth;
                half3 body = lerp(_ShallowColor.rgb, _DeepColor.rgb, saturate(depth / 3.0h));
                Light light = GetMainLight();
                half3 ambient = SampleSH(half3(0.0h, 1.0h, 0.0h));
                body *= light.color * (saturate(light.direction.y) * 0.5h) + ambient;

                half3 col = lerp(body, sky, fres);
                half3 H = normalize(light.direction + V);
                half spec = pow(saturate(dot(N, H)), _SunPower) * _SunStrength;
                col += light.color * spec;

                half alpha = saturate(depth * 1.4h + fres * 0.7h);
                alpha = saturate(max(alpha, spec));
                col = MixFog(col, i.fogFactor);
                return half4(col, alpha);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
