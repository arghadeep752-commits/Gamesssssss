using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace NightClass.EditorTools
{
    /// <summary>
    /// Sets up the Universal Render Pipeline for the three graphics profiles:
    ///
    ///  - one URP pipeline asset per profile (Low / Medium / High) sharing one forward renderer,
    ///  - three quality levels named Low / Medium / High that point at those assets (Android
    ///    starts on Medium; the game then picks a level from the phone's GPU and memory),
    ///  - the post-processing volume profile (tonemapping, colour grading, bloom, vignette).
    ///
    /// Settings are written through SerializedObject so the script works across URP versions;
    /// every setting that could not be found is reported in the build log.
    /// </summary>
    public static class NCRenderSetup
    {
        public const string Dir = "Assets/Settings";

        public class Profile
        {
            public string name;
            public int msaa;
            public float shadowDistance;
            public int shadowResolution;
            public int cascades;
            public float cascade2Split;
            public bool softShadows;
            public int softShadowQuality;   // 1 low, 2 medium, 3 high
            public float lodBias;
            public int upscaling;           // UpscalingFilterSelection: 0 auto, 1 linear, 2 point, 3 FSR
        }

        // Mali-G52-class phones (Galaxy A21s) start on Low, mid-range phones on Medium, flagships on High.
        public static readonly Profile[] Profiles =
        {
            new Profile { name = "Low", msaa = 2, shadowDistance = 20f, shadowResolution = 1024, cascades = 1, cascade2Split = 0.25f,
                          softShadows = false, softShadowQuality = 1, lodBias = 0.7f, upscaling = 1 },
            new Profile { name = "Medium", msaa = 2, shadowDistance = 25f, shadowResolution = 1024, cascades = 1, cascade2Split = 0.25f,
                          softShadows = true, softShadowQuality = 1, lodBias = 1f, upscaling = 3 },
            new Profile { name = "High", msaa = 4, shadowDistance = 30f, shadowResolution = 2048, cascades = 1, cascade2Split = 0.25f,
                          softShadows = true, softShadowQuality = 2, lodBias = 1.5f, upscaling = 3 },
        };

        static void Log(string m) { Debug.Log("[RF-BUILD] " + m); }

        public static UniversalRenderPipelineAsset[] Setup()
        {
            NCBuild.EnsureFolder(Dir);
            UniversalRendererData renderer = CreateRenderer();
            var assets = new UniversalRenderPipelineAsset[Profiles.Length];
            for (int i = 0; i < Profiles.Length; i++) assets[i] = CreatePipelineAsset(Profiles[i], renderer);
            GraphicsSettings.defaultRenderPipeline = assets[1];
            SetupQualityLevels(assets);
            AssetDatabase.SaveAssets();
            RenderPipelineGlobalSettings global = GraphicsSettings.GetSettingsForRenderPipeline<UniversalRenderPipeline>();
            Log("URP ready: default " + assets[1].name + ", global settings " + (global != null ? AssetDatabase.GetAssetPath(global) : "MISSING") +
                ", quality levels " + string.Join("/", QualitySettings.names));
            return assets;
        }

        // ------------------------------------------------------------------ renderer
        static UniversalRendererData CreateRenderer()
        {
            string path = Dir + "/ForwardRenderer.asset";
            AssetDatabase.DeleteAsset(path);
            var rd = ScriptableObject.CreateInstance<UniversalRendererData>();
            AssetDatabase.CreateAsset(rd, path);
            var post = AssetDatabase.LoadAssetAtPath<PostProcessData>("Packages/com.unity.render-pipelines.universal/Runtime/Data/PostProcessData.asset");
            if (post != null) rd.postProcessData = post;
            else Debug.LogWarning("[RF-BUILD] default PostProcessData not found");
            var so = new SerializedObject(rd);
            Set(so, "m_RenderingMode", 0);              // forward
            Set(so, "m_DepthPrimingMode", 0);           // no depth prepass
            Set(so, "m_IntermediateTextureMode", 0);    // auto
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(rd);
            return rd;
        }

        // ------------------------------------------------------------------ pipeline assets
        static UniversalRenderPipelineAsset CreatePipelineAsset(Profile p, UniversalRendererData renderer)
        {
            string path = Dir + "/URP-" + p.name + ".asset";
            AssetDatabase.DeleteAsset(path);
            UniversalRenderPipelineAsset asset = UniversalRenderPipelineAsset.Create(renderer);
            asset.name = "URP-" + p.name;
            AssetDatabase.CreateAsset(asset, path);

            var so = new SerializedObject(asset);
            Set(so, "m_RequireDepthTexture", false);
            Set(so, "m_RequireOpaqueTexture", false);
            Set(so, "m_SupportsTerrainHoles", false);
            Set(so, "m_SupportsHDR", true);
            Set(so, "m_HDRColorBufferPrecision", 0);        // 32-bit (R11G11B10): same bandwidth as LDR
            Set(so, "m_MSAA", p.msaa);
            Set(so, "m_RenderScale", 1f);
            Set(so, "m_UpscalingFilter", p.upscaling);
            Set(so, "m_EnableLODCrossFade", false);
            Set(so, "m_MainLightRenderingMode", 1);          // per pixel
            Set(so, "m_MainLightShadowsSupported", false);   // no sun: moonlight is faked with soft spots
            Set(so, "m_MainLightShadowmapResolution", p.shadowResolution);
            Set(so, "m_AdditionalLightsRenderingMode", 1);   // per pixel: the school is lit by many lamps
            Set(so, "m_AdditionalLightsPerObjectLimit", p.name == "Low" ? 3 : 4);
            Set(so, "m_AdditionalLightShadowsSupported", false);
            Set(so, "m_ReflectionProbeBlending", false);
            Set(so, "m_ReflectionProbeBoxProjection", false);
            Set(so, "m_ShadowDistance", p.shadowDistance);
            Set(so, "m_ShadowCascadeCount", p.cascades);
            Set(so, "m_Cascade2Split", p.cascade2Split);
            Set(so, "m_CascadeBorder", 0.15f);
            Set(so, "m_ShadowDepthBias", 1.1f);
            Set(so, "m_ShadowNormalBias", 1.0f);
            Set(so, "m_SoftShadowsSupported", p.softShadows);
            Set(so, "m_SoftShadowQuality", p.softShadowQuality);
            Set(so, "m_UseSRPBatcher", true);
            Set(so, "m_SupportsDynamicBatching", false);
            Set(so, "m_MixedLightingSupported", false);
            Set(so, "m_SupportsLightCookies", false);
            Set(so, "m_SupportsLightLayers", false);
            Set(so, "m_ColorGradingMode", 1);                // HDR grading
            Set(so, "m_ColorGradingLutSize", 32);
            Set(so, "m_UseFastSRGBLinearConversion", true);
            Set(so, "m_GPUResidentDrawerMode", 0);
            Set(so, "m_SupportDataDrivenLensFlare", false);
            Set(so, "m_SupportScreenSpaceLensFlare", false);
            Set(so, "m_UseAdaptivePerformance", false);
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(asset);
            Log("pipeline asset " + asset.name + ": msaa " + asset.msaaSampleCount + ", shadows " + asset.shadowDistance + " m @" +
                asset.mainLightShadowmapResolution + " x" + asset.shadowCascadeCount + ", hdr " + asset.supportsHDR + ", srp batcher " + asset.useSRPBatcher);
            return asset;
        }

        // ------------------------------------------------------------------ quality levels
        static void SetupQualityLevels(UniversalRenderPipelineAsset[] assets)
        {
            Object[] objs = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/QualitySettings.asset");
            if (objs == null || objs.Length == 0)
            {
                Debug.LogWarning("[RF-BUILD] QualitySettings.asset not found; using the API fallback");
                QualityFallback(assets);
                return;
            }
            var so = new SerializedObject(objs[0]);
            SerializedProperty levels = so.FindProperty("m_QualitySettings");
            if (levels == null || !levels.isArray)
            {
                Debug.LogWarning("[RF-BUILD] m_QualitySettings not found; using the API fallback");
                QualityFallback(assets);
                return;
            }
            levels.arraySize = assets.Length;
            for (int i = 0; i < assets.Length; i++)
            {
                Profile p = Profiles[i];
                SerializedProperty q = levels.GetArrayElementAtIndex(i);
                SetRel(q, "name", p.name);
                SetRel(q, "customRenderPipeline", assets[i]);
                SetRel(q, "pixelLightCount", 0);
                SetRel(q, "shadows", 0);
                SetRel(q, "antiAliasing", 0);                 // MSAA lives in the URP asset
                SetRel(q, "softParticles", false);
                SetRel(q, "softVegetation", false);
                SetRel(q, "realtimeReflectionProbes", false);
                SetRel(q, "billboardsFaceCameraPosition", false);
                SetRel(q, "vSyncCount", 0);
                SetRel(q, "lodBias", p.lodBias);
                SetRel(q, "maximumLODLevel", 0);
                SetRel(q, "anisotropicTextures", 1);          // per-texture anisotropic levels (set on import)
                SetRelOptional(q, "globalTextureMipmapLimit", 0);
                SetRelOptional(q, "textureQuality", 0);
                SetRelOptional(q, "streamingMipmapsActive", false);
                SetRelOptional(q, "asyncUploadTimeSlice", 4);
                SetRelOptional(q, "asyncUploadBufferSize", 32);
                SetRelOptional(q, "particleRaycastBudget", 16);
                SetRelOptional(q, "skinWeights", 2);
                SetRelOptional(q, "terrainQualityOverrides", 0);
                SetRelOptional(q, "enableLODCrossFade", false);
            }
            SerializedProperty cur = so.FindProperty("m_CurrentQuality");
            if (cur != null) cur.intValue = 1;
            SerializedProperty perPlatform = so.FindProperty("m_PerPlatformDefaultQuality");
            if (perPlatform != null && perPlatform.isArray)
            {
                bool found = false;
                for (int i = 0; i < perPlatform.arraySize; i++)
                {
                    SerializedProperty e = perPlatform.GetArrayElementAtIndex(i);
                    SerializedProperty first = e.FindPropertyRelative("first");
                    SerializedProperty second = e.FindPropertyRelative("second");
                    if (first == null || second == null) continue;
                    if (second.intValue >= assets.Length) second.intValue = 1;
                    if (first.stringValue == "Android") { second.intValue = 1; found = true; }
                }
                if (!found)
                {
                    perPlatform.arraySize++;
                    SerializedProperty e = perPlatform.GetArrayElementAtIndex(perPlatform.arraySize - 1);
                    SerializedProperty first = e.FindPropertyRelative("first");
                    SerializedProperty second = e.FindPropertyRelative("second");
                    if (first != null) first.stringValue = "Android";
                    if (second != null) second.intValue = 1;
                }
            }
            so.ApplyModifiedPropertiesWithoutUndo();
            AssetDatabase.SaveAssets();
            if (QualitySettings.names.Length != assets.Length)
            {
                Debug.LogWarning("[RF-BUILD] quality levels not applied (" + QualitySettings.names.Length + "); using the API fallback");
                QualityFallback(assets);
            }
            QualitySettings.SetQualityLevel(1, true);
            for (int i = 0; i < QualitySettings.names.Length && i < assets.Length; i++)
            {
                RenderPipelineAsset rp = QualitySettings.GetRenderPipelineAssetAt(i);
                Log("quality level " + i + " '" + QualitySettings.names[i] + "' -> " + (rp != null ? rp.name : "none"));
            }
        }

        /// <summary>If the quality settings file has an unexpected layout: assign assets level by level.</summary>
        static void QualityFallback(UniversalRenderPipelineAsset[] assets)
        {
            int n = QualitySettings.names.Length;
            for (int i = 0; i < n; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                int profile = Mathf.Clamp(i * assets.Length / Mathf.Max(1, n), 0, assets.Length - 1);
                QualitySettings.renderPipeline = assets[profile];
            }
            QualitySettings.SetQualityLevel(Mathf.Min(1, n - 1), true);
        }

        // ------------------------------------------------------------------ post-processing
        public static VolumeProfile CreateVolumeProfile()
        {
            string path = Dir + "/PostProcessing.asset";
            AssetDatabase.DeleteAsset(path);
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(profile, path);

            // night-school grade: ACES filmic tonemapping, cold shadows, warm lamp highlights,
            // deep vignette and film grain; bloom on the lamps (Medium/High)
            var tone = Add<Tonemapping>(profile);
            tone.mode.Override(TonemappingMode.ACES);

            var color = Add<ColorAdjustments>(profile);
            color.postExposure.Override(0.85f);
            color.contrast.Override(18f);
            color.saturation.Override(-14f);

            var wb = Add<WhiteBalance>(profile);
            wb.temperature.Override(-8f);
            wb.tint.Override(2f);

            var split = Add<SplitToning>(profile);
            split.shadows.Override(new Color(0.32f, 0.48f, 0.56f));
            split.highlights.Override(new Color(0.78f, 0.6f, 0.42f));
            split.balance.Override(-15f);

            var lgg = Add<LiftGammaGain>(profile);
            lgg.lift.Override(new Vector4(0.98f, 1f, 1.03f, -0.02f));
            lgg.gamma.Override(new Vector4(1f, 1f, 1f, -0.02f));
            lgg.gain.Override(new Vector4(1.03f, 1f, 0.97f, 0.02f));

            var bloom = Add<Bloom>(profile);
            bloom.threshold.Override(0.95f);
            bloom.intensity.Override(0.65f);
            bloom.scatter.Override(0.7f);
            bloom.tint.Override(new Color(1f, 0.92f, 0.82f));
            bloom.highQualityFiltering.Override(false);

            var vignette = Add<Vignette>(profile);
            vignette.intensity.Override(0.38f);
            vignette.smoothness.Override(0.5f);
            vignette.color.Override(new Color(0.01f, 0.01f, 0.015f));

            var grain = Add<FilmGrain>(profile);
            grain.type.Override(FilmGrainLookup.Medium3);
            grain.intensity.Override(0.32f);
            grain.response.Override(0.75f);

            var ca = Add<ChromaticAberration>(profile);
            ca.intensity.Override(0.12f);

            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
            Log("post-processing profile: " + profile.components.Count + " effects");
            return profile;
        }

        static T Add<T>(VolumeProfile profile) where T : VolumeComponent
        {
            T c = profile.Add<T>(false);
            c.name = typeof(T).Name;
            AssetDatabase.AddObjectToAsset(c, profile);
            return c;
        }

        // ------------------------------------------------------------------ SerializedObject helpers
        static void Set(SerializedObject so, string name, object value)
        {
            SerializedProperty p = so.FindProperty(name);
            if (p == null)
            {
                Debug.LogWarning("[RF-BUILD] setting not found on " + so.targetObject.GetType().Name + ": " + name);
                return;
            }
            Assign(p, value, so.targetObject.GetType().Name);
        }

        static void SetRel(SerializedProperty parent, string name, object value)
        {
            SerializedProperty p = parent.FindPropertyRelative(name);
            if (p == null)
            {
                Debug.LogWarning("[RF-BUILD] quality setting not found: " + name);
                return;
            }
            Assign(p, value, "QualitySettings");
        }

        static void SetRelOptional(SerializedProperty parent, string name, object value)
        {
            SerializedProperty p = parent.FindPropertyRelative(name);
            if (p != null) Assign(p, value, "QualitySettings");
        }

        static void Assign(SerializedProperty p, object value, string owner)
        {
            try
            {
                switch (p.propertyType)
                {
                    case SerializedPropertyType.Boolean: p.boolValue = Convert.ToBoolean(value); break;
                    case SerializedPropertyType.Integer:
                    case SerializedPropertyType.Enum:
                    case SerializedPropertyType.LayerMask: p.intValue = Convert.ToInt32(value); break;
                    case SerializedPropertyType.Float: p.floatValue = Convert.ToSingle(value); break;
                    case SerializedPropertyType.String: p.stringValue = Convert.ToString(value); break;
                    case SerializedPropertyType.ObjectReference: p.objectReferenceValue = value as Object; break;
                    default:
                        Debug.LogWarning("[RF-BUILD] cannot set " + owner + "." + p.propertyPath + " (" + p.propertyType + ")");
                        break;
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning("[RF-BUILD] could not set " + owner + "." + p.propertyPath + ": " + e.Message);
            }
        }
    }
}
