using UnityEngine;

namespace RealFPS
{
    /// <summary>
    /// Renders the 3D scene at a lower resolution (render scale) into an HDR target and
    /// presents it on screen with filmic post-processing: optional bloom, exposure,
    /// white balance, contrast, saturation, ACES tone mapping, vignette and dithering.
    /// Lives on a "present" camera that draws nothing itself, so the UI stays sharp
    /// and changing the render scale never touches the screen surface.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class PostFX : MonoBehaviour
    {
        public Shader shader;
        public Camera sceneCamera;
        [Range(0.25f, 1f)] public float renderScale = 1f;
        public bool hdr = true;
        public int msaa = 2;
        public bool effects = true;
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
        RenderTexture sceneRT;
        RenderTextureFormat hdrFormat;
        bool supported;
        static readonly int BloomTex = Shader.PropertyToID("_BloomTex");

        public int SceneWidth { get { return sceneRT != null ? sceneRT.width : Screen.width; } }
        public int SceneHeight { get { return sceneRT != null ? sceneRT.height : Screen.height; } }

        void OnEnable()
        {
            supported = shader != null && shader.isSupported;
            if (supported && mat == null) mat = new Material(shader) { hideFlags = HideFlags.HideAndDontSave };
            hdrFormat = SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.RGB111110Float) ? RenderTextureFormat.RGB111110Float :
                        (SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.ARGBHalf) ? RenderTextureFormat.ARGBHalf : RenderTextureFormat.ARGB32);
        }

        void OnDisable()
        {
            ReleaseTarget();
        }

        void OnDestroy()
        {
            ReleaseTarget();
            if (mat != null) Destroy(mat);
        }

        void ReleaseTarget()
        {
            if (sceneCamera != null) sceneCamera.targetTexture = null;
            if (sceneRT != null)
            {
                sceneRT.Release();
                Destroy(sceneRT);
                sceneRT = null;
            }
        }

        void LateUpdate()
        {
            if (sceneCamera == null) return;
            int w = Mathf.Max(64, Mathf.RoundToInt(Screen.width * renderScale));
            int h = Mathf.Max(64, Mathf.RoundToInt(Screen.height * renderScale));
            RenderTextureFormat fmt = hdr ? hdrFormat : RenderTextureFormat.ARGB32;
            int aa = msaa >= 4 ? 4 : (msaa >= 2 ? 2 : 1);
            if (sceneRT != null && sceneRT.width == w && sceneRT.height == h && sceneRT.format == fmt && sceneRT.antiAliasing == aa) return;
            ReleaseTarget();
            sceneRT = new RenderTexture(w, h, 24, fmt, RenderTextureReadWrite.Default)
            {
                name = "SceneColor",
                antiAliasing = aa,
                filterMode = FilterMode.Bilinear,
                useMipMap = false
            };
            if (!sceneRT.Create())
            {
                // MSAA / format not available: fall back to the simplest target
                sceneRT.Release();
                sceneRT = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Default) { name = "SceneColor", filterMode = FilterMode.Bilinear };
                sceneRT.Create();
            }
            sceneCamera.targetTexture = sceneRT;
            sceneCamera.allowMSAA = sceneRT.antiAliasing > 1;
            sceneCamera.allowHDR = sceneRT.format != RenderTextureFormat.ARGB32;
            Debug.Log("[RF] scene target " + w + "x" + h + " " + sceneRT.format + " msaa " + sceneRT.antiAliasing);
        }

        void OnRenderImage(RenderTexture src, RenderTexture dst)
        {
            RenderTexture source = sceneRT != null ? sceneRT : src;
            if (!effects || !supported)
            {
                Graphics.Blit(source, dst);
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
                RenderTextureFormat bf = hdrFormat;
                int w = Mathf.Max(1, source.width / 2), h = Mathf.Max(1, source.height / 2);
                b1 = RenderTexture.GetTemporary(w, h, 0, bf);
                b2 = RenderTexture.GetTemporary(Mathf.Max(1, w / 2), Mathf.Max(1, h / 2), 0, bf);
                b3 = RenderTexture.GetTemporary(Mathf.Max(1, w / 4), Mathf.Max(1, h / 4), 0, bf);
                b1.filterMode = b2.filterMode = b3.filterMode = FilterMode.Bilinear;
                Graphics.Blit(source, b1, mat, 0);  // threshold + downsample
                Graphics.Blit(b1, b2, mat, 1);      // downsample
                Graphics.Blit(b2, b3, mat, 1);
                Graphics.Blit(b3, b2, mat, 2);      // upsample, added on top
                Graphics.Blit(b2, b1, mat, 2);
                mat.SetTexture(BloomTex, b1);
            }
            else
            {
                mat.DisableKeyword("BLOOM");
            }
            Graphics.Blit(source, dst, mat, 3);
            if (b1 != null) RenderTexture.ReleaseTemporary(b1);
            if (b2 != null) RenderTexture.ReleaseTemporary(b2);
            if (b3 != null) RenderTexture.ReleaseTemporary(b3);
        }
    }
}
