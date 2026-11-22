using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;

namespace Danga
{
    /// <summary>Little-endian reader for the converted model files.</summary>
    public class Bin
    {
        readonly byte[] b;
        public int p;
        public Bin(byte[] data) { b = data; }
        public int I32() { int v = System.BitConverter.ToInt32(b, p); p += 4; return v; }
        public float F32() { float v = System.BitConverter.ToSingle(b, p); p += 4; return v; }
        public Vector3 V3() { return new Vector3(F32(), F32(), F32()); }
        public string Str() { int n = I32(); string s = Encoding.UTF8.GetString(b, p, n); p += n; return s; }
        public float[] Floats(int n) { var a = new float[n]; System.Buffer.BlockCopy(b, p, a, 0, n * 4); p += n * 4; return a; }
        public int[] Ints(int n) { var a = new int[n]; System.Buffer.BlockCopy(b, p, a, 0, n * 4); p += n * 4; return a; }
        public bool End => p >= b.Length;
    }

    /// <summary>Time of day: sun, sky and fog colours for every Danga shader.</summary>
    public static class Env
    {
        public static float hour = 9.5f;
        public static float hoursPerSecond = 1f / 60f;          // one game hour per real minute
        public static float night, sunUp;
        public static Vector3 sunDir = new Vector3(0.3f, 0.8f, -0.5f);
        public static Color fogCol;
        public static float fogStart = 140f, fogEnd = 820f;
        public static Material skyMat;
        static Color dayHorizon = new Color(0.72f, 0.80f, 0.88f), nightHorizon = new Color(0.05f, 0.06f, 0.10f);

        public static void Init()
        {
            var sky = Resources.Load<TextAsset>("Gen/Sky/sky");
            if (sky != null)
            {
                object o = Json.Parse(sky.text);
                if (Json.Has(o, "day")) dayHorizon = Col(Json.A(Json.Get(o, "day"), "horizon"), dayHorizon);
                if (Json.Has(o, "night")) nightHorizon = Col(Json.A(Json.Get(o, "night"), "zenith"), nightHorizon) * 0.5f;
            }
            Shader s = Shader.Find("Danga/Sky");
            if (s != null)
            {
                skyMat = new Material(s);
                Texture2D d = Resources.Load<Texture2D>("Gen/Sky/day"), n = Resources.Load<Texture2D>("Gen/Sky/night");
                if (d != null) skyMat.SetTexture("_Day", d);
                if (n != null) skyMat.SetTexture("_Night", n);
                RenderSettings.skybox = skyMat;
            }
            Shader.SetGlobalTexture("_DG_LightMap", Resources.Load<Texture2D>("Gen/City/lightmap") ?? Texture2D.whiteTexture);
            Tick(0f);
        }

        static Color Col(List<object> a, Color fb)
        {
            if (a == null || a.Count < 3) return fb;
            return new Color(Json.F(a[0]), Json.F(a[1]), Json.F(a[2]));
        }

        public static string Clock()
        {
            int h = Mathf.FloorToInt(hour) % 24, m = Mathf.FloorToInt((hour - Mathf.Floor(hour)) * 60f);
            return string.Format("{0:00}:{1:00}", h, m);
        }

