// Soft round shadow under characters and vehicles.
Shader "Danga/Blob"
{
    Properties { _MainTex ("Shape", 2D) = "white" {} _Strength ("Strength", Float) = 0.55 }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent-20" }
        ZWrite Off
        Blend DstColor Zero
        Offset -1, -1
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "DGCommon.cginc"
            sampler2D _MainTex;
            float _Strength;
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };
            v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.uv = v.uv; return o; }
            half4 frag (v2f i) : SV_Target
            {
                half a = tex2D(_MainTex, i.uv).a * _Strength * (0.4h + 0.6h * _DG_SunDir.w);
                return half4(1.0h - a, 1.0h - a, 1.0h - a, 1);
            }
            ENDCG
        }
    }
}
