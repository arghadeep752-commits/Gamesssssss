Shader "RealFPS/Glass"
{
    // URP. Thin glass (lantern panes): faint tint, Fresnel reflection of the environment
    // cubemap and a sharp sun highlight. Premultiplied alpha, no refraction.
    Properties
    {
        [MainColor] _BaseColor ("Tint (A = opacity)", Color) = (0.9, 0.85, 0.75, 0.18)
        _Smoothness ("Smoothness", Range(0, 1)) = 0.92
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent" "RenderType" = "Transparent" "IgnoreProjector" = "True" }

        Pass
        {
            Name "Glass"
            Tags { "LightMode" = "UniversalForward" }
            Blend One OneMinusSrcAlpha
            ZWrite Off
            Cull Back

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor;
                half _Smoothness;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                half3 normalWS : TEXCOORD1;
                half fogFactor : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, o);
                o.positionWS = TransformObjectToWorld(input.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(input.normalOS);
                o.fogFactor = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                half3 N = normalize(i.normalWS);
                half3 V = GetWorldSpaceNormalizeViewDir(i.positionWS);
                half NdotV = saturate(dot(N, V));
                half fresnel = 0.04h + 0.96h * pow(1.0h - NdotV, 5.0h);
                half3 R = reflect(-V, N);
                half mip = (1.0h - _Smoothness) * 6.0h;
                half4 encoded = SAMPLE_TEXTURECUBE_LOD(unity_SpecCube0, samplerunity_SpecCube0, R, mip);
                half3 env = DecodeHDREnvironment(encoded, unity_SpecCube0_HDR);
                Light light = GetMainLight();
                half3 H = SafeNormalize(light.direction + V);
                half spec = pow(saturate(dot(N, H)), 256.0h) * 2.0h;
                half a = _BaseColor.a;
                half3 col = _BaseColor.rgb * a * (SampleSH(N) + light.color * 0.3h) + env * fresnel + light.color * spec;
                col = MixFogColor(col, half3(0.0h, 0.0h, 0.0h), i.fogFactor);
                return half4(col, saturate(a + fresnel * 0.5h));
            }
            ENDHLSL
        }
    }
    Fallback Off
}
