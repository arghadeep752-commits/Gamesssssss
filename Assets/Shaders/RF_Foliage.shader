Shader "RealFPS/Foliage"
{
    // Alpha-tested, two-sided foliage (conifer needle cards, ferns) with PBR
    // lighting, light shining through from behind, vertex ambient occlusion and
    // wind flutter. Vertex colour: R = ambient occlusion, G = wind weight, B = phase.
    Properties
    {
        _MainTex ("Albedo (RGB) Alpha (A)", 2D) = "white" {}
        _Color ("Tint", Color) = (1, 1, 1, 1)
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
        Tags { "Queue" = "AlphaTest" "RenderType" = "TransparentCutout" "IgnoreProjector" = "True" }
        LOD 300
        Cull Off

        CGPROGRAM
        #pragma surface surf Foliage vertex:vert alphatest:_Cutoff addshadow nolightmap nodynlightmap nodirlightmap nometa noforwardadd exclude_path:deferred exclude_path:prepass
        #pragma multi_compile_instancing
        #pragma target 3.0
        #include "UnityPBSLighting.cginc"

        sampler2D _MainTex;
        fixed4 _Color;
        half _Smoothness;
        half _Translucency;
        fixed4 _TransColor;
        float _WindStrength;
        float _WindSpeed;
        half _AOStrength;

        struct Input
        {
            float2 uv_MainTex;
            fixed4 color : COLOR;
        };

        void vert(inout appdata_full v)
        {
            float3 wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
            float3 origin = float3(unity_ObjectToWorld[0].w, unity_ObjectToWorld[1].w, unity_ObjectToWorld[2].w);
            float t = _Time.y * _WindSpeed;
            float phase = v.color.b * 6.2831 + dot(origin.xz, float2(0.13, 0.07));
            float gust = 0.6 + 0.4 * sin(t * 0.37 + origin.x * 0.02);
            float sway = (sin(t + phase) * 0.65 + sin(t * 2.31 + phase * 1.7) * 0.35) * gust;
            float flutter = sin(t * 7.3 + phase * 3.1 + wpos.y) * 0.25;
            float w = v.color.g * _WindStrength;
            float3 offset = float3(sway, flutter * 0.6, sway * 0.55 + flutter * 0.3) * 0.07 * w;
            v.vertex.xyz += mul((float3x3)unity_WorldToObject, offset);
        }

        half4 LightingFoliage(SurfaceOutputStandard s, half3 viewDir, UnityGI gi)
        {
            half4 c = LightingStandard(s, viewDir, gi);
            half3 L = gi.light.dir;
            half back = saturate(dot(viewDir, -L));
            half wrap = saturate(dot(-s.Normal, L) * 0.5 + 0.5);
            c.rgb += s.Albedo * _TransColor.rgb * gi.light.color * (back * back * back * 0.75 + wrap * 0.25) * _Translucency;
            return c;
        }

        inline void LightingFoliage_GI(SurfaceOutputStandard s, UnityGIInput data, inout UnityGI gi)
        {
            LightingStandard_GI(s, data, gi);
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            half ao = lerp(1.0, IN.color.r, _AOStrength);
            o.Albedo = c.rgb * lerp(1.0, ao, 0.6);
            o.Alpha = c.a;
            o.Metallic = 0;
            o.Smoothness = _Smoothness * ao;
            o.Occlusion = ao;
        }
        ENDCG
    }
    Fallback "Legacy Shaders/Transparent/Cutout/VertexLit"
}
