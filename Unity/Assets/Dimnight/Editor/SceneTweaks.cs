using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Dimnight.EditorTools
{
    /// <summary>
    /// Changes made to Granny 4 EndGame's own scenes: the game's name on every text becomes "Granny Dimnight", blood
    /// decals go (a clean house), and each scene reports what still needs work (missing scripts, broken materials).
    /// </summary>
    public static class SceneTweaks
    {
        static readonly Regex OldName = new Regex(@"granny\s*4\s*[:\-]?\s*(the\s+)?end\s*game|granny\s*4", RegexOptions.IgnoreCase);

        static void Log(string message) { Debug.Log("[DIMNIGHT] " + message); }

        public static void Apply(string scenePath)
        {
            Scene scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
            GameObject[] roots = scene.GetRootGameObjects();
            int renamed = RenameTexts(roots);
            int blood = HideBlood(roots);
            Report(scene.name, roots);
            if (renamed + blood > 0)
            {
                EditorSceneManager.MarkSceneDirty(scene);
                EditorSceneManager.SaveScene(scene);
            }
            Log(scene.name + ": " + renamed + " texts renamed, " + blood + " blood decals hidden");
        }

        static string NewName(Match m)
        {
            string s = m.Value;
            if (s == s.ToUpperInvariant()) return "GRANNY DIMNIGHT";
            if (s == s.ToLowerInvariant()) return "granny dimnight";
            return "Granny Dimnight";
        }

        static int RenameTexts(GameObject[] roots)
        {
            int n = 0;
            foreach (GameObject root in roots)
            {
                foreach (var t in root.GetComponentsInChildren<TMPro.TMP_Text>(true))
                {
                    if (string.IsNullOrEmpty(t.text) || !OldName.IsMatch(t.text)) continue;
                    Undo.RecordObject(t, "rename");
                    t.text = OldName.Replace(t.text, NewName);
                    EditorUtility.SetDirty(t);
                    n++;
                }
                foreach (var t in root.GetComponentsInChildren<UnityEngine.UI.Text>(true))
                {
                    if (string.IsNullOrEmpty(t.text) || !OldName.IsMatch(t.text)) continue;
                    t.text = OldName.Replace(t.text, NewName);
                    EditorUtility.SetDirty(t);
                    n++;
                }
            }
            return n;
        }

        static int HideBlood(GameObject[] roots)
        {
            int n = 0;
            foreach (GameObject root in roots)
                foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                {
                    bool bloody = r.sharedMaterials.Any(m => m != null &&
                        (m.name.ToLowerInvariant().Contains("blood") ||
                         (m.mainTexture != null && m.mainTexture.name.ToLowerInvariant().Contains("blood"))));
                    if (!bloody || !r.enabled) continue;
                    r.enabled = false;
                    EditorUtility.SetDirty(r);
                    n++;
                }
            return n;
        }

        static void Report(string sceneName, GameObject[] roots)
        {
            int objects = 0, missing = 0, renderers = 0, broken = 0;
            var missingOn = new List<string>();
            var lights = new Dictionary<LightType, int>();
            foreach (GameObject root in roots)
                foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                {
                    objects++;
                    int m = GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject);
                    if (m > 0) { missing += m; if (missingOn.Count < 15) missingOn.Add(t.name); }
                    var r = t.GetComponent<Renderer>();
                    if (r != null)
                    {
                        renderers++;
                        if (r.sharedMaterials.Any(x => x == null || x.shader == null || x.shader.name == "Hidden/InternalErrorShader")) broken++;
                    }
                    var l = t.GetComponent<Light>();
                    if (l != null) lights[l.type] = lights.TryGetValue(l.type, out int c) ? c + 1 : 1;
                }
            Log(sceneName + ": " + objects + " objects, " + renderers + " renderers (" + broken + " with broken materials), "
                + missing + " missing scripts" + (missingOn.Count > 0 ? " on " + string.Join(", ", missingOn) : "")
                + ", lights " + string.Join(" ", lights.Select(kv => kv.Value + "x" + kv.Key))
                + ", fog " + RenderSettings.fog + " " + RenderSettings.fogMode + " " + RenderSettings.fogDensity
                + ", ambient " + RenderSettings.ambientMode + " " + RenderSettings.ambientSkyColor);
        }
    }
}
