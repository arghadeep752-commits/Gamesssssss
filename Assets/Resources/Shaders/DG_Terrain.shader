// The ground: two texture-array layers blended per vertex, ground shadows from the light map.
Shader "Danga/Terrain"
{
    Properties
    {
        _Tex ("Layers", 2DArray) = "" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry-10" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma require 2darray
            #include "DGCommon.cginc"
            UNITY_DECLARE_TEX2DARRAY(_Tex);
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; float4 color : COLOR; float2 uv : TEXCOORD0; float4 x : TEXCOORD1; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; half3 n : TEXCOORD1; float3 wpos : TEXCOORD2; half3 col : TEXCOORD3; half3 lay : TEXCOORD4; };
            v2f vert (appdata v)
            {
                v2f o;
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.wpos);
                o.uv = v.uv;
                o.n = mul((float3x3)unity_ObjectToWorld, v.normal);
                o.col = v.color.rgb;
                o.lay = half3(floor(v.x.x * 255.0 + 0.5), floor(v.x.z * 255.0 + 0.5), v.x.w);
                return o;
            }
            half4 frag (v2f i) : SV_Target
            {
                half3 a = UNITY_SAMPLE_TEX2DARRAY(_Tex, float3(i.uv, i.lay.x)).rgb;
                half3 b = UNITY_SAMPLE_TEX2DARRAY(_Tex, float3(i.uv * 0.73, i.lay.y)).rgb;
                // blend with a little height-like contrast so the edges look natural
                half t = saturate((i.lay.z - 0.5h) * 1.6h + 0.5h + (dot(b, half3(0.3h, 0.3h, 0.3h)) - 0.2h) * 0.4h);
                half3 alb = lerp(a, b, t) * i.col;
                half sh = DG_GroundShadow(i.wpos);
                half3 c = alb * DG_Light(i.n * rsqrt(max(dot(i.n, i.n), 1e-6)), sh);
                c = DG_Fog(c, i.wpos);
                return half4(c, 1);
            }
            ENDCG
        }
    }
}
