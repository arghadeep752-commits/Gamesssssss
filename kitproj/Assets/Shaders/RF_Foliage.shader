Shader "RealFPS/Foliage"
{
    // URP. Alpha-tested, two-sided foliage (conifer needle cards, ferns): sun light with
    // shadows, light shining through from behind, sky ambient, vertex ambient occlusion
    // and wind. Vertex colour: R = ambient occlusion, G = wind weight, B = wind phase.
    // GPU-instancing and SRP-Batcher compatible.
    Properties
    {
        [MainTexture] _BaseMap ("Albedo (RGB) Alpha (A)", 2D) = "white" {}
        [MainColor] _BaseColor ("Tint", Color) = (1, 1, 1, 1)
        _Cutoff ("Alpha cutoff", Range(0, 1)) = 0.42
        _Smoothness ("Smoothness", Range(0, 1)) = 0.2
        _Translucency ("Translucency", Range(0, 2)) = 0.7
        _TransColor ("Translucency colour", Color) = (0.6, 0.75, 0.25, 1)
        _WindStrength ("Wind strength", Range(0, 3)) = 1
        _WindSpeed ("Wind speed", Range(0, 5)) = 1.3
        _AOStrength ("Vertex AO strength", Range(0, 1)) = 1
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "Queue" = "AlphaTest" "RenderType" = "TransparentCutout" "IgnoreProjector" = "True" }
        LOD 300
        Cull Off

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            half4 _BaseColor;
            half4 _TransColor;
            half _Cutoff;
            half _Smoothness;
            half _Translucency;
            half _WindStrength;
            half _WindSpeed;
            half _AOStrength;
        CBUFFER_END

        TEXTURE2D(_BaseMap);
        SAMPLER(sampler_BaseMap);

        // Sway of the whole branch plus a faster flutter; the phase comes from the vertex
        // colour and the object's position, so neighbouring trees move out of step.
        float3 WindOffsetWS(float3 positionWS, half4 color)
        {
            float3 origin = float3(UNITY_MATRIX_M[0][3], UNITY_MATRIX_M[1][3], UNITY_MATRIX_M[2][3]);
            float t = _Time.y * _WindSpeed;
            float phase = color.b * 6.2831 + dot(origin.xz, float2(0.13, 0.07));
            float gust = 0.6 + 0.4 * sin(t * 0.37 + origin.x * 0.02);
            float sway = (sin(t + phase) * 0.65 + sin(t * 2.31 + phase * 1.7) * 0.35) * gust;
            float flutter = sin(t * 7.3 + phase * 3.1 + positionWS.y) * 0.25;
            float w = color.g * _WindStrength;
            return float3(sway, flutter * 0.6, sway * 0.55 + flutter * 0.3) * (0.07 * w);
        }
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fog
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                half4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                half3 normalWS : TEXCOORD2;
                half4 color : TEXCOORD3;
                half fogFactor : TEXCOORD4;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                positionWS += WindOffsetWS(positionWS, input.color);
                o.positionWS = positionWS;
                o.positionCS = TransformWorldToHClip(positionWS);
                o.normalWS = TransformObjectToWorldNormal(input.normalOS);
                o.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                o.color = input.color;
                o.fogFactor = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                half4 tex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv) * _BaseColor;
                clip(tex.a - _Cutoff);

                half ao = lerp(1.0h, i.color.r, _AOStrength);
                half3 albedo = tex.rgb * lerp(1.0h, ao, 0.6h);
                half3 N = normalize(i.normalWS);
                half3 V = GetWorldSpaceNormalizeViewDir(i.positionWS);

                Light light = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                half shadow = light.shadowAttenuation * light.distanceAttenuation;
                half3 L = light.direction;
                half NdotL = dot(N, L);

                // needle clumps are not flat surfaces: wrap the diffuse term a little
                half wrap = saturate((NdotL + 0.35h) / 1.35h);
                half3 color = albedo * light.color * (wrap * shadow);

                // soft highlight
                half3 H = SafeNormalize(L + V);
                half specPower = exp2(10.0h * _Smoothness + 1.0h);
                color += light.color * (pow(saturate(dot(N, H)), specPower) * _Smoothness * 0.25h * shadow);

                // light shining through the needles from behind
                half back = saturate(dot(V, -L));
                half trans = (back * back * back * 0.75h + saturate(-NdotL * 0.5h + 0.5h) * 0.25h) * _Translucency;
                color += albedo * _TransColor.rgb * light.color * (trans * lerp(0.35h, 1.0h, shadow));

                // sky ambient with the vertex ambient occlusion
                color += SampleSH(N) * albedo * ao;

                color = MixFog(color, i.fogFactor);
                return half4(color, 1.0h);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Off

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex vertShadow
            #pragma fragment fragShadow
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

            float3 _LightDirection;
            float3 _LightPosition;

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                half4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings vertShadow(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, o);
                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                positionWS += WindOffsetWS(positionWS, input.color);
                float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
            #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 lightDirectionWS = normalize(_LightPosition - positionWS);
            #else
                float3 lightDirectionWS = _LightDirection;
            #endif
                float4 positionCS = TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDirectionWS));
            #if UNITY_REVERSED_Z
                positionCS.z = min(positionCS.z, UNITY_NEAR_CLIP_VALUE);
            #else
                positionCS.z = max(positionCS.z, UNITY_NEAR_CLIP_VALUE);
            #endif
                o.positionCS = positionCS;
                o.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                return o;
            }

            half4 fragShadow(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                half a = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).a * _BaseColor.a;
                clip(a - _Cutoff);
                return 0;
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On
            ColorMask R
            Cull Off

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex vertDepth
            #pragma fragment fragDepth
            #pragma multi_compile_instancing

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
                half4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings vertDepth(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, o);
                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                positionWS += WindOffsetWS(positionWS, input.color);
                o.positionCS = TransformWorldToHClip(positionWS);
                o.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                return o;
            }

            half4 fragDepth(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                clip(SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).a * _BaseColor.a - _Cutoff);
                return i.positionCS.z;
            }
            ENDHLSL
        }
    }
    Fallback "Universal Render Pipeline/Simple Lit"
}
