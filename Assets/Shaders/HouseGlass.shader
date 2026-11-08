// Window panes, glass railings and shower screens: a faint tint plus reflections of the surroundings.
Shader "GridProto/HouseGlass"
{
    Properties
    {
        _Color ("Tint", Color) = (0.8, 0.88, 0.9, 1)
        _Alpha ("Opacity", Range(0, 1)) = 0.16
    }
    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        LOD 100

        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            ZWrite Off
            Blend SrcAlpha OneMinusSrcAlpha
            Cull Back

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "UnityStandardUtils.cginc"

            fixed4 _Color;
            half _Alpha;
            half _HouseExposure;
            half _HouseProbeExposure;

            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 wpos : TEXCOORD0;
                half3 wn : TEXCOORD1;
                UNITY_FOG_COORDS(2)
            };

            v2f vert (appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.wn = UnityObjectToWorldNormal(v.normal);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                half3 n = normalize(i.wn);
                half3 v = normalize(_WorldSpaceCameraPos - i.wpos);
                half3 r = reflect(-v, n);
                r = BoxProjectedCubemapDirection(r, i.wpos, unity_SpecCube0_ProbePosition, unity_SpecCube0_BoxMin, unity_SpecCube0_BoxMax);
                half3 env = DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0, r, 0.5), unity_SpecCube0_HDR);
                half exposure = _HouseExposure > 0.0 ? _HouseExposure : 1.0;
                half probeExposure = _HouseProbeExposure > 0.0 ? _HouseProbeExposure : exposure;
                env *= saturate(exposure / probeExposure);
                half nv = saturate(dot(n, v));
                half fres = 0.04 + 0.96 * pow(1.0 - nv, 5.0);
                half3 col = lerp(_Color.rgb * 0.25, env, saturate(0.35 + fres));
                half a = saturate(_Alpha + fres * 0.55);
                UNITY_APPLY_FOG(i.fogCoord, col);
                return fixed4(col, a);
            }
            ENDCG
        }
    }
    FallBack Off
}
