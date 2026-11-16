using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Moulika.EditorTools
{
    /// <summary>
    /// Builds Resources/School.prefab from the converted school (tools/unity/convert_assets.py):
    /// Assets/Game/School/school.bytes (one mesh per object of school.glb, every glTF primitive a sub-mesh),
    /// materials.json, the photos, the Hyper3D textures and the lightmaps baked in Blender.
    /// Materials follow game/scripts/mats.gd exactly (see Shaders/School.shader).
    /// </summary>
    public static class SchoolBuilder
    {
        public const string Folder = "Assets/Game/School";
        const string Out = "Assets/Generated/School";
        public const string PrefabPath = "Assets/Resources/School.prefab";

        public static bool Available { get { return File.Exists(Folder + "/school.bytes") && File.Exists(Folder + "/materials.json"); } }

        static void Tex(string path, bool srgb, bool mips, TextureWrapMode wrap, bool compress, int maxSize = 2048)
        {
            var imp = AssetImporter.GetAtPath(path) as TextureImporter;
            if (imp == null) return;
            imp.textureType = TextureImporterType.Default;
            imp.sRGBTexture = srgb;
            imp.mipmapEnabled = mips;
            imp.wrapMode = wrap;
            imp.filterMode = mips ? FilterMode.Trilinear : FilterMode.Bilinear;
            imp.anisoLevel = mips ? 4 : 1;
            imp.maxTextureSize = maxSize;
            imp.alphaIsTransparency = false;
            imp.textureCompression = compress ? TextureImporterCompression.CompressedHQ : TextureImporterCompression.Uncompressed;
            imp.SaveAndReimport();
        }

        static IEnumerable<string> Files(string dir, params string[] exts)
        {
            if (!Directory.Exists(dir)) yield break;
            foreach (string f in Directory.GetFiles(dir))
            {
                string e = Path.GetExtension(f).ToLowerInvariant();
                if (Array.IndexOf(exts, e) >= 0) yield return f.Replace('\\', '/');
            }
        }

        public static void ImportTextures()
        {
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (string f in Files(Folder + "/Photos", ".jpg", ".png"))
                    Tex(f, true, true, TextureWrapMode.Repeat, true, 1024);
                foreach (string f in Files(Folder + "/Textures", ".jpg", ".png"))
                    Tex(f, true, true, TextureWrapMode.Repeat, true, 1024);
                foreach (string f in Files(Folder + "/Lightmaps", ".png"))
                    Tex(f, true, false, TextureWrapMode.Clamp, false, 1024);
            }
            finally
            {
                AssetDatabase.StopAssetEditing();
            }
        }

        static string Str(BinaryReader r)
        {
            int n = r.ReadInt32();
            return System.Text.Encoding.UTF8.GetString(r.ReadBytes(n));
        }

        static Vector3[] V3(BinaryReader r, int n)
        {
            var a = new Vector3[n];
            for (int i = 0; i < n; i++) a[i] = new Vector3(r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
            return a;
        }

        static Vector2[] V2(BinaryReader r, int n)
        {
            var a = new Vector2[n];
            for (int i = 0; i < n; i++) a[i] = new Vector2(r.ReadSingle(), r.ReadSingle());
            return a;
        }

        static void Folders()
        {
            if (!AssetDatabase.IsValidFolder("Assets/Generated")) AssetDatabase.CreateFolder("Assets", "Generated");
            if (AssetDatabase.IsValidFolder(Out)) AssetDatabase.DeleteAsset(Out);
            AssetDatabase.CreateFolder("Assets/Generated", "School");
            AssetDatabase.CreateFolder(Out, "Meshes");
            AssetDatabase.CreateFolder(Out, "Materials");
            if (!AssetDatabase.IsValidFolder("Assets/Resources")) AssetDatabase.CreateFolder("Assets", "Resources");
        }

        static string Safe(string s)
        {
            foreach (char c in Path.GetInvalidFileNameChars()) s = s.Replace(c, '_');
            return s;
        }

        public static void Build()
        {
            if (!Available) throw new Exception("converted school missing in " + Folder);
            Folders();
            ImportTextures();
            object mj = Json.Parse(File.ReadAllText(Folder + "/materials.json"));
            object meta = Level.LoadMeta();
            if (meta == null) throw new Exception("Resources/school_meta.json missing");
            List<object> mats = Json.A(mj, "materials");
            float gain = Json.F(mj, "lm_gain", 2.48f);
            var lightmapped = new HashSet<string>();
            foreach (object o in Json.A(mj, "lightmapped")) lightmapped.Add((string)o);
            var baseColors = Json.O(meta, "base_colors");
            var emit = Json.O(meta, "emit");
            Dictionary<string, float> roomLight = Level.RoomLights(meta);

            Shader school = Shader.Find("Moulika/School");
            Shader glassShader = Shader.Find("Moulika/Glass");
            if (school == null || glassShader == null) throw new Exception("Moulika shaders missing");
            Texture2D white = Texture2D.whiteTexture;
            var leaves = AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "/Photos/leaves.png");
            var glassMats = new Dictionary<string, Material>();
            var cache = new Dictionary<string, Material>();
            int created = 0;

            Func<int, string, float, Material> make = (mi, lmNode, flat) =>
            {
                object md = mats[mi];
                string name = Json.S(md, "name");
                if (name == "glass" || name == "glass_dirty")
                {
                    Material g;
                    if (!glassMats.TryGetValue(name, out g))
                    {
                        g = new Material(glassShader) { name = name };
                        g.SetVector("_Color", new Vector4(0.25f, 0.32f, 0.34f, name == "glass" ? 0.22f : 0.4f));
                        g.renderQueue = 3000;
                        AssetDatabase.CreateAsset(g, Out + "/Materials/" + name + ".mat");
                        glassMats[name] = g;
                    }
                    return g;
                }
                string key = mi + "|" + (lmNode ?? "flat" + Mathf.RoundToInt(flat * 1000f));
                Material m;
                if (cache.TryGetValue(key, out m)) return m;
                m = new Material(school) { name = name + (lmNode != null ? "@" + lmNode : "@flat" + Mathf.RoundToInt(flat * 1000f)) };
                string own = Json.S(md, "texture");
                string photo = Json.S(md, "photo");
                // Mats.color_of: the paint colour from school_meta.json, grey when the material has none
                object bc = baseColors != null ? Json.Get(baseColors, name) : null;
                Vector4 basec = bc != null ? new Vector4(Json.At(bc, 0), Json.At(bc, 1), Json.At(bc, 2), 0f) : new Vector4(0.5f, 0.5f, 0.5f, 0f);
                if (!string.IsNullOrEmpty(own))
                {
                    m.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "/Textures/" + own) ?? white);
                    m.SetFloat("_Tint", 0f);
                    m.SetVector("_Base", new Vector4(0.5f, 0.5f, 0.5f, 0f));
                }
                else if (name == "leaves")
                {
                    m.SetTexture("_MainTex", leaves != null ? (Texture)leaves : white);
                    m.SetFloat("_Tint", 0f);
                    m.SetFloat("_Cutout", 1f);
                    m.SetVector("_Base", new Vector4(0.3f, 0.45f, 0.2f, 0f));
                }
                else
                {
                    Texture2D pt = string.IsNullOrEmpty(photo) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "/Photos/" + photo);
                    m.SetTexture("_MainTex", pt != null ? (Texture)pt : white);
                    m.SetFloat("_Tint", Json.F(md, "tint", 1f));
                    m.SetVector("_Base", basec);
                    m.SetFloat("_Avg", pt != null ? Json.F(md, "avg", 0.5f) : 1f);
                }
                if (lmNode != null)
                {
                    var lm = AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "/Lightmaps/" + lmNode + ".png");
                    m.SetTexture("_LM", lm != null ? (Texture)lm : white);
                    m.SetFloat("_UseLM", lm != null ? 1f : 0f);
                }
                else
                {
                    m.SetTexture("_LM", white);
                    m.SetFloat("_UseLM", 0f);
                }
                m.SetVector("_FlatLight", new Vector4(flat, flat, flat * 1.05f, 0f));
                m.SetFloat("_LMGain", gain);
                m.SetFloat("_Glow", (emit != null ? Json.F(emit, name, 0f) : 0f) * 0.25f);
                m.SetFloat("_Cull", Json.Get(md, "two_sided") is bool && (bool)Json.Get(md, "two_sided") ? 0f : 2f);
                AssetDatabase.CreateAsset(m, Out + "/Materials/" + created.ToString("000") + "_" + Safe(m.name) + ".mat");
                created++;
                cache[key] = m;
                return m;
            };

            var root = new GameObject("School");
            int count = 0, verts = 0;
            using (var r = new BinaryReader(File.OpenRead(Folder + "/school.bytes")))
            {
                if (r.ReadInt32() != 0x4843534D || r.ReadInt32() != 1) throw new Exception("unexpected school.bytes format");
                int nodes = r.ReadInt32();
                for (int i = 0; i < nodes; i++)
                {
                    string name = Str(r);
                    var t = new Vector3(r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
                    int nv = r.ReadInt32();
                    Vector3[] pos = V3(r, nv), nrm = V3(r, nv);
                    Vector2[] uv0 = V2(r, nv), uv1 = V2(r, nv);
                    int ns = r.ReadInt32();
                    var mesh = new Mesh { name = name };
                    mesh.indexFormat = nv > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16;
                    mesh.vertices = pos;
                    mesh.normals = nrm;
                    mesh.uv = uv0;
                    mesh.uv2 = uv1;
                    mesh.subMeshCount = ns;
                    var smats = new Material[ns];
                    bool lit = lightmapped.Contains(name);
                    float flat = lit ? 0.16f : Level.LightAt(meta, roomLight, t);
                    if (name == "arch_roof") flat = 0.03f;
                    for (int s = 0; s < ns; s++)
                    {
                        int mi = r.ReadInt32();
                        int ni = r.ReadInt32();
                        var idx = new int[ni];
                        for (int k = 0; k < ni; k++) idx[k] = r.ReadInt32();
                        mesh.SetTriangles(idx, s, false);
                        smats[s] = make(mi, lit ? name : null, flat);
                    }
                    mesh.RecalculateBounds();
                    AssetDatabase.CreateAsset(mesh, Out + "/Meshes/" + i.ToString("00") + "_" + Safe(name) + ".asset");
                    var go = new GameObject(name);
                    go.transform.SetParent(root.transform, false);
                    go.transform.localPosition = t;
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var mr = go.AddComponent<MeshRenderer>();
                    mr.sharedMaterials = smats;
                    mr.shadowCastingMode = ShadowCastingMode.Off;
                    mr.receiveShadows = false;
                    mr.lightProbeUsage = LightProbeUsage.Off;
                    mr.reflectionProbeUsage = ReflectionProbeUsage.Off;
                    mr.allowOcclusionWhenDynamic = false;
                    count++;
                    verts += nv;
                }
            }
            AssetDatabase.DeleteAsset(PrefabPath);
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            Debug.Log("[MOULIKA] school built: " + count + " objects, " + verts + " vertices, " + created + " materials");
        }
    }
}
