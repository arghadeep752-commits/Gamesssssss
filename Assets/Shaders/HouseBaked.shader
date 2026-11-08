// Surfaces of the Blender-made house. The lighting (sun, sky, lamps and bounced light) was baked in Blender
// with Cycles into the mesh (UV2 = light per vertex), so this shader only multiplies it with the texture,
// adds reflections from the room's reflection probe and applies the camera exposure and a film curve.
Shader "GridProto/HouseBaked"
{
    Properties
    {
        _MainTex ("Albedo", 2D) = "white" {}
        _Color ("Color", Color) = (1, 1, 1, 1)
        _Glossiness ("Smoothness", Range(0, 1)) = 0.2
        _Metallic ("Metallic", Range(0, 1)) = 0
        _EmissionLin ("Emission (linear)", Vector) = (0, 0, 0, 0)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        LOD 200

        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "UnityStandardUtils.cginc"

            sampler2D _MainTex;
            float4 _MainTex_ST;
            fixed4 _Color;
            half _Glossiness;
            half _Metallic;
            float4 _EmissionLin;
            half _HouseExposure;
            half _HouseProbeExposure;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float2 uv : TEXCOORD0;
                float3 light : TEXCOORD1;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                half3 light : TEXCOORD1;
                float3 wpos : TEXCOORD2;
                half3 wn : TEXCOORD3;
                UNITY_FOG_COORDS(4)
            };

            v2f vert (appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = TRANSFORM_TEX(v.uv, _MainTex);
                o.light = v.light;
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.wn = UnityObjectToWorldNormal(v.normal);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            // filmic curve (ACES fit), keeps bright sunlit walls and lamps from clipping harshly
            half3 Film (half3 x)
            {
                x *= 0.62;
                return saturate((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14));
            }

            fixed4 frag (v2f i) : SV_Target
            {
                half3 albedo = tex2D(_MainTex, i.uv).rgb * _Color.rgb;
                half exposure = _HouseExposure > 0.0 ? _HouseExposure : 1.0;
                half3 n = normalize(i.wn);
                half3 v = normalize(_WorldSpaceCameraPos - i.wpos);
                half3 lit = albedo * (1.0 - _Metallic * 0.85) * i.light + _EmissionLin.rgb;
                half3 col = Film(lit * exposure);

                // reflection of the room (box-projected probe), stronger at grazing angles
                half3 r = reflect(-v, n);
                r = BoxProjectedCubemapDirection(r, i.wpos, unity_SpecCube0_ProbePosition, unity_SpecCube0_BoxMin, unity_SpecCube0_BoxMax);
                half rough = 1.0 - _Glossiness;
                half mip = rough * (1.7 - 0.7 * rough) * 6.0;
                half3 env = DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0, r, mip), unity_SpecCube0_HDR);
                half probeExposure = _HouseProbeExposure > 0.0 ? _HouseProbeExposure : exposure;
                env *= saturate(exposure / probeExposure);
                half nv = saturate(dot(n, v));
                half3 f0 = lerp(half3(0.04, 0.04, 0.04), albedo, _Metallic);
                half3 fres = f0 + (max(half3(_Glossiness, _Glossiness, _Glossiness), f0) - f0) * pow(1.0 - nv, 5.0);
                half occlusion = saturate(dot(i.light, half3(0.3, 0.59, 0.11)) * exposure * 2.5);
                half3 spec = env * fres * occlusion * (_Glossiness * _Glossiness * 0.85 + _Metallic * 0.15);
                col = col * (1.0 - fres * _Metallic * 0.6) + spec;

                UNITY_APPLY_FOG(i.fogCoord, col);
                return fixed4(col, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
