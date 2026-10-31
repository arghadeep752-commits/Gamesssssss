Shader "RealFPS/Grass"
{
    // Instanced grass cards: wrapped diffuse + light through the blades, wind,
    // per-clump colour variation and a dithered fade at the draw distance.
    // Vertex colour: R = ambient occlusion, G = wind weight, B = phase.
    Properties
    {
        _MainTex ("Albedo (RGB) Alpha (A)", 2D) = "white" {}
        _Cutoff ("Alpha cutoff", Range(0, 1)) = 0.4
        _ColorA ("Fresh tint", Color) = (1, 1, 1, 1)
        _ColorB ("Dry tint", Color) = (1.12, 1.0, 0.72, 1)
        _Translucency ("Translucency", Range(0, 2)) = 0.6
        _WindStrength ("Wind strength", Range(0, 3)) = 1
        _WindSpeed ("Wind speed", Range(0, 5)) = 1.6
        _FadeStart ("Fade start", Float) = 18
        _FadeEnd ("Fade end", Float) = 30
    }

    SubShader
    {
        Tags { "Queue" = "AlphaTest" "RenderType" = "TransparentCutout" "IgnoreProjector" = "True" }
        LOD 200
        Cull Off

        CGPROGRAM
        #pragma surface surf Grass vertex:vert alphatest:_Cutoff nolightmap nodynlightmap nodirlightmap nometa noforwardadd exclude_path:deferred exclude_path:prepass
        #pragma multi_compile_instancing
        #pragma target 3.0
        #include "UnityPBSLighting.cginc"

        sampler2D _MainTex;
        fixed4 _ColorA;
        fixed4 _ColorB;
        half _Translucency;
        float _WindStrength;
        float _WindSpeed;
        float _FadeStart;
        float _FadeEnd;

        struct Input
        {
            float2 uv_MainTex;
            fixed4 color : COLOR;
            float3 worldPos;
            float4 screenPos;
        };

        void vert(inout appdata_full v)
        {
            float3 origin = float3(unity_ObjectToWorld[0].w, unity_ObjectToWorld[1].w, unity_ObjectToWorld[2].w);
            float3 wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
            float t = _Time.y * _WindSpeed;
            float wave = sin(t + dot(wpos.xz, float2(0.21, 0.13)) + v.color.b * 6.28);
            float gust = 0.55 + 0.45 * sin(t * 0.31 + wpos.x * 0.03 + wpos.z * 0.02);
            float w = v.color.g * v.color.g * _WindStrength;
            float3 offset = float3(wave * 0.09, 0.0, wave * 0.05) * gust * w;
            v.vertex.xyz += mul((float3x3)unity_WorldToObject, offset);
        }

        half4 LightingGrass(SurfaceOutput s, half3 viewDir, UnityGI gi)
        {
            half3 L = gi.light.dir;
            half ndl = saturate(dot(s.Normal, L) * 0.65 + 0.35);
            half back = saturate(dot(viewDir, -L));
            half trans = back * back * back * _Translucency;
            half3 c = s.Albedo * gi.light.color * (ndl + trans);
            c += s.Albedo * gi.indirect.diffuse;
            return half4(c, s.Alpha);
        }

        inline void LightingGrass_GI(SurfaceOutput s, UnityGIInput data, inout UnityGI gi)
        {
            gi = UnityGlobalIllumination(data, 1.0, s.Normal);
        }

        float Bayer4(float2 p)
        {
            float2 q = fmod(floor(p), 4.0);
            float i = q.x + q.y * 4.0;
            // 4x4 ordered dither thresholds
            float4 r0 = float4(0.0, 8.0, 2.0, 10.0);
            float4 r1 = float4(12.0, 4.0, 14.0, 6.0);
            float4 r2 = float4(3.0, 11.0, 1.0, 9.0);
            float4 r3 = float4(15.0, 7.0, 13.0, 5.0);
            float4 row = q.y < 0.5 ? r0 : (q.y < 1.5 ? r1 : (q.y < 2.5 ? r2 : r3));
            float v = q.x < 0.5 ? row.x : (q.x < 1.5 ? row.y : (q.x < 2.5 ? row.z : row.w));
            return (v + 0.5) / 16.0;
        }

        void surf(Input IN, inout SurfaceOutput o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex);
            float n = frac(sin(dot(floor(IN.worldPos.xz * 0.35), float2(12.9898, 78.233))) * 43758.5453);
            fixed3 tint = lerp(_ColorA.rgb, _ColorB.rgb, n * n);
            o.Albedo = c.rgb * tint * lerp(0.55, 1.0, IN.color.r);
            float d = distance(IN.worldPos, _WorldSpaceCameraPos);
            float fade = saturate((_FadeEnd - d) / max(_FadeEnd - _FadeStart, 0.01));
            float2 sp = IN.screenPos.xy / max(IN.screenPos.w, 1e-4) * _ScreenParams.xy;
            o.Alpha = c.a * step(Bayer4(sp), fade);
        }
        ENDCG
    }
    Fallback Off
}
