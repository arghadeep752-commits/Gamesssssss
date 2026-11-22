// Leaves: alpha-tested texture-array layers, both sides lit, gentle wind sway.
Shader "Danga/Foliage"
{
    Properties
    {
        _Tex ("Layers", 2DArray) = "" {}
        _Cutoff ("Alpha cut", Float) = 0.45
    }
    SubShader
    {
        Tags { "RenderType"="TransparentCutout" "Queue"="AlphaTest" }
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma require 2darray
            #include "DGCommon.cginc"
            UNITY_DECLARE_TEX2DARRAY(_Tex);
            float _Cutoff;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; float4 color : COLOR; float2 uv : TEXCOORD0; float4 x : TEXCOORD1; };
            struct v2f { float4 pos : SV_POSITION; float3 uv : TEXCOORD0; half3 n : TEXCOORD1; float3 wpos : TEXCOORD2; half3 col : TEXCOORD3; };
            v2f vert (appdata v)
            {
                v2f o;
                float3 w = mul(unity_ObjectToWorld, v.vertex).xyz;
                float sway = sin(_DG_Misc.y * 1.7 + w.x * 0.21 + w.z * 0.17) * 0.06 + sin(_DG_Misc.y * 3.1 + w.x * 0.9) * 0.025;
                w.xz += sway * saturate(v.uv.y) * 1.5;
                o.wpos = w;
                o.pos = UnityWorldToClipPos(w);
                o.uv = float3(v.uv, floor(v.x.x * 255.0 + 0.5));
                o.n = mul((float3x3)unity_ObjectToWorld, v.normal);
                o.col = v.color.rgb;
                return o;
            }
            half4 frag (v2f i, fixed facing : VFACE) : SV_Target
            {
                half4 t = UNITY_SAMPLE_TEX2DARRAY(_Tex, i.uv);
                clip(t.a - _Cutoff);
                half3 n = i.n * rsqrt(max(dot(i.n, i.n), 1e-6)) * (facing > 0 ? 1.0h : -1.0h);
                half ndl = saturate(dot(n, _DG_SunDir.xyz)) * 0.7h + 0.3h * saturate(-dot(n, _DG_SunDir.xyz));   // light through the leaves
                half3 c = t.rgb * i.col * (DG_Ambient(half3(0, 1, 0)) * 0.85h + _DG_SunCol.rgb * ndl * _DG_SunDir.w);
                c = DG_Fog(c, i.wpos);
                return half4(c, 1);
            }
            ENDCG
        }
    }
}
