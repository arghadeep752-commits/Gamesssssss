Shader "RealFPS/Water"
{
    Properties
    {
        _ShallowColor ("Shallow colour", Color) = (0.30, 0.38, 0.30, 1)
        _DeepColor ("Deep colour", Color) = (0.035, 0.085, 0.095, 1)
        _NormalMap ("Normal map", 2D) = "bump" {}
        _DepthTex ("Depth (R)", 2D) = "black" {}
        _DepthRect ("Depth rect (xMin, zMin, 1/width, 1/depth)", Vector) = (0, 0, 1, 1)
        _MaxDepth ("Depth of R=1 (m)", Float) = 8
        _Sky ("Sky panorama", 2D) = "white" {}
        _SkyRotation ("Sky rotation", Float) = 0
        _Wave ("Wave tiling A, B, strength", Vector) = (0.045, 0.12, 0.42, 0)
        _WaveSpeed ("Wave speed", Vector) = (0.011, 0.007, -0.009, 0.013)
        _SunPower ("Sun glint power", Float) = 420
        _SunStrength ("Sun glint strength", Float) = 2.2
        _ReflectStrength ("Reflection strength", Range(0, 1.5)) = 0.95
    }

    SubShader
    {
        Tags { "Queue" = "Transparent-50" "RenderType" = "Transparent" "IgnoreProjector" = "True" }
        LOD 200

        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Back

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "UnityLightingCommon.cginc"

            sampler2D _NormalMap;
            sampler2D _DepthTex;
            sampler2D _Sky;
            float4 _DepthRect;
            float4 _Wave;
            float4 _WaveSpeed;
            half4 _ShallowColor;
            half4 _DeepColor;
            float _MaxDepth;
            float _SkyRotation;
            float _SunPower;
            float _SunStrength;
            float _ReflectStrength;

            struct appdata
            {
                float4 vertex : POSITION;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 wpos : TEXCOORD0;
                UNITY_FOG_COORDS(1)
            };

            v2f vert(appdata v)
            {
                v2f o;
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.wpos);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            // Same mapping as Unity's Skybox/Panoramic shader (with its _Rotation).
            half3 SampleSky(float3 d, float lod)
            {
                float a = radians(_SkyRotation);
                float s = sin(a);
                float c = cos(a);
                float3 r = normalize(float3(c * d.x + s * d.z, d.y, -s * d.x + c * d.z));
                float2 uv = float2(0.5 - atan2(r.z, r.x) / (2.0 * UNITY_PI), 1.0 - acos(clamp(r.y, -1.0, 1.0)) / UNITY_PI);
                return tex2Dlod(_Sky, float4(uv, 0.0, lod)).rgb;
            }

            half4 frag(v2f i) : SV_Target
            {
                float2 uv1 = i.wpos.xz * _Wave.x + _Time.y * _WaveSpeed.xy;
                float2 uv2 = i.wpos.xz * _Wave.y + _Time.y * _WaveSpeed.zw;
                half3 n1 = UnpackNormal(tex2D(_NormalMap, uv1));
                half3 n2 = UnpackNormal(tex2D(_NormalMap, uv2));
                float3 V = _WorldSpaceCameraPos - i.wpos;
                float dist = length(V);
                V /= max(dist, 1e-3);
                float2 nxy = (n1.xy + n2.xy) * _Wave.z * (0.25 + 0.75 * saturate(1.0 - dist / 260.0));
                float3 N = normalize(float3(nxy.x, 1.0, nxy.y));

                float3 R = reflect(-V, N);
                R.y = abs(R.y);
                half3 sky = SampleSky(R, saturate(dist / 140.0) * 3.0) * _ReflectStrength;
                half fres = 0.02 + 0.98 * pow(1.0 - saturate(dot(N, V)), 5.0);

                float2 duv = (i.wpos.xz - _DepthRect.xy) * _DepthRect.zw;
                half depth = tex2D(_DepthTex, duv).r * _MaxDepth;
                half3 body = lerp(_ShallowColor.rgb, _DeepColor.rgb, saturate(depth / 3.0));
                half3 L = _WorldSpaceLightPos0.xyz;
                half3 ambient = ShadeSH9(half4(0.0, 1.0, 0.0, 1.0));
                body *= _LightColor0.rgb * saturate(L.y) * 0.5 + ambient;

                half3 col = lerp(body, sky, fres);
                half3 H = normalize(L + V);
                half spec = pow(saturate(dot(N, H)), _SunPower) * _SunStrength;
                col += _LightColor0.rgb * spec;

                half alpha = saturate(depth * 1.4 + fres * 0.7);
                alpha = saturate(max(alpha, spec));
                UNITY_APPLY_FOG(i.fogCoord, col);
                return half4(col, alpha);
            }
            ENDCG
        }
    }
    Fallback Off
}