        public static void Tick(float dt)
        {
            hour = Mathf.Repeat(hour + dt * hoursPerSecond, 24f);
            float t = (hour - 5.8f) / 12.6f;                          // 0 at sunrise, 1 at sunset (Agartala, roughly)
            float elev = Mathf.Sin(Mathf.Clamp01(t) * Mathf.PI) * 64f;
            if (t < 0f || t > 1f) elev = -8f - 20f * Mathf.Sin(Mathf.Clamp01((t < 0 ? t + 0.9f : t - 1f) / 0.9f) * Mathf.PI);
            float az = Mathf.Lerp(100f, 250f, Mathf.Clamp01(t));
            sunUp = Mathf.Clamp01((elev + 2f) / 14f);
            night = 1f - Mathf.Clamp01((elev + 6f) / 12f);
            float golden = Mathf.Clamp01(1f - Mathf.Abs(elev - 6f) / 14f) * sunUp;
            float e = Mathf.Max(elev, 6f) * Mathf.Deg2Rad, a = az * Mathf.Deg2Rad;
            if (night > 0.5f) { e = 48f * Mathf.Deg2Rad; a = 210f * Mathf.Deg2Rad; }   // moonlight
            Vector3 sd = new Vector3(Mathf.Sin(a) * Mathf.Cos(e), Mathf.Sin(e), Mathf.Cos(a) * Mathf.Cos(e));
            sunDir = sd.normalized;
            Color sunC = Color.Lerp(new Color(1.05f, 0.98f, 0.88f), new Color(1.1f, 0.62f, 0.34f), golden);
            Color moon = new Color(0.30f, 0.38f, 0.58f);
            float strength = Mathf.Lerp(0.30f, 1f, sunUp);
            Color sun = Color.Lerp(sunC * 1.15f, moon, night);
            Color sky = Color.Lerp(Color.Lerp(new Color(0.50f, 0.58f, 0.70f), new Color(0.55f, 0.46f, 0.48f), golden), new Color(0.07f, 0.09f, 0.15f), night);
            Color ground = Color.Lerp(new Color(0.34f, 0.31f, 0.26f), new Color(0.03f, 0.03f, 0.045f), night);
            fogCol = Color.Lerp(Color.Lerp(dayHorizon, new Color(0.92f, 0.66f, 0.50f), golden * 0.8f), nightHorizon, night);
            Shader.SetGlobalVector("_DG_SunDir", new Vector4(sunDir.x, sunDir.y, sunDir.z, strength));
            Shader.SetGlobalColor("_DG_SunCol", sun);
            Shader.SetGlobalColor("_DG_SkyCol", sky);
            Shader.SetGlobalColor("_DG_GroundCol", ground);
            Shader.SetGlobalColor("_DG_FogCol", fogCol);
            float end = Mathf.Lerp(fogEnd, fogEnd * 0.55f, night);
            Shader.SetGlobalVector("_DG_Fog", new Vector4(fogStart, 1f / Mathf.Max(1f, end - fogStart), 0.92f, 0f));
            Shader.SetGlobalVector("_DG_Misc", new Vector4(night, Time.timeSinceLevelLoad, 0f, 1f));
            Shader.SetGlobalVector("_DG_LMRect", new Vector4(City.Half, 0f, 0f, 0f));
        }
    }

    // =================================================================================================== models
    public class VSpec
    {
        public string name, cls;
        public float length, width, height, mass, top, waterline;
        public bool police, open;
        public Vector3 seat, exit, box, rotor, tailRotor, motor;
        public float rotorR;
        public List<Vector3> lights = new List<Vector3>();
        public List<WheelSpec> wheels = new List<WheelSpec>();
        public bool IsBike => cls == "bike";
        public bool IsHeli => cls == "heli";
        public bool IsBoat => cls == "boat";
    }

    public struct WheelSpec { public Vector3 pos; public float r; public bool steer, drive; }

    public class WSpec { public string name; public float length; public Vector3 muzzle; }

    public class PSpec { public string name, kind; public Vector3 size; }

    /// <summary>Loads the converted Hyper3D Rodin models (meshes, textures, rigs) and keeps one copy of each.</summary>
    public static class Models
    {
        static readonly Dictionary<string, Mesh> meshes = new Dictionary<string, Mesh>();
        static readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();
        static readonly Dictionary<string, CharData> chars = new Dictionary<string, CharData>();
        public static readonly Dictionary<string, VSpec> vehicles = new Dictionary<string, VSpec>();
        public static readonly Dictionary<string, WSpec> weapons = new Dictionary<string, WSpec>();
        public static readonly Dictionary<string, PSpec> props = new Dictionary<string, PSpec>();
        public static readonly List<string> buildings = new List<string>();
        public static readonly List<string> charNames = new List<string>();
        static Shader model;
        static bool ready;

