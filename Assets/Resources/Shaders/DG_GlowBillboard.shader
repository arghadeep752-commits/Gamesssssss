// Camera-facing glows from one mesh: street lamp heads at night, car lights, muzzle flashes, impact sparks.
// Each quad's 4 vertices sit at the glow's centre; uv picks the corner, uv2.x is the size in metres.
Shader "Danga/GlowBillboard"
{
    Properties
    {
        _MainTex ("Shape", 2D) = "white" {}
        _Color ("Colour", Color) = (1, 0.85, 0.6, 1)
        _NightOnly ("Night only", Float) = 1
        _Scale ("Scale", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent+10" }
        ZWrite Off
        Blend SrcAlpha One
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "DGCommon.cginc"
            sampler2D _MainTex;
            half4 _Color;
            float _NightOnly;
            float _Scale;
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; float2 uv2 : TEXCOORD1; float4 color : COLOR; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; half4 col : TEXCOORD1; };
            v2f vert (appdata v)
            {
                v2f o;
                float4 vp = mul(UNITY_MATRIX_MV, float4(v.vertex.xyz, 1));
                vp.xy += (v.uv * 2.0 - 1.0) * v.uv2.x * _Scale;
                o.pos = mul(UNITY_MATRIX_P, vp);
                o.uv = v.uv;
                o.col = v.color * _Color;
                o.col.a *= lerp(1.0, _DG_Misc.x, _NightOnly);
                return o;
            }
            half4 frag (v2f i) : SV_Target
            {
                half a = tex2D(_MainTex, i.uv).a * i.col.a;
                return half4(i.col.rgb, a);
            }
            ENDCG
        }
    }
}
