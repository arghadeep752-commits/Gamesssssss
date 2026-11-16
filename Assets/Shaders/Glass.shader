// Window glass: unlit, see-through, both sides (mats.gd: glass / glass_dirty).
Shader "Moulika/Glass"
{
    Properties
    {
        _Color ("Colour (linear, alpha = opacity)", Vector) = (0.25, 0.32, 0.34, 0.22)
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "IgnoreProjector" = "True" }
        Pass
        {
            Cull Off
            ZWrite Off
            Blend SrcAlpha OneMinusSrcAlpha
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            #include "MoulikaCommon.cginc"

            float4 _Color;

            struct v2f
            {
                float4 pos : SV_POSITION;
                float dist : TEXCOORD0;
            };

            v2f vert(float4 vertex : POSITION)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(vertex);
                float3 wp = mul(unity_ObjectToWorld, vertex).xyz;
                o.dist = distance(wp, _WorldSpaceCameraPos.xyz);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                return float4(MoulikaFinish(_Color.rgb, i.dist), _Color.a);
            }
            ENDCG
        }
    }
    Fallback Off
}
