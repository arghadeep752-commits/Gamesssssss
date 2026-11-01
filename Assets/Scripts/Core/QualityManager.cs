using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace RealFPS
{
    /// <summary>
    /// Applies the Low / Medium / High graphics profile.
    ///
    /// Each profile is a Unity quality level with its own URP asset (shadow resolution,
    /// cascades and distance, MSAA, HDR, soft shadows - see RFRenderSetup in the editor
    /// folder). On top of that this script sets the parts that live on scene objects:
    /// render resolution, terrain detail, grass distance and density, tree detail
    /// distances, culling distances for small props and which post effects are active.
    ///
    /// Render resolution: the short side of the screen is rendered at up to 720 px (Low),
    /// 900 px (Medium) or 1080 px (High), never above the screen's own resolution, so a
    /// 720p phone renders at native resolution. If the frame rate stays below the target,
    /// the resolution drops a little at a time (down to ~72%) and recovers when the frame
    /// rate does.
    /// </summary>
    public class QualityManager : MonoBehaviour
    {
        public static QualityManager I { get; private set; }

        public Camera cam;
        public Light sun;
        public Terrain terrain;
        public TreeRenderer trees;
        public Volume volume;

        public float RenderScale { get; private set; } = 1f;
        public GraphicsLevel Level { get; private set; } = GraphicsLevel.Medium;

        float baseScale = 1f;
        float minScale = 0.7f;
        float fpsTimer;
        int fpsFrames;
        float lastChange;
        bool forced;

        public const int DetailLayer = 8;
        public const int PropLayer = 9;

        static UniversalRenderPipelineAsset Urp
        {
            get { return GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset; }
        }

        void Awake()
        {
            I = this;
        }

        public void Apply()
        {
            GraphicsLevel g = GameSettings.Graphics;
            Level = g;
            int index = (int)g;
            if (index < QualitySettings.names.Length && QualitySettings.GetQualityLevel() != index)
                QualitySettings.SetQualityLevel(index, true);
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = GameSettings.Fps60 ? 60 : 30;

            float targetShort, detailDist, detailDensity, pixelError, basemap, lodScale, lodBias, detailCull, propCull;
            switch (g)
            {
                case GraphicsLevel.Low:
                    targetShort = 720f; detailDist = 16f; detailDensity = 0.35f; pixelError = 10f; basemap = 150f;
                    lodScale = 0.7f; lodBias = 0.6f; detailCull = 28f; propCull = 110f;
                    break;
                case GraphicsLevel.High:
                    targetShort = 1080f; detailDist = 42f; detailDensity = 1f; pixelError = 4f; basemap = 400f;
                    lodScale = 1.35f; lodBias = 1.5f; detailCull = 70f; propCull = 240f;
                    break;
                default:
                    targetShort = 900f; detailDist = 28f; detailDensity = 0.65f; pixelError = 6f; basemap = 250f;
                    lodScale = 1f; lodBias = 1f; detailCull = 45f; propCull = 170f;
                    break;
            }
            QualitySettings.lodBias = lodBias;

            float shortSide = Mathf.Max(1f, Mathf.Min(Screen.width, Screen.height));
            if (!forced)
            {
                baseScale = Mathf.Clamp(targetShort / shortSide, 0.5f, 1f);
                minScale = Mathf.Max(0.5f, baseScale * 0.72f);
            }

            UniversalRenderPipelineAsset urp = Urp;
            float shadowDistance = urp != null ? urp.shadowDistance : 40f;
            if (terrain != null)
            {
                terrain.heightmapPixelError = pixelError;
                terrain.basemapDistance = basemap;
                terrain.detailObjectDistance = detailDist;
                terrain.detailObjectDensity = detailDensity;
                terrain.drawInstanced = RenderCompat.UseInstancing;
            }
            if (trees != null)
            {
                trees.lodScale = lodScale;
                trees.shadowDistance = Mathf.Min(shadowDistance, 70f);
            }
            if (cam != null)
            {
                cam.fieldOfView = GameSettings.FieldOfView;
                var cull = new float[32];
                cull[DetailLayer] = detailCull;
                cull[PropLayer] = propCull;
                cam.layerCullDistances = cull;
                cam.layerCullSpherical = true;
            }
            ApplyVolume(g);
            SetScale(baseScale, true);
            Debug.Log("[RF] graphics " + g + " (quality level " + QualitySettings.GetQualityLevel() + " '" + QualitySettings.names[QualitySettings.GetQualityLevel()] + "')" +
                      " urp=" + (urp != null ? urp.name : "none") + " shadows=" + shadowDistance + "m msaa=" + (urp != null ? urp.msaaSampleCount : 0) +
                      " hdr=" + (urp != null && urp.supportsHDR) + " scale=" + RenderScale.ToString("0.00") + " target " + Application.targetFrameRate + " fps");
        }

        void ApplyVolume(GraphicsLevel g)
        {
            if (volume == null || volume.sharedProfile == null) return;
            VolumeProfile p = volume.profile;   // a runtime copy; the asset stays untouched
            Bloom bloom;
            if (p.TryGet(out bloom)) bloom.active = g == GraphicsLevel.High;
            Vignette vignette;
            if (p.TryGet(out vignette)) vignette.active = g != GraphicsLevel.Low;
            FilmGrain grain;
            if (p.TryGet(out grain)) grain.active = false;
        }

        /// <summary>Automated tests in a software-rendered emulator: render fewer pixels, keep everything else.</summary>
        public void ForceScale(float s)
        {
            forced = true;
            baseScale = s;
            minScale = s;
            SetScale(s, true);
        }

        void SetScale(float s, bool force)
        {
            s = Mathf.Clamp(s, 0.25f, 1f);
            if (!force && Mathf.Abs(s - RenderScale) < 0.01f) return;
            RenderScale = s;
            UniversalRenderPipelineAsset urp = Urp;
            if (urp != null) urp.renderScale = s;
            lastChange = Time.unscaledTime;
            Debug.Log("[RF] render scale " + s.ToString("0.00"));
        }

        void Update()
        {
            // Dynamic resolution: if the frame rate stays well below the target, render fewer pixels.
            fpsFrames++;
            fpsTimer += Time.unscaledDeltaTime;
            if (fpsTimer < 2.5f) return;
            float fps = fpsFrames / fpsTimer;
            fpsFrames = 0;
            fpsTimer = 0f;
            if (forced || Game.I == null || Game.I.State != GameState.Playing) return;
            if (Time.unscaledTime - lastChange < 4f) return;
            float target = Application.targetFrameRate > 0 ? Application.targetFrameRate : 30;
            if (fps < target * 0.85f && RenderScale > minScale + 0.01f)
                SetScale(Mathf.Max(minScale, RenderScale - 0.06f), false);
            else if (fps > target * 0.97f && RenderScale < baseScale - 0.01f && Time.unscaledTime - lastChange > 12f)
                SetScale(Mathf.Min(baseScale, RenderScale + 0.05f), false);
        }
    }
}
