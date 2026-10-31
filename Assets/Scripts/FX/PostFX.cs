using UnityEngine;

namespace RealFPS
{
    /// <summary>
    /// Light-weight filmic post-processing for mobile (built-in render pipeline):
    /// optional bloom, exposure, white balance, contrast, saturation, ACES tone
    /// mapping, vignette and dithering in a single final pass.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class PostFX : MonoBehaviour
    {
        public Shader shader;
        public bool bloom = true;
        public float exposure = 0.95f;
        public float contrast = 1.06f;
        public float saturation = 1.1f;
        public Color colorFilter = new Color(1.02f, 1.0f, 0.97f, 1f);
        public float vignette = 0.32f;
        public float bloomThreshold = 1.05f;
        public float bloomKnee = 0.5f;
        public float bloomIntensity = 0.32f;

        Material mat;
        RenderTextureFormat hdrFormat;
        static readonly int BloomTex = Shader.PropertyToID("_BloomTex");

        void OnEnable()
        {
            if (shader == null || !shader.isSupported)
            {
                enabled = false;
                return;
            }
            if (mat == null) mat = new Material(shader) { hideFlags = HideFlags.HideAndDontSave };
            hdrFormat = SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.RGB111110Float) ? RenderTextureFormat.RGB111110Float :
                        (SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.ARGBHalf) ? RenderTextureFormat.ARGBHalf : RenderTextureFormat.Default);
        }

        void OnDestroy()
        {
            if (mat != null) Destroy(mat);
        }

        void OnRenderImage(RenderTexture src, RenderTexture dst)
        {
            if (mat == null)
            {
                Graphics.Blit(src, dst);
                return;
            }
            mat.SetFloat("_Exposure", exposure);
            mat.SetFloat("_Contrast", contrast);
            mat.SetFloat("_Saturation", saturation);
            mat.SetColor("_ColorFilter", colorFilter);
            mat.SetFloat("_Vignette", vignette);

            RenderTexture b1 = null, b2 = null, b3 = null;
            if (bloom)
            {
                mat.EnableKeyword("BLOOM");
                mat.SetFloat("_Threshold", bloomThreshold);
                mat.SetFloat("_Knee", bloomKnee);
                mat.SetFloat("_BloomIntensity", bloomIntensity);
                int w = Mathf.Max(1, src.width / 2), h = Mathf.Max(1, src.height / 2);
                b1 = RenderTexture.GetTemporary(w, h, 0, hdrFormat);
                b2 = RenderTexture.GetTemporary(Mathf.Max(1, w / 2), Mathf.Max(1, h / 2), 0, hdrFormat);
                b3 = RenderTexture.GetTemporary(Mathf.Max(1, w / 4), Mathf.Max(1, h / 4), 0, hdrFormat);
                b1.filterMode = b2.filterMode = b3.filterMode = FilterMode.Bilinear;
                Graphics.Blit(src, b1, mat, 0);  // threshold + downsample
                Graphics.Blit(b1, b2, mat, 1);   // downsample
                Graphics.Blit(b2, b3, mat, 1);
                Graphics.Blit(b3, b2, mat, 2);   // upsample, added on top
                Graphics.Blit(b2, b1, mat, 2);
                mat.SetTexture(BloomTex, b1);
            }
            else
            {
                mat.DisableKeyword("BLOOM");
            }
            Graphics.Blit(src, dst, mat, 3);
            if (b1 != null) RenderTexture.ReleaseTemporary(b1);
            if (b2 != null) RenderTexture.ReleaseTemporary(b2);
            if (b3 != null) RenderTexture.ReleaseTemporary(b3);
        }
    }
}
