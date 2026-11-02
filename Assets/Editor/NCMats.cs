using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace NightClass.EditorTools
{
    /// <summary>Creates and caches the URP materials (textures from tools/process_assets.py).</summary>
    public static class NCMats
    {
        public const string TexDir = "Assets/Art/Tex/";
        public const string DecalDir = "Assets/Art/Decals/";
        public const string FxDir = "Assets/Art/FX/";
        public const string MatDir = "Assets/Generated/Materials";
        static readonly Dictionary<string, Material> cache = new Dictionary<string, Material>();
        static readonly Dictionary<Material, float> uv = new Dictionary<Material, float>();
        static int missing;

        public static void Reset()
        {
            cache.Clear();
            uv.Clear();
            missing = 0;
            NCBuild.EnsureFolder(MatDir);
        }

        public static void SetUV(Material m, float repeatsPerMetre) { if (m != null) uv[m] = repeatsPerMetre; }

        public static float UVScale(Material m)
        {
            float s;
            return m != null && uv.TryGetValue(m, out s) ? s : 1f;
        }

        public static Texture2D Tex(string pathNoExt)
        {
            foreach (string ext in new[] { ".png", ".jpg" })
            {
                var t = AssetDatabase.LoadAssetAtPath<Texture2D>(pathNoExt + ext);
                if (t != null) return t;
            }
            return null;
        }

        /// <summary>URP Lit with optional texture set "slot" (albedo / normal / mask).</summary>
        public static Material Lit(string key, string slot, Color tint, float smoothness = 0.3f, float metallic = 0f,
                                   float repeatsPerMetre = 0.5f, Color? emission = null, float normalScale = 1f, Texture2D albedoOverride = null)
        {
            Material m;
            if (cache.TryGetValue(key, out m)) return m;
            Shader sh = Shader.Find("Universal Render Pipeline/Lit");
            m = new Material(sh) { name = key };
            Texture2D alb = albedoOverride != null ? albedoOverride : (slot != null ? Tex(TexDir + slot + "_albedo") : null);
            if (slot != null && alb == null && albedoOverride == null) missing++;
            if (alb != null) m.SetTexture("_BaseMap", alb);
            m.SetColor("_BaseColor", tint);
            Texture2D nrm = slot != null ? Tex(TexDir + slot + "_normal") : null;
            if (nrm != null)
            {
                m.SetTexture("_BumpMap", nrm);
                m.SetFloat("_BumpScale", normalScale);
                m.EnableKeyword("_NORMALMAP");
            }
            Texture2D mask = slot != null ? Tex(TexDir + slot + "_mask") : null;
            if (mask != null)
            {
                m.SetTexture("_MetallicGlossMap", mask);
                m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetTexture("_OcclusionMap", mask);
                m.EnableKeyword("_OCCLUSIONMAP");
                m.SetFloat("_OcclusionStrength", 1f);
                m.SetFloat("_SmoothnessTextureChannel", 0f);
            }
            m.SetFloat("_Smoothness", smoothness);
            m.SetFloat("_Metallic", metallic);
            m.SetFloat("_EnvironmentReflections", 0f);
            m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            if (emission.HasValue)
            {
                m.EnableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", emission.Value);
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            }
            Save(m, key);
            uv[m] = repeatsPerMetre;
            cache[key] = m;
            return m;
        }

        /// <summary>Lit material showing one picture (posters, chalkboard, notes, face).</summary>
        public static Material Picture(string key, string file, Color tint, float smoothness = 0.2f, Color? emission = null, bool cutout = false)
        {
            Material m;
            if (cache.TryGetValue(key, out m)) return m;
            Texture2D tex = Tex(DecalDir + file);
            if (tex == null) tex = Tex("Assets/Art/Teacher/" + file);
            m = Lit(key, null, tint, smoothness, 0f, 1f, emission, 1f, tex);
            if (cutout)
            {
                m.SetFloat("_AlphaClip", 1f);
                m.SetFloat("_Cutoff", 0.5f);
                m.EnableKeyword("_ALPHATEST_ON");
                m.SetOverrideTag("RenderType", "TransparentCutout");
                m.renderQueue = (int)RenderQueue.AlphaTest;
            }
            if (emission.HasValue && tex != null) { m.SetTexture("_EmissionMap", tex); }
            EditorUtility.SetDirty(m);
            return m;
        }

        public static Material Custom(string key, string shader, System.Action<Material> setup)
        {
            Material m;
            if (cache.TryGetValue(key, out m)) return m;
            Shader sh = Shader.Find(shader);
            if (sh == null)
            {
                Debug.LogWarning("[RF-BUILD] shader not found: " + shader);
                sh = Shader.Find("Universal Render Pipeline/Unlit");
            }
            m = new Material(sh) { name = key };
            if (setup != null) setup(m);
            Save(m, key);
            cache[key] = m;
            return m;
        }

        public static Material Particle(string key, string fxFile, Color tint, bool additive)
        {
            return Custom(key, additive ? "NightClass/ParticleAdd" : "NightClass/ParticleAlpha", m =>
            {
                Texture2D t = Tex(FxDir + fxFile);
                if (t != null) m.SetTexture("_BaseMap", t);
                m.SetColor("_BaseColor", tint);
            });
        }

        static void Save(Material m, string key)
        {
            string path = MatDir + "/" + key + ".mat";
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(m, path);
        }

        public static void Report()
        {
            Debug.Log("[RF-BUILD] materials: " + cache.Count + " (texture sets missing: " + missing + ")");
        }
    }
}
