// The house's surfaces: a photographed texture tinted to the material's paint colour (or the Hyper3D model's own
// texture), lit by the night lighting baked in Blender (lightmap on the second UV set). Things that move (doors,
// items) have no lightmap and use a flat light set per room instead.
Shader "TradersMadness/House"
{
    Properties
    {
        _MainTex ("Photo or own texture", 2D) = "white" {}
        _LM ("Baked light", 2D) = "white" {}
        _Base ("Paint colour (linear)", Vector) = (0.5, 0.5, 0.5, 0)
        _Tint ("How much paint colour replaces the photo", Float) = 1
        _Avg ("Average brightness of the photo", Float) = 0.5
        _LMGain ("Baked light gain", Float) = 2.48
        _FlatLight ("Light when there is no lightmap", Vector) = (0.3, 0.3, 0.31, 0)
        _UseLM ("Use the lightmap", Float) = 1
        _Ambient ("Ambient", Vector) = (0.008, 0.009, 0.012, 0)
        _Glow ("Glow", Float) = 0
        _Mul ("Colour multiplier", Color) = (1, 1, 1, 1)
        _Gray ("Desaturate", Float) = 0
        _Cutout ("Alpha cut-out", Float) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        LOD 100
        Pass
        {
            Cull [_Cull]
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "TMCommon.cginc"

            sampler2D _MainTex;
            sampler2D _LM;
            float4 _Base;
            float _Tint;
            float _Avg;
            float _LMGain;
            float4 _FlatLight;
            float _UseLM;
            float4 _Ambient;
            float _Glow;
            float4 _Mul;
            float _Gray;
            float _Cutout;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                float2 uv2 : TEXCOORD1;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float2 uv2 : TEXCOORD1;
                float dist : TEXCOORD2;
            };

            v2f vert(appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                o.uv2 = v.uv2;
                float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.dist = distance(wp, _WorldSpaceCameraPos.xyz);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                float4 t4 = tex2D(_MainTex, i.uv);
                if (_Cutout > 0.5)
                    clip(t4.a - 0.5);
                float3 t = t4.rgb;
                float l = dot(t, float3(0.33333, 0.33333, 0.33333)) / max(_Avg, 0.03);
                float3 c = lerp(t, _Base.rgb * clamp(l, 0.0, 2.2), _Tint);
                float g = dot(c, float3(0.3, 0.59, 0.11));
                c = lerp(c, float3(g, g, g), _Gray) * _Mul.rgb;
                float3 light = lerp(_FlatLight.rgb, tex2D(_LM, i.uv2).rgb * _LMGain, _UseLM) + _Ambient.rgb;
                float3 col = c * light + _Base.rgb * _Glow;
                return float4(TMFinish(col, i.dist), 1.0);
            }
            ENDCG
        }
    }
    Fallback Off
}
