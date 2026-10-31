Shader "RealFPS/Distant"
{
    // Cheap lit shader for the far mountain ring (vertex colours + a large-scale detail texture).
    Properties
    {
        _Detail ("Detail", 2D) = "gray" {}
        _DetailScale ("Detail scale", Float) = 0.015
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry+10" }
        LOD 100

        CGPROGRAM
        #pragma surface surf Lambert nolightmap nodynlightmap nodirlightmap nometa noforwardadd noshadow exclude_path:deferred exclude_path:prepass
        #pragma multi_compile_instancing
        #pragma target 3.0

        sampler2D _Detail;
        float _DetailScale;

        struct Input
        {
            fixed4 color : COLOR;
            float3 worldPos;
        };

        void surf(Input IN, inout SurfaceOutput o)
        {
            half d = tex2D(_Detail, IN.worldPos.xz * _DetailScale).g;
            o.Albedo = IN.color.rgb * (0.7 + 0.6 * d);
        }
        ENDCG
    }
    Fallback "Diffuse"
}
