using UnityEngine;
using UnityEngine.Rendering;

namespace RealFPS
{
    /// <summary>
    /// Applies the Low / Medium / High graphics level: render resolution, shadows,
    /// anti-aliasing, draw distances, grass and post-processing. Also lowers the
    /// render resolution on its own when the frame rate cannot keep up.
    /// </summary>
    public class QualityManager : MonoBehaviour
    {
        public static QualityManager I { get; private set; }

        public Camera cam;
        public Light sun;
        public Terrain terrain;
        public PostFX post;
        public GrassRenderer grass;

        public float RenderScale { get; private set; } = 1f;
        float baseScale = 1f;
        float minScale = 0.55f;
        float fpsTimer;
        int fpsFrames;
        float lastChange;
        int appliedLevel = -1;

        public const int DetailLayer = 8;
        public const int PropLayer = 9;

        void Awake()
        {
            I = this;
        }

        public void Apply()
        {
            GraphicsLevel g = GameSettings.Graphics;
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = GameSettings.Fps60 ? 60 : 30;
            QualitySettings.pixelLightCount = 0;
            QualitySettings.softParticles = false;
            QualitySettings.realtimeReflectionProbes = false;
            QualitySettings.billboardsFaceCameraPosition = false;
            QualitySettings.shadowProjection = ShadowProjection.StableFit;
            QualitySettings.skinWeights = SkinWeights.TwoBones;
            QualitySettings.asyncUploadTimeSlice = 4;

            float shadowDist, lod, detailCull, propCull, terrainError, basemap, grassDist;
            switch (g)
            {
                case GraphicsLevel.Low:
                    baseScale = 0.62f;
                    QualitySettings.shadows = ShadowQuality.HardOnly;
                    QualitySettings.shadowResolution = ShadowResolution.Low;
                    QualitySettings.shadowCascades = 1;
                    QualitySettings.antiAliasing = 0;
                    QualitySettings.anisotropicFiltering = AnisotropicFiltering.Disable;
                    QualitySettings.masterTextureLimit = 1;
                    shadowDist = 28f; lod = 0.55f; detailCull = 24f; propCull = 90f;
                    terrainError = 14f; basemap = 250f; grassDist = 0f;
                    break;
                case GraphicsLevel.High:
                    baseScale = 1.0f;
                    QualitySettings.shadows = ShadowQuality.All;
                    QualitySettings.shadowResolution = ShadowResolution.High;
                    QualitySettings.shadowCascades = 2;
                    QualitySettings.shadowCascade2Split = 0.3f;
                    QualitySettings.antiAliasing = 4;
                    QualitySettings.anisotropicFiltering = AnisotropicFiltering.Enable;
                    QualitySettings.masterTextureLimit = 0;
                    shadowDist = 75f; lod = 1.6f; detailCull = 65f; propCull = 220f;
                    terrainError = 5f; basemap = 1000f; grassDist = 48f;
                    break;
                default:
                    baseScale = 0.8f;
                    QualitySettings.shadows = ShadowQuality.All;
                    QualitySettings.shadowResolution = ShadowResolution.Medium;
                    QualitySettings.shadowCascades = 1;
                    QualitySettings.antiAliasing = 2;
                    QualitySettings.anisotropicFiltering = AnisotropicFiltering.Enable;
                    QualitySettings.masterTextureLimit = 0;
                    shadowDist = 45f; lod = 1.0f; detailCull = 40f; propCull = 150f;
                    terrainError = 8f; basemap = 1000f; grassDist = 30f;
                    break;
            }
            QualitySettings.shadowDistance = shadowDist;
            QualitySettings.lodBias = lod;
            minScale = Mathf.Min(baseScale, 0.55f);

            if (sun != null)
            {
                sun.shadows = g == GraphicsLevel.Low ? LightShadows.Hard : LightShadows.Soft;
                sun.shadowStrength = 0.92f;
                sun.shadowBias = 0.06f;
                sun.shadowNormalBias = 0.5f;
            }
            int msaa = QualitySettings.antiAliasing;
            QualitySettings.antiAliasing = 0;   // MSAA lives on the scene render target, not the screen
            if (cam != null)
            {
                cam.fieldOfView = GameSettings.FieldOfView;
                var cull = new float[32];
                cull[DetailLayer] = detailCull;
                cull[PropLayer] = propCull;
                cam.layerCullDistances = cull;
                cam.layerCullSpherical = true;
            }
            if (post != null)
            {
                post.hdr = g != GraphicsLevel.Low;
                post.msaa = msaa;
                post.effects = g != GraphicsLevel.Low;
                post.bloom = g == GraphicsLevel.High;
            }
            if (terrain != null)
            {
                terrain.heightmapPixelError = terrainError;
                terrain.basemapDistance = basemap;
                terrain.shadowCastingMode = g == GraphicsLevel.High ? ShadowCastingMode.On : ShadowCastingMode.Off;
            }
            if (grass != null)
            {
                grass.SetDistance(grassDist);
            }
            if (appliedLevel != (int)g)
            {
                appliedLevel = (int)g;
                SetScale(baseScale, true);
            }
        }

        /// <summary>Automated tests in a software-rendered emulator: render few pixels, keep everything else.</summary>
        public void ForceScale(float s)
        {
            baseScale = s;
            minScale = s;
            SetScale(s, true);
        }

        void SetScale(float s, bool force)
        {
            s = Mathf.Clamp(s, 0.25f, 1f);
            if (!force && Mathf.Abs(s - RenderScale) < 0.01f) return;
            RenderScale = s;
            if (post != null) post.renderScale = s;
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
            if (Game.I == null || Game.I.State != GameState.Playing) return;
            if (Time.unscaledTime - lastChange < 4f) return;
            float target = Application.targetFrameRate > 0 ? Application.targetFrameRate : 30;
            if (fps < target * 0.82f && RenderScale > minScale + 0.01f)
                SetScale(RenderScale - 0.07f, false);
            else if (fps > target * 0.97f && RenderScale < baseScale - 0.01f && Time.unscaledTime - lastChange > 12f)
                SetScale(Mathf.Min(baseScale, RenderScale + 0.05f), false);
        }
    }
}
