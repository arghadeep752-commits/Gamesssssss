using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Dimnight.EditorTools
{
    /// <summary>
    /// Materials still on a shader URP cannot draw (built-in Standard / Legacy / Mobile / Unlit, ProBuilder's shaders,
    /// AssetRipper dummies with no package version) are moved to URP Lit or URP Unlit, keeping their texture, tiling,
    /// colour, normal map, cut-out and emission. Read straight from the saved properties, so it works whatever shader
    /// the material had.
    /// </summary>
    public static class MaterialFixer
    {
        struct TexEntry { public Texture tex; public Vector2 scale; public Vector2 offset; }

        public static int FixAll()
        {
            Shader lit = Shader.Find("Universal Render Pipeline/Lit");
            Shader unlit = Shader.Find("Universal Render Pipeline/Unlit");
            if (lit == null || unlit == null)
            {
                Debug.LogError("[DIMNIGHT-ERR] URP shaders not found: is com.unity.render-pipelines.universal installed?");
                return 0;
            }
            int n = 0;
            var counts = new Dictionary<string, int>();
            foreach (string guid in AssetDatabase.FindAssets("t:Material", new[] { "Assets" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (path.Contains("/TextMesh Pro/")) continue;
                Material mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat == null) continue;
                string name = mat.shader != null ? mat.shader.name : "(none)";
                if (!NeedsFix(mat.shader, name)) continue;
                ReadSaved(mat, out Dictionary<string, TexEntry> tex, out Dictionary<string, Color> col, out Dictionary<string, float> flt);
                bool wantUnlit = name.StartsWith("Unlit/") || name.Contains("Unlit") || name.StartsWith("Mobile/Unlit");
                mat.shader = wantUnlit ? unlit : lit;
                Apply(mat, tex, col, flt);
                EditorUtility.SetDirty(mat);
                counts[name] = counts.TryGetValue(name, out int c) ? c + 1 : 1;
                n++;
            }
            foreach (var kv in counts) Debug.Log("[DIMNIGHT]   " + kv.Value + " x " + kv.Key);
            AssetDatabase.SaveAssets();
            return n;
        }

        static bool NeedsFix(Shader s, string name)
        {
            if (s == null || name == "Hidden/InternalErrorShader" || !s.isSupported) return true;
            string[] fine = { "Universal Render Pipeline/", "TextMeshPro/", "Skybox/", "UI/", "Sprites/", "Shader Graphs/", "Hidden/", "GUI/" };
            foreach (string f in fine) if (name.StartsWith(f)) return false;
            return true;
        }

        static void ReadSaved(Material mat, out Dictionary<string, TexEntry> tex, out Dictionary<string, Color> col, out Dictionary<string, float> flt)
        {
            tex = new Dictionary<string, TexEntry>();
            col = new Dictionary<string, Color>();
            flt = new Dictionary<string, float>();
            var so = new SerializedObject(mat);
            SerializedProperty envs = so.FindProperty("m_SavedProperties.m_TexEnvs");
            for (int i = 0; envs != null && i < envs.arraySize; i++)
            {
                SerializedProperty e = envs.GetArrayElementAtIndex(i);
                string key = e.FindPropertyRelative("first")?.stringValue;
                SerializedProperty v = e.FindPropertyRelative("second");
                if (string.IsNullOrEmpty(key) || v == null) continue;
                tex[key] = new TexEntry
                {
                    tex = v.FindPropertyRelative("m_Texture").objectReferenceValue as Texture,
                    scale = v.FindPropertyRelative("m_Scale").vector2Value,
                    offset = v.FindPropertyRelative("m_Offset").vector2Value,
                };
            }
            SerializedProperty cols = so.FindProperty("m_SavedProperties.m_Colors");
            for (int i = 0; cols != null && i < cols.arraySize; i++)
            {
                SerializedProperty e = cols.GetArrayElementAtIndex(i);
                string key = e.FindPropertyRelative("first")?.stringValue;
                if (!string.IsNullOrEmpty(key)) col[key] = e.FindPropertyRelative("second").colorValue;
            }
            SerializedProperty floats = so.FindProperty("m_SavedProperties.m_Floats");
            for (int i = 0; floats != null && i < floats.arraySize; i++)
            {
                SerializedProperty e = floats.GetArrayElementAtIndex(i);
                string key = e.FindPropertyRelative("first")?.stringValue;
                if (!string.IsNullOrEmpty(key)) flt[key] = e.FindPropertyRelative("second").floatValue;
            }
        }

        static bool First(Dictionary<string, TexEntry> tex, out TexEntry found, params string[] keys)
        {
            foreach (string k in keys)
                if (tex.TryGetValue(k, out found) && found.tex != null) return true;
            found = default;
            return false;
        }

        static void Apply(Material mat, Dictionary<string, TexEntry> tex, Dictionary<string, Color> col, Dictionary<string, float> flt)
        {
            if (First(tex, out TexEntry main, "_BaseMap", "_MainTex", "_Albedo", "_MainTexture", "_Diffuse", "_BaseColorMap"))
            {
                Vector2 scale = main.scale == Vector2.zero ? Vector2.one : main.scale;
                mat.SetTexture("_BaseMap", main.tex);
                mat.SetTextureScale("_BaseMap", scale);
                mat.SetTextureOffset("_BaseMap", main.offset);
                if (mat.HasProperty("_MainTex")) { mat.SetTexture("_MainTex", main.tex); mat.SetTextureScale("_MainTex", scale); mat.SetTextureOffset("_MainTex", main.offset); }
            }
            Color c = Color.white;
            if (col.TryGetValue("_BaseColor", out Color bc)) c = bc;
            else if (col.TryGetValue("_Color", out Color cc)) c = cc;
            mat.SetColor("_BaseColor", c);
            if (mat.HasProperty("_Color")) mat.SetColor("_Color", c);

            if (mat.HasProperty("_BumpMap") && First(tex, out TexEntry bump, "_BumpMap", "_NormalMap"))
            {
                mat.SetTexture("_BumpMap", bump.tex);
                mat.EnableKeyword("_NORMALMAP");
            }
            float mode = flt.TryGetValue("_Mode", out float m) ? m : 0f;
            if (mode == 1f && mat.HasProperty("_AlphaClip"))
            {
                mat.SetFloat("_AlphaClip", 1f);
                mat.SetFloat("_Cutoff", flt.TryGetValue("_Cutoff", out float cut) ? cut : 0.5f);
                mat.EnableKeyword("_ALPHATEST_ON");
                mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.AlphaTest;
            }
            if (mat.HasProperty("_EmissionColor") && col.TryGetValue("_EmissionColor", out Color em) && em.maxColorComponent > 0.01f)
            {
                mat.SetColor("_EmissionColor", em);
                if (First(tex, out TexEntry emap, "_EmissionMap")) mat.SetTexture("_EmissionMap", emap.tex);
                mat.EnableKeyword("_EMISSION");
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            if (mat.HasProperty("_Smoothness"))
                mat.SetFloat("_Smoothness", flt.TryGetValue("_Glossiness", out float g) ? g : flt.TryGetValue("_Smoothness", out float s) ? s : 0.2f);
        }
    }
}
