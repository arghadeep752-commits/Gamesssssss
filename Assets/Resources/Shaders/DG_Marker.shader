// Glowing column on the ground for the shops, the house and the hospital (needs no vertex colours).
Shader "Danga/Marker"
{
    Properties { _Color ("Colour", Color) = (1, 0.8, 0.2, 0.5) }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" }
        ZWrite Off
        Cull Off
        Blend SrcAlpha One
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            half4 _Color;
            struct appdata { float4 vertex : POSITION; };
            struct v2f { float4 pos : SV_POSITION; float h : TEXCOORD0; };
            v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.h = saturate(v.vertex.y * 0.5 + 0.5); return o; }
            half4 frag (v2f i) : SV_Target { return half4(_Color.rgb, _Color.a * (1.0 - i.h) * (1.0 - i.h)); }
            ENDCG
        }
    }
}
