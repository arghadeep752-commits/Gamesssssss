// Additive glow: lamp heads, light pools at night, muzzle flashes, head lights, the rotor blur.
Shader "Danga/Glow"
{
    Properties
    {
        _MainTex ("Shape", 2D) = "white" {}
        _Color ("Colour", Color) = (1, 0.9, 0.7, 1)
        _NightOnly ("Night only", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" }
        ZWrite Off
        Blend SrcAlpha One
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "DGCommon.cginc"
            sampler2D _MainTex;
            half4 _Color;
            float _NightOnly;
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; float4 color : COLOR; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; half4 col : TEXCOORD1; };
            v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.uv = v.uv; o.col = v.color * _Color; return o; }
            half4 frag (v2f i) : SV_Target
            {
                half a = tex2D(_MainTex, i.uv).a * i.col.a * lerp(1.0h, _DG_Misc.x, _NightOnly);
                return half4(i.col.rgb, a);
            }
            ENDCG
        }
    }
}
