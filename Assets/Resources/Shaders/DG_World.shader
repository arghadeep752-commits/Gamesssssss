// Map geometry: one texture array for every surface (layer index per vertex), tint, ambient occlusion, emissive at night.
Shader "Danga/World"
{
    Properties
    {
        _Tex ("Layers", 2DArray) = "" {}
        _Nrm ("Normal layers", 2DArray) = "" {}
        _Ground ("Ground shadows (0/1)", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma require 2darray
            #pragma multi_compile __ DG_NORMALMAP
            #include "DGCommon.cginc"
            UNITY_DECLARE_TEX2DARRAY(_Tex);
            UNITY_DECLARE_TEX2DARRAY(_Nrm);
            float _Ground;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; float4 color : COLOR; float2 uv : TEXCOORD0; float4 x : TEXCOORD1; };
            struct v2f { float4 pos : SV_POSITION; float3 uv : TEXCOORD0; half3 n : TEXCOORD1; float3 wpos : TEXCOORD2; half4 col : TEXCOORD3; half ao : TEXCOORD4; };
            v2f vert (appdata v)
            {
                v2f o;
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.wpos);
                o.uv = float3(v.uv, floor(v.x.x * 255.0 + 0.5));
                o.n = mul((float3x3)unity_ObjectToWorld, v.normal);
                o.col = v.color;
                o.ao = v.x.y;
                return o;
            }
            half4 frag (v2f i) : SV_Target
            {
                half4 t = UNITY_SAMPLE_TEX2DARRAY(_Tex, i.uv);
                half3 n = i.n * rsqrt(max(dot(i.n, i.n), 1e-6));
#ifdef DG_NORMALMAP
                half3 tn = UNITY_SAMPLE_TEX2DARRAY(_Nrm, i.uv).xyz * 2.0h - 1.0h;
                // cheap tangent frame from the normal (good enough for walls and floors)
                half3 tx = normalize(abs(n.y) > 0.7h ? cross(n, half3(0, 0, 1)) : cross(half3(0, 1, 0), n));
                half3 ty = cross(n, tx);
                n = normalize(tx * tn.x * 0.7h + ty * tn.y * 0.7h + n * tn.z);
#endif
                half ao = max(i.ao, 0.25h);
                if (_Ground > 0.5) ao *= DG_GroundShadow(i.wpos);
                half3 c = t.rgb * i.col.rgb * DG_Light(n, ao);
                // windows, sign boards and lamps light up at night
                c += t.rgb * i.col.rgb * i.col.a * (0.15h + 1.6h * _DG_Misc.x) * _DG_Misc.w;
                c = DG_Fog(c, i.wpos);
                return half4(c, 1);
            }
            ENDCG
        }
    }
}