        public static void Init()
        {
            if (ready) return;
            ready = true;
            model = Shader.Find("Danga/Model");
            var ta = Resources.Load<TextAsset>("models");
            if (ta == null) { Debug.LogWarning("[DG] models.json missing"); return; }
            object o = Json.Parse(ta.text);
            var vs = Json.O(o, "vehicles");
            if (vs != null)
                foreach (var kv in vs)
                {
                    object v = kv.Value;
                    var s = new VSpec
                    {
                        name = kv.Key, cls = Json.S(v, "cls", "car"), length = Json.F(v, "length", 4f), width = Json.F(v, "width", 1.8f),
                        height = Json.F(v, "height", 1.5f), mass = Json.F(v, "mass", 1000f), top = Json.F(v, "top", 120f),
                        police = Json.Has(v, "police") && (bool)Json.Get(v, "police"), open = Json.Has(v, "open") && (bool)Json.Get(v, "open"),
                        seat = Json.V3(v, "seat"), exit = Json.V3(v, "exit"), box = Json.V3(v, "box"), waterline = Json.F(v, "waterline", 0.5f)
                    };
                    var lights = Json.A(v, "lights");
                    if (lights != null) foreach (object l in lights) s.lights.Add(Json.V3(l));
                    var wh = Json.A(v, "wheels");
                    if (wh != null)
                        foreach (object w in wh)
                            s.wheels.Add(new WheelSpec
                            {
                                pos = new Vector3(Json.F(w, "x"), Json.F(w, "y"), Json.F(w, "z")), r = Json.F(w, "r", 0.3f),
                                steer = (bool)Json.Get(w, "steer"), drive = (bool)Json.Get(w, "drive")
                            });
                    if (Json.Has(v, "rotor")) { var r = Json.A(v, "rotor"); s.rotor = Json.V3(r); s.rotorR = Json.At(r, 3, 5f); }
                    if (Json.Has(v, "tail_rotor")) s.tailRotor = Json.V3(v, "tail_rotor");
                    if (Json.Has(v, "motor")) s.motor = Json.V3(v, "motor");
                    vehicles[kv.Key] = s;
                }
            var ws = Json.O(o, "weapons");
            if (ws != null)
                foreach (var kv in ws)
                    weapons[kv.Key] = new WSpec { name = kv.Key, length = Json.F(kv.Value, "length", 0.3f), muzzle = Json.V3(kv.Value, "muzzle") };
            var ps = Json.O(o, "props");
            if (ps != null)
                foreach (var kv in ps)
                {
                    var spec = new PSpec { name = kv.Key, kind = Json.S(kv.Value, "kind", "prop"), size = Json.V3(kv.Value, "size") };
                    props[kv.Key] = spec;
                    if (spec.kind == "building") buildings.Add(kv.Key);
                }
            var cs = Json.O(o, "characters");
            if (cs != null) foreach (var kv in cs) charNames.Add(kv.Key);
            Debug.Log("[DG] models: " + vehicles.Count + " vehicles, " + weapons.Count + " weapons, " + charNames.Count + " characters, " + props.Count + " props");
        }

