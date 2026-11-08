// Soft contact shadows (ambient occlusion) under blocks and along walls.
// Multiplies whatever is already drawn, so it darkens the floor without lighting cost.
Shader "GridProto/ContactShadow"
{
    Properties
    {
        _MainTex ("Mask", 2D) = "black" {}
    }
    SubShader
    {
        Tags { "Queue" = "Geometry+10" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        LOD 100

        Pass
        {
            Tags { "LightMode" = "Always" }
            ZWrite Off
            Blend DstColor Zero
            Offset -1, -1

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "UnityCG.cginc"

            sampler2D _MainTex;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                fixed4 color : COLOR;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                fixed strength : TEXCOORD1;
                UNITY_FOG_COORDS(2)
            };

            v2f vert (appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                o.strength = v.color.a;
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                fixed m = tex2D(_MainTex, i.uv).r * i.strength;
                fixed4 col = fixed4(1.0 - m, 1.0 - m, 1.0 - m, 1.0);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, col, fixed4(1, 1, 1, 1));
                return col;
            }
            ENDCG
        }
    }
}
