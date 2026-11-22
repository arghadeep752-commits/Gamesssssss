// Rivers, ponds, the lake and the sea: animated ripples, sky reflection with fresnel, sun glints, shore colour.
Shader "Danga/Water"
{
    Properties
    {
        _Deep ("Deep colour", Color) = (0.04, 0.16, 0.22, 1)
        _Shallow ("Shallow colour", Color) = (0.15, 0.32, 0.30, 1)
        _Sky ("Sky reflection colour", Color) = (0.55, 0.68, 0.82, 1)
        _Waves ("Wave size", Float) = 1.0
        _Alpha ("Opacity", Float) = 0.88
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent-10" }
        ZWrite Off
        Blend SrcAlpha OneMinusSrcAlpha
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "DGCommon.cginc"
            half4 _Deep, _Shallow, _Sky;
            float _Waves, _Alpha;
            struct appdata { float4 vertex : POSITION; float4 color : COLOR; };
            struct v2f { float4 pos : SV_POSITION; float3 wpos : TEXCOORD0; half4 col : TEXCOORD1; };
            v2f vert (appdata v)
            {
                v2f o;
                float3 w = mul(unity_ObjectToWorld, v.vertex).xyz;
                float t = _DG_Misc.y;
                w.y += (sin(w.x * 0.05 + t * 0.9) * 0.18 + sin(w.z * 0.07 + t * 1.3) * 0.12) * _Waves * v.color.r;
                o.wpos = w;
                o.pos = UnityWorldToClipPos(w);
                o.col = v.color;
                return o;
            }
            half4 frag (v2f i) : SV_Target
            {
                float t = _DG_Misc.y;
                float2 p = i.wpos.xz;
                // ripple normal from a few travelling waves
                float2 g = float2(0, 0);
                g += cos(dot(p, float2(0.31, 0.17)) + t * 1.9) * float2(0.31, 0.17) * 0.6;
                g += cos(dot(p, float2(-0.21, 0.37)) + t * 2.3) * float2(-0.21, 0.37) * 0.5;
                g += cos(dot(p, float2(0.93, -0.61)) + t * 3.7) * float2(0.93, -0.61) * 0.12;
                g += cos(dot(p, float2(-1.4, -1.1)) + t * 4.4) * float2(-1.4, -1.1) * 0.06;
                half3 n = normalize(half3(-g.x * 0.35 * _Waves, 1.0h, -g.y * 0.35 * _Waves));
                half3 v = normalize(_WorldSpaceCameraPos.xyz - i.wpos);
                half fres = pow(1.0h - saturate(dot(n, v)), 4.0h) * 0.85h + 0.08h;
                half depth = saturate(i.col.r);
                half3 water = lerp(_Shallow.rgb, _Deep.rgb, depth) * (DG_Ambient(half3(0, 1, 0)) + _DG_SunCol.rgb * _DG_SunDir.w * 0.3h);
                half3 sky = lerp(_DG_FogCol.rgb, _Sky.rgb * (0.4h + 0.6h * _DG_SunDir.w), saturate(reflect(-v, n).y * 2.0h));
                half3 c = lerp(water, sky, fres);
                half3 h = normalize(_DG_SunDir.xyz + v);
                c += _DG_SunCol.rgb * pow(saturate(dot(n, h)), 180.0h) * 2.5h * _DG_SunDir.w;
                c = DG_Fog(c, i.wpos);
                return half4(c, lerp(_Alpha, 1.0, fres * 0.5));
            }
            ENDCG
        }
    }
}