        /// <summary>A 'DGMS' mesh: positions, normals, uv, triangles.</summary>
        public static Mesh Mesh(string folder, string name)
        {
            string key = folder + "/" + name;
            Mesh m;
            if (meshes.TryGetValue(key, out m)) return m;
            var ta = Resources.Load<TextAsset>("Gen/" + key);
            if (ta == null) { Debug.LogWarning("[DG] mesh missing: " + key); meshes[key] = null; return null; }
            var b = new Bin(ta.bytes);
            b.I32(); b.I32();
            int nv = b.I32();
            float[] P = b.Floats(nv * 3), N = b.Floats(nv * 3), UV = b.Floats(nv * 2);
            int ni = b.I32();
            int[] I = b.Ints(ni);
            m = new Mesh { name = name };
            if (nv > 65000) m.indexFormat = IndexFormat.UInt32;
            var vp = new Vector3[nv];
            var vn = new Vector3[nv];
            var vu = new Vector2[nv];
            for (int i = 0; i < nv; i++)
            {
                vp[i] = new Vector3(P[i * 3], P[i * 3 + 1], P[i * 3 + 2]);
                vn[i] = new Vector3(N[i * 3], N[i * 3 + 1], N[i * 3 + 2]);
                vu[i] = new Vector2(UV[i * 2], UV[i * 2 + 1]);
            }
            m.vertices = vp;
            m.normals = vn;
            m.uv = vu;
            m.triangles = I;
            m.RecalculateBounds();
            m.RecalculateTangents();
            m.UploadMeshData(true);
            meshes[key] = m;
            Resources.UnloadAsset(ta);
            return m;
        }

        public static Material Mat(string folder, string name, Color tint)
        {
            string key = folder + "/" + name + "/" + ColorUtility.ToHtmlStringRGB(tint);
            Material m;
            if (mats.TryGetValue(key, out m)) return m;
            m = new Material(model) { name = name };
            var a = Resources.Load<Texture2D>("Gen/" + folder + "/" + name + "_albedo");
            var n = Resources.Load<Texture2D>("Gen/" + folder + "/" + name + "_normal");
            var r = Resources.Load<Texture2D>("Gen/" + folder + "/" + name + "_mr");
            if (a != null) m.SetTexture("_MainTex", a);
            if (n != null) m.SetTexture("_BumpMap", n);
            if (r != null) m.SetTexture("_MR", r);
            m.SetColor("_Color", tint);
            m.SetFloat("_Gloss", folder == "Vehicles" ? 1.6f : 1f);
            mats[key] = m;
            return m;
        }

        public static CharData Char(string name)
        {
            CharData c;
            if (chars.TryGetValue(name, out c)) return c;
            var ta = Resources.Load<TextAsset>("Gen/Chars/" + name);
            c = ta != null ? CharData.Load(name, ta.bytes) : null;
            if (ta != null) Resources.UnloadAsset(ta);
            chars[name] = c;
            if (c == null) Debug.LogWarning("[DG] character missing: " + name);
            return c;
        }

        static Mesh blobMesh;
        static Material blobMat;

        /// <summary>The soft dark patch under people and vehicles that sits them on the ground.</summary>
        public static GameObject Blob(Transform parent, float width, float length, float strength = 0.55f)
        {
            if (blobMesh == null)
            {
                blobMesh = new Mesh { name = "blob" };
                blobMesh.vertices = new[] { new Vector3(-0.5f, 0, -0.5f), new Vector3(0.5f, 0, -0.5f), new Vector3(0.5f, 0, 0.5f), new Vector3(-0.5f, 0, 0.5f) };
                blobMesh.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
                blobMesh.triangles = new[] { 0, 2, 1, 0, 3, 2 };
                blobMesh.RecalculateBounds();
                Shader sh = Shader.Find("Danga/Blob");
                blobMat = new Material(sh != null ? sh : Shader.Find("Sprites/Default"));
                var t = Resources.Load<Texture2D>("UI/blob");
                if (t != null) blobMat.SetTexture("_MainTex", t);
                blobMat.SetFloat("_Strength", strength);
            }
            var go = new GameObject("shadow");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(0f, 0.04f, 0f);
            go.transform.localScale = new Vector3(width, 1f, length);
            go.AddComponent<MeshFilter>().sharedMesh = blobMesh;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = blobMat;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            return go;
        }

