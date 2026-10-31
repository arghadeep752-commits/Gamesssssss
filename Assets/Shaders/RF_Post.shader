Shader "Hidden/RealFPS/Post"
{
    Properties
    {
        _MainTex ("Source", 2D) = "white" {}
    }

    CGINCLUDE
    #include "UnityCG.cginc"

    sampler2D _MainTex;
    float4 _MainTex_TexelSize;
    sampler2D _BloomTex;
    float _Threshold, _Knee, _BloomIntensity;
    float _Exposure, _Contrast, _Saturation, _Vignette;
    float4 _ColorFilter;

    struct v2f
    {
        float4 pos : SV_POSITION;
        float2 uv : TEXCOORD0;
    };

    v2f vert(appdata_img v)
    {
        v2f o;
        o.pos = UnityObjectToClipPos(v.vertex);
        o.uv = v.texcoord.xy;
        return o;
    }

    half3 Box4(float2 uv, float2 d)
    {
        half3 s = tex2D(_MainTex, uv + float2(-d.x, -d.y)).rgb;
        s += tex2D(_MainTex, uv + float2(d.x, -d.y)).rgb;
        s += tex2D(_MainTex, uv + float2(-d.x, d.y)).rgb;
        s += tex2D(_MainTex, uv + float2(d.x, d.y)).rgb;
        return s * 0.25;
    }

    half4 fragPrefilter(v2f i) : SV_Target
    {
        half3 c = Box4(i.uv, _MainTex_TexelSize.xy);
        half br = max(c.r, max(c.g, c.b));
        half soft = clamp(br - _Threshold + _Knee, 0.0, 2.0 * _Knee);
        soft = soft * soft / (4.0 * _Knee + 1e-4);
        half contrib = max(soft, br - _Threshold) / max(br, 1e-4);
        return half4(min(c * contrib, 30.0), 1.0);
    }

    half4 fragDown(v2f i) : SV_Target
    {
        return half4(Box4(i.uv, _MainTex_TexelSize.xy), 1.0);
    }

    half4 fragUp(v2f i) : SV_Target
    {
        return half4(Box4(i.uv, _MainTex_TexelSize.xy * 0.5), 1.0);
    }

    float3 ACESFilm(float3 x)
    {
        return saturate((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14));
    }

    half4 fragUber(v2f i) : SV_Target
    {
        float3 c = tex2D(_MainTex, i.uv).rgb;
        #if defined(BLOOM)
        c += tex2D(_BloomTex, i.uv).rgb * _BloomIntensity;
        #endif
        c = max(c * _Exposure * _ColorFilter.rgb, 0.0);
        c = pow(c / 0.18 + 1e-5, _Contrast) * 0.18;
        float l = dot(c, float3(0.2126, 0.7152, 0.0722));
        c = max(lerp(l.xxx, c, _Saturation), 0.0);
        c = ACESFilm(c);
        float2 d = i.uv - 0.5;
        d.x *= _ScreenParams.x / _ScreenParams.y * 0.62;
        c *= saturate(1.0 - dot(d, d) * _Vignette * 2.0);
        // dither in a perceptual space to avoid banding in the sky
        float n = frac(sin(dot(i.uv * _ScreenParams.xy, float2(12.9898, 78.233))) * 43758.5453);
        c = sqrt(c);
        c += (n - 0.5) / 255.0;
        c = c * c;
        return half4(c, 1.0);
    }
    ENDCG

    SubShader
    {
        Cull Off ZWrite Off ZTest Always

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment fragPrefilter
            ENDCG
        }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment fragDown
            ENDCG
        }
        Pass
        {
            Blend One One
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment fragUp
            ENDCG
        }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment fragUber
            #pragma multi_compile __ BLOOM
            ENDCG
        }
    }
    Fallback Off
}
