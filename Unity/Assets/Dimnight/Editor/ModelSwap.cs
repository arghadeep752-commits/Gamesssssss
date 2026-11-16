using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Dimnight.EditorTools
{
    /// <summary>
    /// Puts the new Granny Dimnight models into the original scenes: every object listed in
    /// Assets/Dimnight/Models/&lt;scene&gt;.dmodel (written by tools/models/build.py) gets its new mesh, materials and
    /// collider mesh in place - same transform, same scripts, same colliders - so the house plays exactly the same.
    /// </summary>
    public static class ModelSwap
    {
        const string Root = "Assets/Dimnight/Models";
        const string TexRoot = "Assets/Dimnight/Textures";
        static Dictionary<string, Material> materials;

        static void Log(string m) { Debug.Log("[DIMNIGHT] " + m); }

        public static int Apply(Scene scene)
        {
            string file = Root + "/" + scene.name + ".dmodel";
            if (!File.Exists(file)) { Log(scene.name + ": no new models (" + file + ")"); return 0; }
            LoadMaterials();

            var byId = new Dictionary<ulong, GameObject>();
            foreach (GameObject root in scene.GetRootGameObjects())
                foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                {
                    var gid = GlobalObjectId.GetGlobalObjectIdSlow(t.gameObject);
                    byId[gid.targetObjectId] = t.gameObject;
                }

            string meshDir = Root + "/Meshes/" + scene.name;
            if (!AssetDatabase.IsValidFolder(Root + "/Meshes")) AssetDatabase.CreateFolder(Root, "Meshes");
            if (!AssetDatabase.IsValidFolder(meshDir)) AssetDatabase.CreateFolder(Root + "/Meshes", scene.name);

            int swapped = 0, missing = 0, colliders = 0;
            AssetDatabase.StartAssetEditing();
            var created = new List<(GameObject go, Mesh mesh, Material[] mats)>();
            try
            {
                using (var br = new BinaryReader(File.OpenRead(file)))
                {
                    if (Encoding.ASCII.GetString(br.ReadBytes(4)) != "DMDL") { Log("bad model file " + file); return 0; }
                    int version = br.ReadInt32();
                    int count = br.ReadInt32();
                    for (int i = 0; i < count; i++)
                    {
                        long fid = br.ReadInt64();
                        int subCount = br.ReadInt32();
                        var matKeys = new string[subCount];
                        for (int s = 0; s < subCount; s++)
                        {
                            int len = br.ReadInt16();
                            matKeys[s] = Encoding.UTF8.GetString(br.ReadBytes(len));
                        }
                        int vc = br.ReadInt32();
                        var pos = new Vector3[vc];
                        var nor = new Vector3[vc];
                        var uv = new Vector2[vc];
                        for (int v = 0; v < vc; v++) pos[v] = new Vector3(br.ReadSingle(), br.ReadSingle(), br.ReadSingle());
                        for (int v = 0; v < vc; v++) nor[v] = new Vector3(br.ReadSingle(), br.ReadSingle(), br.ReadSingle());
                        for (int v = 0; v < vc; v++) uv[v] = new Vector2(br.ReadSingle(), br.ReadSingle());
                        var tris = new int[subCount][];
                        for (int s = 0; s < subCount; s++)
                        {
                            int n = br.ReadInt32();
                            tris[s] = new int[n];
                            for (int k = 0; k < n; k++) tris[s][k] = br.ReadInt32();
                        }

                        if (!byId.TryGetValue(unchecked((ulong)fid), out GameObject go)) { missing++; continue; }
                        var mesh = new Mesh { name = go.name + "_dimnight" };
                        if (vc > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                        mesh.vertices = pos;
                        mesh.normals = nor;
                        mesh.uv = uv;
                        mesh.subMeshCount = subCount;
                        for (int s = 0; s < subCount; s++) mesh.SetTriangles(tris[s], s, false);
                        mesh.RecalculateBounds();
                        mesh.RecalculateTangents();
                        var mats = new Material[subCount];
                        for (int s = 0; s < subCount; s++) mats[s] = GetMaterial(matKeys[s]);
                        AssetDatabase.CreateAsset(mesh, meshDir + "/" + Safe(go.name) + "_" + fid + ".asset");
                        created.Add((go, mesh, mats));
                    }
                }
            }
            finally
            {
                AssetDatabase.StopAssetEditing();
            }

            foreach (var (go, mesh, mats) in created)
            {
                var mf = go.GetComponent<MeshFilter>();
                var mr = go.GetComponent<MeshRenderer>();
                if (mf == null || mr == null) continue;
                Mesh old = mf.sharedMesh;
                mf.sharedMesh = mesh;
                mr.sharedMaterials = mats;
                var so = new SerializedObject(mr);
                var first = so.FindProperty("m_StaticBatchInfo.firstSubMesh");
                var subs = so.FindProperty("m_StaticBatchInfo.subMeshCount");
                if (first != null) first.intValue = 0;
                if (subs != null) subs.intValue = 0;
                var lm = so.FindProperty("m_LightmapIndex");
                if (lm != null) lm.intValue = 65535;
                so.ApplyModifiedPropertiesWithoutUndo();
                foreach (var mc in go.GetComponents<MeshCollider>())
                {
                    if (mc.sharedMesh == null || mc.sharedMesh == old || mc.sharedMesh.name.StartsWith("Combined"))
                    {
                        mc.sharedMesh = mesh;
                        colliders++;
                    }
                }
                EditorUtility.SetDirty(go);
                swapped++;
            }
            AssetDatabase.SaveAssets();
            Log(scene.name + ": new models swapped in for " + swapped + " objects (" + colliders + " collider meshes), " + missing + " not found");
            return swapped;
        }

        static string Safe(string s)
        {
            var sb = new StringBuilder();
            foreach (char c in s) sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.Length > 40 ? sb.ToString(0, 40) : sb.ToString();
        }

        [System.Serializable] class MatSpec { public string slot; public float[] color; public float tile = 1; public float smoothness; public float metallic; public float transparent = -1; public float emission; public bool stretch; }

        static Dictionary<string, MatSpec> specs;

        static void LoadMaterials()
        {
            if (materials != null) return;
            materials = new Dictionary<string, Material>();
            specs = new Dictionary<string, MatSpec>();
            string path = Root + "/materials.json";
            if (!File.Exists(path)) return;
            // materials.json is {"key": {...}, ...}: parse with a tiny reader (JsonUtility can't read dictionaries)
            string json = File.ReadAllText(path);
            foreach (var kv in SplitTopLevel(json))
            {
                var spec = JsonUtility.FromJson<MatSpec>(kv.Value);
                if (spec != null) specs[kv.Key] = spec;
            }
            if (!AssetDatabase.IsValidFolder(Root + "/Materials")) AssetDatabase.CreateFolder(Root, "Materials");
        }

        static IEnumerable<KeyValuePair<string, string>> SplitTopLevel(string json)
        {
            int i = json.IndexOf('{') + 1;
            while (i > 0 && i < json.Length)
            {
                int q0 = json.IndexOf('"', i);
                if (q0 < 0) yield break;
                int q1 = json.IndexOf('"', q0 + 1);
                string key = json.Substring(q0 + 1, q1 - q0 - 1);
                int b0 = json.IndexOf('{', q1);
                int depth = 0, b1 = b0;
                for (; b1 < json.Length; b1++)
                {
                    if (json[b1] == '{') depth++;
                    else if (json[b1] == '}') { depth--; if (depth == 0) break; }
                }
                yield return new KeyValuePair<string, string>(key, json.Substring(b0, b1 - b0 + 1));
                i = b1 + 1;
            }
        }

        static Material GetMaterial(string key)
        {
            if (materials.TryGetValue(key, out Material m)) return m;
            specs.TryGetValue(key, out MatSpec spec);
            Shader lit = Shader.Find("Universal Render Pipeline/Lit");
            m = new Material(lit) { name = "Dimnight_" + key };
            Color c = Color.white;
            if (spec != null && spec.color != null && spec.color.Length >= 3) c = new Color(spec.color[0] / 255f, spec.color[1] / 255f, spec.color[2] / 255f, 1);
            if (spec != null && !string.IsNullOrEmpty(spec.slot))
            {
                string slot = spec.slot.StartsWith("@") ? spec.slot.Substring(1) : spec.slot;
                string diff = spec.slot.StartsWith("@") ? TexRoot + "/" + slot + ".png" : TexRoot + "/" + slot + "/diff.jpg";
                string nor = TexRoot + "/" + slot + "/nor.jpg";
                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(diff);
                if (tex != null)
                {
                    m.SetTexture("_BaseMap", tex);
                    m.SetTexture("_MainTex", tex);
                }
                var nt = AssetDatabase.LoadAssetAtPath<Texture2D>(nor);
                if (nt != null)
                {
                    var imp = AssetImporter.GetAtPath(nor) as TextureImporter;
                    if (imp != null && imp.textureType != TextureImporterType.NormalMap)
                    {
                        imp.textureType = TextureImporterType.NormalMap;
                        imp.SaveAndReimport();
                        nt = AssetDatabase.LoadAssetAtPath<Texture2D>(nor);
                    }
                    m.SetTexture("_BumpMap", nt);
                    m.SetFloat("_BumpScale", 0.8f);
                    m.EnableKeyword("_NORMALMAP");
                }
            }
            m.SetColor("_BaseColor", c);
            m.SetColor("_Color", c);
            if (spec != null)
            {
                m.SetFloat("_Smoothness", spec.smoothness);
                m.SetFloat("_Metallic", spec.metallic);
                if (spec.emission > 0)
                {
                    m.EnableKeyword("_EMISSION");
                    m.SetColor("_EmissionColor", c * spec.emission);
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
                }
                if (spec.transparent >= 0)
                {
                    m.SetFloat("_Surface", 1);
                    m.SetFloat("_Blend", 0);
                    m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
                    m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                    m.SetFloat("_ZWrite", 0);
                    m.SetOverrideTag("RenderType", "Transparent");
                    m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
                    c.a = spec.transparent;
                    m.SetColor("_BaseColor", c);
                }
            }
            AssetDatabase.CreateAsset(m, Root + "/Materials/" + Safe(key) + ".mat");
            materials[key] = m;
            return m;
        }
    }
}