        /// <summary>Puts a static model (vehicle body, weapon) on a new child object.</summary>
        public static GameObject Spawn(string folder, string name, Transform parent, Color tint)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            Mesh m = Mesh(folder, name);
            if (m == null) return go;
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = Mat(folder, name, tint);
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = false;
            mr.lightProbeUsage = LightProbeUsage.Off;
            mr.reflectionProbeUsage = ReflectionProbeUsage.Off;
            return go;
        }
    }

    // =================================================================================================== characters
    public class Clip
    {
        public string name;
        public float length, speed, fps;
        public bool loop;
        public int frames;
        public Vector3[] P;          // [bone * frames + frame]
        public Quaternion[] R;
    }

    /// <summary>A character from tools/rig/autorig.py: skinned mesh, 19 bones, hand-keyed clips, grip points.</summary>
    public class CharData
    {
        public string name;
        public Mesh mesh;
        public string[] bones;
        public int[] parent;
        public Vector3[] rest;
        public Matrix4x4[] bind;
        public readonly Dictionary<string, Clip> clips = new Dictionary<string, Clip>();
        public Vector3 hand, handTip, handL, headTop;
        public bool[] upper;

        public int Bone(string n) { return System.Array.IndexOf(bones, n); }

        public static CharData Load(string name, byte[] data)
        {
            var b = new Bin(data);
            var c = new CharData { name = name };
            b.I32(); b.I32();
            int nv = b.I32();
            float[] P = b.Floats(nv * 3), N = b.Floats(nv * 3), UV = b.Floats(nv * 2);
            int[] bi = b.Ints(nv * 4);
            float[] bw = b.Floats(nv * 4);
            int ni = b.I32();
            int[] I = b.Ints(ni);
            int nb = b.I32();
            c.bones = new string[nb];
            c.parent = new int[nb];
            c.rest = new Vector3[nb];
            c.bind = new Matrix4x4[nb];
            for (int k = 0; k < nb; k++)
            {
                c.bones[k] = b.Str();
                c.parent[k] = b.I32();
                c.rest[k] = b.V3();
                b.Floats(4); b.Floats(3);
                float[] m = b.Floats(16);
                var mm = new Matrix4x4();
                for (int r = 0; r < 4; r++) for (int col = 0; col < 4; col++) mm[r, col] = m[r * 4 + col];
                c.bind[k] = mm;
            }
            b.F32(); b.F32();
            int nc = b.I32();
            for (int k = 0; k < nc; k++)
            {
                var clip = new Clip { name = b.Str(), length = b.F32() };
                clip.loop = b.I32() != 0;
                clip.speed = b.F32();
                clip.frames = b.I32();
                clip.fps = b.F32();
                int n = nb * clip.frames;
                float[] cp = b.Floats(n * 3), cr = b.Floats(n * 4);
                clip.P = new Vector3[n];
                clip.R = new Quaternion[n];
                for (int i = 0; i < n; i++)
                {
                    clip.P[i] = new Vector3(cp[i * 3], cp[i * 3 + 1], cp[i * 3 + 2]);
                    clip.R[i] = new Quaternion(cr[i * 4], cr[i * 4 + 1], cr[i * 4 + 2], cr[i * 4 + 3]);
                }
                c.clips[clip.name] = clip;
            }
            if (!b.End) { c.hand = b.V3(); c.handTip = b.V3(); c.handL = b.V3(); c.headTop = b.V3(); }

            var mesh = new Mesh { name = name };
            if (nv > 65000) mesh.indexFormat = IndexFormat.UInt32;
            var vp = new Vector3[nv];
            var vn = new Vector3[nv];
            var vu = new Vector2[nv];
            var w = new BoneWeight[nv];
            var tmp = new KeyValuePair<int, float>[4];
            for (int i = 0; i < nv; i++)
            {
                vp[i] = new Vector3(P[i * 3], P[i * 3 + 1], P[i * 3 + 2]);
                vn[i] = new Vector3(N[i * 3], N[i * 3 + 1], N[i * 3 + 2]);
                vu[i] = new Vector2(UV[i * 2], UV[i * 2 + 1]);
                float sum = 0f;
                for (int j = 0; j < 4; j++) { tmp[j] = new KeyValuePair<int, float>(Mathf.Clamp(bi[i * 4 + j], 0, nb - 1), Mathf.Max(0f, bw[i * 4 + j])); sum += tmp[j].Value; }
                System.Array.Sort(tmp, (x, y) => y.Value.CompareTo(x.Value));
                if (sum < 1e-5f) { tmp[0] = new KeyValuePair<int, float>(0, 1f); sum = 1f; }
                w[i] = new BoneWeight
                {
                    boneIndex0 = tmp[0].Key, weight0 = tmp[0].Value / sum, boneIndex1 = tmp[1].Key, weight1 = tmp[1].Value / sum,
                    boneIndex2 = tmp[2].Key, weight2 = tmp[2].Value / sum, boneIndex3 = tmp[3].Key, weight3 = tmp[3].Value / sum
                };
            }
            mesh.vertices = vp;
            mesh.normals = vn;
            mesh.uv = vu;
            mesh.triangles = I;
            mesh.boneWeights = w;
            mesh.bindposes = c.bind;
            mesh.RecalculateBounds();
            mesh.RecalculateTangents();
            c.mesh = mesh;
            c.upper = new bool[nb];
            int spine = c.Bone("Spine");
            for (int k = 0; k < nb; k++)
            {
                int q = k;
                while (q >= 0 && q != spine) q = c.parent[q];
                c.upper[k] = q == spine;
            }
            return c;
        }
    }

    /// <summary>One character on screen: bones, skinned mesh and a clip player with cross-fades and an upper-body layer.</summary>
    public class Rig : MonoBehaviour
    {
        public CharData data;
        public Transform[] bones;
        public SkinnedMeshRenderer smr;
        Clip cur, prev, up;
        float tCur, tPrev, fade, fadeLen = 0.2f, upW, upTarget, tUp;
        public float speed = 1f;
        public string Current => cur != null ? cur.name : "";
        public float Normalized => cur == null ? 0f : (cur.length > 0 ? tCur / cur.length : 0f);
        public bool Finished => cur != null && !cur.loop && tCur >= cur.length - 1e-3f;
        public float updateEvery;
        float acc;

        public static Rig Create(string model, Transform parent, Color tint)
        {
            CharData d = Models.Char(model);
            var go = new GameObject("rig_" + model);
            go.transform.SetParent(parent, false);
            var rig = go.AddComponent<Rig>();
            rig.data = d;
            if (d == null) return rig;
            int nb = d.bones.Length;
            rig.bones = new Transform[nb];
            for (int k = 0; k < nb; k++)
            {
                var t = new GameObject(d.bones[k]).transform;
                t.SetParent(d.parent[k] >= 0 ? rig.bones[d.parent[k]] : go.transform, false);
                t.localPosition = d.rest[k];
                rig.bones[k] = t;
            }
            var mgo = new GameObject("mesh");
            mgo.transform.SetParent(go.transform, false);
            var smr = mgo.AddComponent<SkinnedMeshRenderer>();
            smr.sharedMesh = d.mesh;
            smr.bones = rig.bones;
            smr.rootBone = rig.bones[0];
            smr.sharedMaterial = Models.Mat("Chars", model, tint);
            smr.updateWhenOffscreen = false;
            smr.shadowCastingMode = ShadowCastingMode.Off;
            smr.receiveShadows = false;
            smr.lightProbeUsage = LightProbeUsage.Off;
            smr.reflectionProbeUsage = ReflectionProbeUsage.Off;
            smr.localBounds = new Bounds(new Vector3(0, 0.1f, 0), new Vector3(2.4f, 2.6f, 2.4f));
            smr.quality = SkinQuality.Bone4;
            rig.smr = smr;
            rig.Play("idle", 0f);
            return rig;
        }

        public Transform Bone(string n)
        {
            if (data == null) return transform;
            int i = data.Bone(n);
            return i >= 0 ? bones[i] : transform;
        }

        public bool Has(string clip) { return data != null && data.clips.ContainsKey(clip); }

        public void Play(string clip, float fadeTime = 0.2f, float spd = 1f, bool restart = false)
        {
            speed = spd;
            if (data == null) return;
            Clip c;
            if (!data.clips.TryGetValue(clip, out c)) return;
            if (c == cur && !restart) return;
            prev = cur;
            tPrev = tCur;
            cur = c;
            tCur = 0f;
            fadeLen = Mathf.Max(0.0001f, fadeTime);
            fade = prev == null || fadeTime <= 0f ? 1f : 0f;
        }

        /// <summary>Upper-body layer (aiming while running); null to blend it out.</summary>
        public void Upper(string clip, float weight = 1f)
        {
            if (data == null) return;
            Clip c = null;
            if (clip != null) data.clips.TryGetValue(clip, out c);
            if (c != null && c != up) { up = c; tUp = 0f; }
            upTarget = c != null ? weight : 0f;
        }

        public void RestartUpper() { tUp = 0f; }

        void LateUpdate()
        {
            if (data == null || cur == null) return;
            float dt = Time.deltaTime;
            if (updateEvery > 0f)
            {
                acc += dt;
                if (acc < updateEvery) return;
                dt = acc;
                acc = 0f;
            }
            tCur += dt * speed;
            if (cur.loop) tCur = Mathf.Repeat(tCur, cur.length); else tCur = Mathf.Min(tCur, cur.length);
            if (prev != null && fade < 1f)
            {
                tPrev += dt * speed;
                tPrev = prev.loop ? Mathf.Repeat(tPrev, prev.length) : Mathf.Min(tPrev, prev.length);
                fade = Mathf.Min(1f, fade + dt / fadeLen);
            }
            upW = Mathf.MoveTowards(upW, upTarget, dt * 6f);
            if (up != null)
            {
                tUp += dt;
                tUp = up.loop ? Mathf.Repeat(tUp, up.length) : Mathf.Min(tUp, up.length);
            }
            int nb = bones.Length;
            for (int k = 0; k < nb; k++)
            {
                Vector3 p;
                Quaternion r;
                Sample(cur, tCur, k, out p, out r);
                if (prev != null && fade < 1f)
                {
                    Vector3 p2;
                    Quaternion r2;
                    Sample(prev, tPrev, k, out p2, out r2);
                    p = Vector3.Lerp(p2, p, fade);
                    r = Quaternion.Slerp(r2, r, fade);
                }
                if (up != null && upW > 0.001f && data.upper[k])
                {
                    Vector3 p3;
                    Quaternion r3;
                    Sample(up, tUp, k, out p3, out r3);
                    r = Quaternion.Slerp(r, r3, upW);
                    if (k != 0) p = Vector3.Lerp(p, p3, upW);
                }
                bones[k].localPosition = p;
                bones[k].localRotation = r;
            }
        }

        static void Sample(Clip c, float t, int bone, out Vector3 p, out Quaternion r)
        {
            float f = t * c.fps;
            int f0 = Mathf.Clamp((int)f, 0, c.frames - 1);
            int f1 = c.loop ? (f0 + 1) % c.frames : Mathf.Min(f0 + 1, c.frames - 1);
            float a = Mathf.Clamp01(f - f0);
            int i0 = bone * c.frames + f0, i1 = bone * c.frames + f1;
            p = Vector3.LerpUnclamped(c.P[i0], c.P[i1], a);
            r = Quaternion.SlerpUnclamped(c.R[i0], c.R[i1], a);
        }
    }
}
