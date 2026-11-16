using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
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
            int navmeshes = BakeNavMeshes(scene, roots);
            int occlusion = ClearOcclusionData(scene.name);
            Report(scene.name, roots);
            ReportCamerasAndVolumes(scene.name, roots);
            ReportNavMeshReach(scene.name, roots);
            if (renamed + blood + navmeshes + occlusion > 0)
            {
                EditorSceneManager.MarkSceneDirty(scene);
                EditorSceneManager.SaveScene(scene);
            }
            Log(scene.name + ": " + renamed + " texts renamed, " + blood + " blood decals hidden, " + navmeshes + " navmeshes baked");
        }

        /// <summary>
        /// Occlusion data exported from the original build points at the old scene's renderers: it can hide the whole
        /// house from the camera, so it is cleared (the house is small, Unity's frustum culling is enough).
        /// </summary>
        static int ClearOcclusionData(string sceneName)
        {
            int size = StaticOcclusionCulling.umbraDataSize;
            if (size <= 0) return 0;
            StaticOcclusionCulling.Clear();
            Log(sceneName + ": old occlusion culling data cleared (" + size + " bytes)");
            return 1;
        }

        static string Path(Transform t)
        {
            string p = t.name;
            while (t.parent != null) { t = t.parent; p = t.name + "/" + p; }
            return p;
        }

        static void ReportCamerasAndVolumes(string sceneName, GameObject[] roots)
        {
            foreach (GameObject root in roots)
            {
                foreach (Camera c in root.GetComponentsInChildren<Camera>(true))
                {
                    string urp = "";
                    var data = c.GetComponent("UniversalAdditionalCameraData");
                    if (data != null)
                    {
                        var so = new SerializedObject(data);
                        var type = so.FindProperty("m_CameraType");
                        var stack = so.FindProperty("m_Cameras");
                        var post = so.FindProperty("m_RenderPostProcessing");
                        urp = " urpType=" + (type != null ? type.intValue.ToString() : "?") + " stack=" + (stack != null ? stack.arraySize.ToString() : "?")
                            + " post=" + (post != null ? post.boolValue.ToString() : "?");
                    }
                    Log(sceneName + ": camera " + Path(c.transform) + " active=" + c.gameObject.activeInHierarchy + " enabled=" + c.enabled
                        + " depth=" + c.depth + " clear=" + c.clearFlags + " bg=" + c.backgroundColor + " mask=0x" + c.cullingMask.ToString("X")
                        + " near=" + c.nearClipPlane + " far=" + c.farClipPlane + " occl=" + c.useOcclusionCulling
                        + " target=" + (c.targetTexture != null ? c.targetTexture.name : "screen") + urp);
                }
                foreach (Component v in root.GetComponentsInChildren(typeof(Behaviour), true))
                {
                    if (v == null || v.GetType().Name != "Volume") continue;
                    var so = new SerializedObject(v);
                    var profile = so.FindProperty("sharedProfile")?.objectReferenceValue as ScriptableObject;
                    var global = so.FindProperty("m_IsGlobal");
                    var weight = so.FindProperty("weight");
                    Log(sceneName + ": volume " + Path(v.transform) + " active=" + v.gameObject.activeInHierarchy + " global=" + (global != null && global.boolValue)
                        + " weight=" + (weight != null ? weight.floatValue : -1f) + " profile=" + (profile != null ? profile.name : "none"));
                    if (profile == null) continue;
                    var comps = new SerializedObject(profile).FindProperty("components");
                    if (comps == null) continue;
                    for (int i = 0; i < comps.arraySize; i++)
                    {
                        var comp = comps.GetArrayElementAtIndex(i).objectReferenceValue as ScriptableObject;
                        if (comp == null) { Log("    (missing volume component)"); continue; }
                        var cso = new SerializedObject(comp);
                        var it = cso.GetIterator();
                        var parts = new List<string>();
                        bool enter = true;
                        while (it.NextVisible(enter))
                        {
                            enter = false;
                            if (it.name == "m_Script") continue;
                            var ov = it.FindPropertyRelative("m_OverrideState");
                            var val = it.FindPropertyRelative("m_Value");
                            if (ov == null || val == null || !ov.boolValue) continue;
                            string vs = val.propertyType == SerializedPropertyType.Float ? val.floatValue.ToString("0.###")
                                : val.propertyType == SerializedPropertyType.Color ? val.colorValue.ToString()
                                : val.propertyType == SerializedPropertyType.Vector4 ? val.vector4Value.ToString()
                                : val.propertyType == SerializedPropertyType.Boolean ? val.boolValue.ToString()
                                : val.propertyType == SerializedPropertyType.Integer || val.propertyType == SerializedPropertyType.Enum ? val.intValue.ToString()
                                : val.propertyType.ToString();
                            parts.Add(it.name + "=" + vs);
                        }
                        Log("    " + comp.GetType().Name + " active=" + new SerializedObject(comp).FindProperty("active")?.boolValue + " " + string.Join(" ", parts));
                    }
                }
                foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                {
                    if (t.name != "Player") continue;
                    var r = t.GetComponent<Renderer>();
                    if (r == null) continue;
                    var m = r.sharedMaterial;
                    Log(sceneName + ": Player renderer enabled=" + r.enabled + " material=" + (m != null ? m.name + " (" + m.shader.name + ", cull " + (m.HasProperty("_Cull") ? m.GetFloat("_Cull").ToString() : "?") + ")" : "none"));
                }
            }
            Log(sceneName + ": quality " + QualitySettings.names[QualitySettings.GetQualityLevel()] + ", pipeline "
                + (GraphicsSettings.defaultRenderPipeline != null ? GraphicsSettings.defaultRenderPipeline.name : "none") + " / "
                + (QualitySettings.renderPipeline != null ? QualitySettings.renderPipeline.name : "default"));
        }

        static void ReportNavMeshReach(string sceneName, GameObject[] roots)
        {
            var tri = UnityEngine.AI.NavMesh.CalculateTriangulation();
            if (tri.vertices == null || tri.vertices.Length == 0) return;
            Bounds b = new Bounds(tri.vertices[0], Vector3.zero);
            foreach (Vector3 v in tri.vertices) b.Encapsulate(v);
            Log(sceneName + ": navmesh bounds " + b.min + " .. " + b.max);
            foreach (GameObject root in roots)
                foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                {
                    string n = t.name;
                    bool interesting = n == "GrannyAI" || n == "GrannySpawnPoint" || n == "WakeUpPoint" || n.EndsWith(" Point") || n == "GrannyCrashRespawnPoint";
                    if (!interesting) continue;
                    var agent = t.GetComponent<UnityEngine.AI.NavMeshAgent>();
                    string a = agent != null ? " agentType=" + agent.agentTypeID + " r=" + agent.radius + " h=" + agent.height + " baseOffset=" + agent.baseOffset : "";
                    bool ok = UnityEngine.AI.NavMesh.SamplePosition(t.position, out UnityEngine.AI.NavMeshHit hit, 10f, UnityEngine.AI.NavMesh.AllAreas);
                    Log(sceneName + ": " + n + " at " + t.position + (ok ? " -> navmesh " + hit.distance.ToString("0.00") + " m away at " + hit.position : " -> NO navmesh within 10 m") + a);
                }
        }

        /// <summary>
        /// The exported game has no NavMesh data (AssetRipper does not bring it back), so Granny's walkable area is
        /// baked again here from each NavMeshSurface's own settings and saved next to the scene.
        /// </summary>
        static int BakeNavMeshes(Scene scene, GameObject[] roots)
        {
            System.Type surfaceType = System.AppDomain.CurrentDomain.GetAssemblies()
                .Select(a => a.GetType("Unity.AI.Navigation.NavMeshSurface", false))
                .FirstOrDefault(t => t != null);
            if (surfaceType == null) { Log("NavMeshSurface type not found - navmesh not baked"); return 0; }
            var build = surfaceType.GetMethod("BuildNavMesh", System.Type.EmptyTypes);
            var dataProp = surfaceType.GetProperty("navMeshData");
            int n = 0;
            foreach (GameObject root in roots)
                foreach (Component surface in root.GetComponentsInChildren(surfaceType, true))
                {
                    if (!((Behaviour)surface).isActiveAndEnabled) continue;
                    var timer = System.Diagnostics.Stopwatch.StartNew();
                    try { build.Invoke(surface, null); }
                    catch (System.Exception e) { Log("navmesh bake failed on " + surface.name + ": " + e.InnerException?.Message); continue; }
                    var data = dataProp.GetValue(surface) as Object;
                    if (data == null) { Log("navmesh bake gave no data on " + surface.name); continue; }
                    const string dir = "Assets/Dimnight/NavMesh";
                    if (!AssetDatabase.IsValidFolder(dir)) AssetDatabase.CreateFolder("Assets/Dimnight", "NavMesh");
                    string path = dir + "/" + scene.name + "-" + surface.name + "-" + n + ".asset";
                    AssetDatabase.DeleteAsset(path);
                    AssetDatabase.CreateAsset(data, path);
                    EditorUtility.SetDirty(surface);
                    var tri = UnityEngine.AI.NavMesh.CalculateTriangulation();
                    var sso = new SerializedObject(surface);
                    string settings = "";
                    foreach (string f in new[] { "m_AgentTypeID", "m_CollectObjects", "m_UseGeometry", "m_DefaultArea", "m_OverrideVoxelSize", "m_MinRegionArea" })
                    {
                        var prop = sso.FindProperty(f);
                        if (prop != null) settings += " " + f.Substring(2) + "=" + (prop.propertyType == SerializedPropertyType.Float ? prop.floatValue.ToString() : prop.propertyType == SerializedPropertyType.Boolean ? prop.boolValue.ToString() : prop.intValue.ToString());
                    }
                    var mask = sso.FindProperty("m_LayerMask");
                    if (mask != null) settings += " LayerMask=0x" + mask.intValue.ToString("X");
                    Log(scene.name + ": navmesh baked on " + surface.name + " in " + timer.ElapsedMilliseconds + " ms, "
                        + (tri.indices.Length / 3) + " triangles," + settings + ", surface at " + surface.transform.position);
                    n++;
                }
            return n;
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
