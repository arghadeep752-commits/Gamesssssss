// Night window: dark moonlit sky gradient with a hazy moon glow and grimy glass streaks.
Shader "NightClass/Window"
{
    Properties
    {
        _Top ("Sky top", Color) = (0.02, 0.035, 0.07, 1)
        _Bottom ("Sky horizon", Color) = (0.07, 0.11, 0.17, 1)
        _Moon ("Moon glow", Color) = (0.35, 0.45, 0.6, 1)
        _MoonPos ("Moon position (uv)", Vector) = (0.7, 0.75, 0, 0)
        _Grime ("Grime texture", 2D) = "white" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "Unlit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            TEXTURE2D(_Grime); SAMPLER(sampler_Grime);
            CBUFFER_START(UnityPerMaterial)
                half4 _Top, _Bottom, _Moon;
                float4 _MoonPos;
                float4 _Grime_ST;
            CBUFFER_END
            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float fog : TEXCOORD1; };
            Varyings vert(Attributes i)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(i.positionOS.xyz);
                o.uv = i.uv;
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 frag(Varyings i) : SV_Target
            {
                half3 sky = lerp(_Bottom.rgb, _Top.rgb, saturate(i.uv.y));
                float d = distance(i.uv, _MoonPos.xy);
                sky += _Moon.rgb * (exp(-d * 9.0) * 0.8 + smoothstep(0.075, 0.06, d) * 1.5);
                half g = SAMPLE_TEXTURE2D(_Grime, sampler_Grime, i.uv * _Grime_ST.xy + _Grime_ST.zw).r;
                sky *= lerp(0.55, 1.0, g);
                sky = MixFog(sky, i.fog);
                return half4(sky, 1);
            }
            ENDHLSL
        }
    }
}
