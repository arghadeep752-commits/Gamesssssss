// Moulika ma'am: her own colour, normal and metal/roughness textures, lit by the night ambient light and the
// nearest lamps of the school plus the faint cold glow in front of her face (the game passes up to five lights).
// Godot equivalent: StandardMaterial3D lit by OmniLight3D (inverse-distance falloff with a smooth edge at the range).
Shader "Moulika/Character"
{
    Properties
    {
        _MainTex ("Colour", 2D) = "white" {}
        _BumpMap ("Normal map", 2D) = "bump" {}
        _MR ("Metal (B) roughness (G)", 2D) = "white" {}
        _Ambient ("Ambient light (linear)", Vector) = (0.068, 0.084, 0.143, 0)
        _Bright ("Brightness", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        Pass
        {
            Cull Off
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "MoulikaCommon.cginc"

            sampler2D _MainTex;
            sampler2D _BumpMap;
            sampler2D _MR;
            float4 _Ambient;
            float _Bright;
            float4 _LPos[5];   // xyz = world position, w = range (0 = off)
            float4 _LCol[5];   // rgb = linear colour * energy

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float4 tangent : TANGENT;
                float2 uv : TEXCOORD0;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 wpos : TEXCOORD1;
                float3 wn : TEXCOORD2;
                float3 wt : TEXCOORD3;
                float3 wb : TEXCOORD4;
            };

            v2f vert(appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.wn = UnityObjectToWorldNormal(v.normal);
                o.wt = UnityObjectToWorldDir(v.tangent.xyz);
                o.wb = cross(o.wn, o.wt) * v.tangent.w * unity_WorldTransformParams.w;
                return o;
            }

            float4 frag(v2f i, float facing : VFACE) : SV_Target
            {
                float3 albedo = tex2D(_MainTex, i.uv).rgb;
                float4 mr = tex2D(_MR, i.uv);
                float rough = clamp(mr.g, 0.08, 1.0);
                float metal = mr.b;
                float3 tn = UnpackNormal(tex2D(_BumpMap, i.uv));
                float side = facing > 0 ? 1.0 : -1.0;
                float3 n = normalize(tn.x * i.wt + tn.y * i.wb + tn.z * i.wn * side);
                float3 v = normalize(_WorldSpaceCameraPos.xyz - i.wpos);

                float3 diffuse = _Ambient.rgb;
                float3 spec = 0;
                float shin = 2.0 / max(rough * rough * rough * rough, 0.002) - 2.0;
                float specAmt = (1.0 - rough) * (1.0 - rough) * 0.5;
                [unroll]
                for (int k = 0; k < 5; k++)
                {
                    float range = max(_LPos[k].w, 0.0001);
                    float on = _LPos[k].w > 0.0 ? 1.0 : 0.0;
                    float3 L = _LPos[k].xyz - i.wpos;
                    float d = max(length(L), 0.0001);
                    L /= d;
                    float nd = d / range;
                    nd = nd * nd;
                    nd = nd * nd;
                    nd = saturate(1.0 - nd);
                    float att = on * nd * nd / max(d, 0.25);
                    float ndl = saturate(dot(n, L));
                    diffuse += _LCol[k].rgb * att * ndl;
                    float3 h = normalize(L + v);
                    spec += _LCol[k].rgb * att * ndl * pow(saturate(dot(n, h)), shin) * specAmt;
                }
                float3 col = (albedo * (1.0 - metal) * diffuse + spec) * _Bright;
                return float4(MoulikaFinish(col, distance(i.wpos, _WorldSpaceCameraPos.xyz)), 1.0);
            }
            ENDCG
        }
    }
    Fallback Off
}
