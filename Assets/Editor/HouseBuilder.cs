using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace TradersMadness.EditorTools
{
    /// <summary>
    /// Builds Resources/House.prefab from the converted house (tools/unity/convert_assets.py):
    /// Assets/Game/House/house.bytes (one mesh per object of house.glb, every glTF primitive a sub-mesh),
    /// materials.json, the photos, the Hyper3D textures and the lightmaps baked in Blender (Shaders/House.shader).
    /// The monitor screens, the LED strip and the keypad light get the glowing Screen material; room objects with a
    /// second "power on" lightmap get an AltLightmap.
    /// </summary>
    public static class HouseBuilder
    {
        public const string Folder = "Assets/Game/House";
        const string Out = "Assets/Generated/House";
        public const string PrefabPath = "Assets/Resources/House.prefab";

        public static bool Available { get { return File.Exists(Folder + "/house.bytes") && File.Exists(Folder + "/materials.json"); } }

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
                foreach (string f in Files(Folder + "/Photos", ".jpg", ".png")) AssetRules.Ensure(f);
                foreach (string f in Files(Folder + "/Textures", ".jpg", ".png")) AssetRules.Ensure(f);
                foreach (string f in Files(Folder + "/Lightmaps", ".png")) AssetRules.Ensure(f);
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
            AssetDatabase.CreateFolder("Assets/Generated", "House");
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
            if (!Available) throw new Exception("converted house missing in " + Folder);
            Folders();
            ImportTextures();
            object mj = Json.Parse(File.ReadAllText(Folder + "/materials.json"));
            object meta = Level.LoadMeta();
            if (meta == null) throw new Exception("Resources/house_meta.json missing");
            List<object> mats = Json.A(mj, "materials");
            float gain = Json.F(mj, "lm_gain", 2.48f);
            var lightmapped = new HashSet<string>();
            foreach (object o in Json.A(mj, "lightmapped")) lightmapped.Add((string)o);
            var baseColors = Json.O(meta, "base_colors");
            var emit = Json.O(meta, "emit");
            Dictionary<string, float> roomLight = Level.RoomLights(meta, false);
            var lmMeta = Json.O(meta, "lightmaps");

            Shader school = Shader.Find("TradersMadness/House");
            Shader glassShader = Shader.Find("TradersMadness/Glass");
            Shader screenShader = Shader.Find("TradersMadness/Screen");
            if (school == null || glassShader == null || screenShader == null) throw new Exception("TradersMadness shaders missing");
            var screenMat = new Material(screenShader) { name = "screen" };
            screenMat.SetColor("_Color", new Color(1f, 1f, 1f, 1f));
            screenMat.SetFloat("_On", 0f);
            AssetDatabase.CreateAsset(screenMat, Out + "/Materials/screen.mat");
            var ledMat = new Material(screenShader) { name = "led" };
            ledMat.SetColor("_Color", new Color(0.55f, 0.32f, 1f, 1f));
            ledMat.SetFloat("_On", 0f);
            ledMat.SetFloat("_Lines", 0f);
            AssetDatabase.CreateAsset(ledMat, Out + "/Materials/led.mat");
            var keyMat = new Material(screenShader) { name = "keypad_led" };
            keyMat.SetColor("_Color", new Color(1f, 0.1f, 0.05f, 1f));
            keyMat.SetFloat("_On", 1f);
            keyMat.SetFloat("_Lines", 0f);
            AssetDatabase.CreateAsset(keyMat, Out + "/Materials/keypad_led.mat");
            Texture2D white = Texture2D.whiteTexture;
            var glassMats = new Dictionary<string, Material>();
            var cache = new Dictionary<string, Material>();
            int created = 0;

            Func<int, string, float, Material> make = (mi, lmNode, flat) =>
            {
                object md = mats[mi];
                string name = Json.S(md, "name");
                if (name == "glass")
                {
                    Material g;
                    if (!glassMats.TryGetValue(name, out g))
                    {
                        g = new Material(glassShader) { name = name };
                        g.SetVector("_Color", new Vector4(0.16f, 0.2f, 0.22f, 0.16f));
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
                // the paint colour from house_meta.json, grey when the material has none
                object bc = baseColors != null ? Json.Get(baseColors, name) : null;
                Vector4 basec = bc != null ? new Vector4(Json.At(bc, 0), Json.At(bc, 1), Json.At(bc, 2), 0f) : new Vector4(0.5f, 0.5f, 0.5f, 0f);
                if (!string.IsNullOrEmpty(own))
                {
                    m.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "/Textures/" + own) ?? white);
                    m.SetFloat("_Tint", 0f);
                    m.SetVector("_Base", new Vector4(0.5f, 0.5f, 0.5f, 0f));
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

            var root = new GameObject("House");
            int count = 0, verts = 0;
            using (var r = new BinaryReader(File.OpenRead(Folder + "/house.bytes")))
            {
                if (r.ReadInt32() != 0x53554F48 || r.ReadInt32() != 1) throw new Exception("unexpected house.bytes format");
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
                    float flat = lit ? 0.16f : Level.LightAt(meta, roomLight, t + new Vector3(0f, 0.8f, 0f));
                    bool glow = name.StartsWith("screen_") || name == "led_strip" || name == "keypad_led";
                    for (int s = 0; s < ns; s++)
                    {
                        int mi = r.ReadInt32();
                        int ni = r.ReadInt32();
                        var idx = new int[ni];
                        for (int k = 0; k < ni; k++) idx[k] = r.ReadInt32();
                        mesh.SetTriangles(idx, s, false);
                        smats[s] = glow ? (name == "led_strip" ? ledMat : name == "keypad_led" ? keyMat : screenMat) : make(mi, lit ? name : null, flat);
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
                    // a second lightmap for the power-on state of the trading room
                    object lme = lmMeta != null ? Json.Get(lmMeta, name) : null;
                    string onFile = lme != null ? Json.S(lme, "on") : "";
                    if (lit && !string.IsNullOrEmpty(onFile))
                    {
                        var onTex = AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "/Lightmaps/" + name + "_on.png");
                        if (onTex != null)
                        {
                            var alt = go.AddComponent<AltLightmap>();
                            alt.onLightmap = onTex;
                        }
                    }
                    count++;
                    verts += nv;
                }
            }
            AssetDatabase.DeleteAsset(PrefabPath);
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            Debug.Log("[TM] house built: " + count + " objects, " + verts + " vertices, " + created + " materials");
        }
    }
}
