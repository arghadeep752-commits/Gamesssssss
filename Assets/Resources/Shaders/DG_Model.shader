// Characters, vehicles and weapons (Hyper3D Rodin textures): albedo, normal map, metal/rough, sky reflection.
Shader "Danga/Model"
{
    Properties
    {
        _MainTex ("Albedo", 2D) = "white" {}
        _BumpMap ("Normal", 2D) = "bump" {}
        _MR ("Metal (B) Rough (G)", 2D) = "white" {}
        _Color ("Tint", Color) = (1, 1, 1, 1)
        _Gloss ("Gloss boost", Float) = 1.0
        _Emis ("Emission", Color) = (0, 0, 0, 0)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "DGCommon.cginc"
            sampler2D _MainTex, _BumpMap, _MR;
            half4 _Color, _Emis;
            float _Gloss;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; float4 tangent : TANGENT; float2 uv : TEXCOORD0; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; half3 n : TEXCOORD1; half3 t : TEXCOORD2; half3 b : TEXCOORD3; float3 wpos : TEXCOORD4; };
            v2f vert (appdata v)
            {
                v2f o;
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.wpos);
                o.uv = v.uv;
                o.n = UnityObjectToWorldNormal(v.normal);
                o.t = UnityObjectToWorldDir(v.tangent.xyz);
                o.b = cross(o.n, o.t) * v.tangent.w * unity_WorldTransformParams.w;
                return o;
            }
            half4 frag (v2f i) : SV_Target
            {
                half4 alb = tex2D(_MainTex, i.uv) * _Color;
                half3 tn = UnpackNormal(tex2D(_BumpMap, i.uv));
                half3 n = normalize(normalize(i.t) * tn.x + normalize(i.b) * tn.y + normalize(i.n) * tn.z);
                half4 mr = tex2D(_MR, i.uv);
                half metal = mr.b;
                half rough = saturate(mr.g / max(0.3h, _Gloss));
                half3 v = normalize(_WorldSpaceCameraPos.xyz - i.wpos);
                half3 diff = alb.rgb * (1.0h - metal * 0.85h) * DG_Light(n, 1.0h);
                half3 h = normalize(_DG_SunDir.xyz + v);
                half spow = exp2(10.0h * (1.0h - rough) + 1.0h);
                half3 spec = _DG_SunCol.rgb * pow(saturate(dot(n, h)), spow) * (1.0h - rough) * _DG_SunDir.w * lerp(0.25h, 1.0h, metal);
                half3 r = reflect(-v, n);
                half3 env = lerp(_DG_GroundCol.rgb, _DG_FogCol.rgb * 1.1h, saturate(r.y * 3.0h + 0.5h));
                half fres = pow(1.0h - saturate(dot(n, v)), 3.0h);
                half3 refl = env * lerp(0.04h + 0.2h * fres, 1.0h, metal) * (1.0h - rough) * lerp(1.0h, alb.rgb, metal);
                half3 c = diff + spec + refl + _Emis.rgb * (0.5h + _DG_Misc.x);
                c = DG_Fog(c, i.wpos);
                return half4(c, 1);
            }
            ENDCG
        }
    }
}
