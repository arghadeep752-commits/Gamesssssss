// The photographed sky (Poly Haven HDRI as a panorama), blended to the night sky, with the sun disc.
Shader "Danga/Sky"
{
    Properties
    {
        _Day ("Day panorama", 2D) = "grey" {}
        _Night ("Night panorama", 2D) = "black" {}
        _Rot ("Rotation", Float) = 0
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" }
        Cull Off ZWrite Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "DGCommon.cginc"
            sampler2D _Day, _Night;
            float _Rot;
            struct appdata { float4 vertex : POSITION; };
            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; };
            v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.dir = v.vertex.xyz; return o; }
            half4 frag (v2f i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float lon = atan2(d.x, d.z) / (2.0 * UNITY_PI) + 0.5 + _Rot;
                float lat = asin(clamp(d.y, -1.0, 1.0)) / UNITY_PI + 0.5;
                float2 uv = float2(lon, lat);
                half3 day = tex2Dlod(_Day, float4(uv, 0, 0)).rgb;
                half3 night = tex2Dlod(_Night, float4(uv, 0, 0)).rgb;
                half3 c = lerp(day * (0.35h + 0.65h * _DG_SunDir.w), night, _DG_Misc.x);
                half s = saturate(dot(d, _DG_SunDir.xyz));
                c += _DG_SunCol.rgb * (pow(s, 900.0h) * 6.0h + pow(s, 12.0h) * 0.18h) * _DG_SunDir.w;
                // haze towards the horizon so the fog meets the sky
                c = lerp(c, _DG_FogCol.rgb, saturate(1.0h - abs(d.y) * 7.0h) * 0.75h);
                return half4(DG_Grade(c), 1);
            }
            ENDCG
        }
    }
}
