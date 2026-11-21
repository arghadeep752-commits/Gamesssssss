// Monitor screens, the keypad light, the LED strip: unlit, glowing, with faint scan lines on the screens.
// _On = 0 shows a dark glossy screen.
Shader "TradersMadness/Screen"
{
    Properties
    {
        _MainTex ("Picture", 2D) = "white" {}
        _Color ("Glow colour (linear)", Color) = (1, 1, 1, 1)
        _On ("Switched on", Float) = 1
        _Bright ("Brightness", Float) = 1.4
        _Lines ("Scan lines", Float) = 1
        _Off ("Colour when off (linear)", Vector) = (0.012, 0.014, 0.02, 0)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        Pass
        {
            Cull Back
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            #include "TMCommon.cginc"

            sampler2D _MainTex;
            float4 _Color;
            float _On;
            float _Bright;
            float _Lines;
            float4 _Off;

            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float dist : TEXCOORD1; };

            v2f vert(appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                o.dist = distance(mul(unity_ObjectToWorld, v.vertex).xyz, _WorldSpaceCameraPos.xyz);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                float3 pic = tex2D(_MainTex, i.uv).rgb * _Color.rgb * _Bright;
                float sl = 1.0 - _Lines * 0.12 * (0.5 + 0.5 * sin(i.uv.y * 900.0));
                float3 col = lerp(_Off.rgb, pic * sl, saturate(_On));
                return float4(TMFinish(col, i.dist), 1.0);
            }
            ENDCG
        }
    }
    Fallback Off
}
