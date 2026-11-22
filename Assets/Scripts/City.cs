using System.Collections.Generic;
using System.Runtime.InteropServices;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Rendering;

namespace Danga
{
    /// <summary>
    /// Agartala: streams the 128 m map chunks built by tools/city (render meshes straight from the file's vertex
    /// layout, collision meshes, building boxes), the sea and far hills, the water levels and the street lamps.
    /// </summary>
    public class City : MonoBehaviour
    {
        public static City I;
        public static float Half = 1100f;
        public const int LayerWorld = 0, LayerVehicle = 9, LayerPed = 10, LayerPlayer = 11;
        public object meta;
        public float chunkSize = 128f, renderDist = 420f, collDist = 170f;

        [StructLayout(LayoutKind.Sequential)]
        struct Vtx { public float px, py, pz; public uint n, c; public float u, v; public uint x; }

        struct Group { public int id, off; }

        class Chunk
        {
            public int ix, iz;
            public Vector3 centre;
            public List<Group> groups = new List<Group>();
            public GameObject go, coll;
            public bool rLoaded, cLoaded;
            public List<Mesh> meshes = new List<Mesh>();
            public Mesh collMesh;
            public List<GameObject> boxes = new List<GameObject>();
        }

        TextAsset chunksAsset;
        NativeArray<byte> data;
        readonly List<Chunk> chunks = new List<Chunk>();
        readonly Dictionary<long, Chunk> byKey = new Dictionary<long, Chunk>();
        Material[] mats = new Material[4];
        Material seaMat;
        short[] water;
        int wn;
        float wcell = 4f;
        public readonly List<Vector3> lamps = new List<Vector3>();
        public readonly List<MapPoint> points = new List<MapPoint>();
        public readonly List<Zone> zones = new List<Zone>();
        static readonly VertexAttributeDescriptor[] Layout =
        {
            new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 3),
            new VertexAttributeDescriptor(VertexAttribute.Normal, VertexAttributeFormat.SNorm8, 4),
            new VertexAttributeDescriptor(VertexAttribute.Color, VertexAttributeFormat.UNorm8, 4),
            new VertexAttributeDescriptor(VertexAttribute.TexCoord0, VertexAttributeFormat.Float32, 2),
            new VertexAttributeDescriptor(VertexAttribute.TexCoord1, VertexAttributeFormat.UNorm8, 4),
        };
        bool packedOk = true;
        int cursor;
        public int loadedChunks;

        public class MapPoint { public string kind, name, label, model; public Vector3 p; public float yaw; public bool parked, owned; }
        public class Zone { public string name; public Vector2 c; public float r; }

        public static long Key(int ix, int iz) { return ((long)ix << 32) ^ (uint)iz; }

        public void Init()
        {
            I = this;
            var mt = Resources.Load<TextAsset>("city_meta");
            meta = mt != null ? Json.Parse(mt.text) : new Dictionary<string, object>();
            Half = Json.F(meta, "half", 1100f);
            chunkSize = Json.F(meta, "chunk", 128f);
            ReadMeta();
            packedOk = SystemInfo.SupportsVertexAttributeFormat(VertexAttributeFormat.SNorm8, 4) && SystemInfo.SupportsVertexAttributeFormat(VertexAttributeFormat.UNorm8, 4);
            MakeMaterials();
            chunksAsset = Resources.Load<TextAsset>("Gen/City/chunks");
            if (chunksAsset != null)
            {
                data = chunksAsset.GetData<byte>();
                ReadDirectory();
            }
            else Debug.LogWarning("[DG] city chunks missing");
            LoadExtras();
            LoadColliders();
            LoadWater();
            BuildLampGlows();
            Debug.Log("[DG] city: " + chunks.Count + " chunks, " + lamps.Count + " lamps, " + points.Count + " points, packed vertices " + packedOk);
        }

        void ReadMeta()
        {
            var lp = Json.A(meta, "lamps");
            if (lp != null) foreach (object l in lp) lamps.Add(Json.V3(l));
            var pts = Json.A(meta, "points");
            if (pts != null)
                foreach (object o in pts)
                    points.Add(new MapPoint
                    {
                        kind = Json.S(o, "kind"), name = Json.S(o, "name"), label = Json.S(o, "label", Json.S(o, "name")), model = Json.S(o, "model"),
                        p = Json.V3(o, "p"), yaw = Json.F(o, "yaw"), parked = Json.Has(o, "parked") && (bool)Json.Get(o, "parked"),
                        owned = Json.Has(o, "owned") && (bool)Json.Get(o, "owned")
                    });
            var lm = Json.A(meta, "landmarks");
            if (lm != null)
                foreach (object o in lm)
                    points.Add(new MapPoint { kind = "landmark", name = Json.S(o, "name"), label = Json.S(o, "label", Json.S(o, "name")), p = Json.V3(o, "p"), yaw = Json.F(o, "yaw") });
            var zs = Json.A(meta, "zones");
            if (zs != null)
                foreach (object o in zs)
                {
                    var c = Json.A(o, "c");
                    zones.Add(new Zone { name = Json.S(o, "name"), c = new Vector2(Json.At(c, 0), Json.At(c, 1)), r = Json.F(o, "r", 100f) });
                }
        }

        public MapPoint Point(string kind)
        {
            foreach (var p in points) if (p.kind == kind) return p;
            return null;
        }

        public string ZoneAt(Vector3 p)
        {
            string best = null;
            float bd = 1e9f;
            foreach (var z in zones)
            {
                float d = Vector2.Distance(new Vector2(p.x, p.z), z.c);
                if (d < z.r && d / z.r < bd) { bd = d / z.r; best = z.name; }
            }
            return best ?? "Agartala";
        }

        void MakeMaterials()
        {
            var albedo = Resources.Load<Texture2DArray>("Gen/City/layers");
            var normals = Resources.Load<Texture2DArray>("Gen/City/layers_n");
            if (albedo == null) Debug.LogWarning("[DG] city texture array missing");
            string[] sh = { "Danga/World", "Danga/Foliage", "Danga/Water", "Danga/Terrain" };
            for (int i = 0; i < 4; i++)
            {
                Shader s = Shader.Find(sh[i]);
                mats[i] = new Material(s != null ? s : Shader.Find("Unlit/Color")) { name = sh[i] };
                if (albedo != null && mats[i].HasProperty("_Tex")) mats[i].SetTexture("_Tex", albedo);
                if (normals != null && mats[i].HasProperty("_Nrm")) mats[i].SetTexture("_Nrm", normals);
            }
            if (normals != null && QualitySettings.GetQualityLevel() >= 3) mats[0].EnableKeyword("DG_NORMALMAP");
            seaMat = new Material(mats[2]) { name = "Sea" };
            seaMat.SetFloat("_Waves", 2.2f);
            seaMat.SetColor("_Deep", new Color(0.03f, 0.13f, 0.20f));
            seaMat.SetColor("_Shallow", new Color(0.10f, 0.30f, 0.32f));
        }

        public void SetNormalMaps(bool on)
        {
            if (on) mats[0].EnableKeyword("DG_NORMALMAP"); else mats[0].DisableKeyword("DG_NORMALMAP");
        }

        int I32(int off) { return data.ReinterpretLoad<int>(off); }

        void ReadDirectory()
        {
            int p = 0;
            if (I32(0) != 0x31434744) { Debug.LogWarning("[DG] bad chunks file"); return; }
            chunkSize = data.ReinterpretLoad<float>(8);
            int count = I32(16);
            p = 20;
            for (int k = 0; k < count; k++)
            {
                var c = new Chunk { ix = I32(p), iz = I32(p + 4) };
                int ng = I32(p + 8);
                p += 12;
                c.centre = new Vector3((c.ix + 0.5f) * chunkSize - Half, 0f, (c.iz + 0.5f) * chunkSize - Half);
                for (int g = 0; g < ng; g++)
                {
                    int id = I32(p);
                    p += 4;
                    c.groups.Add(new Group { id = id, off = p });
                    int nv = I32(p);
                    if (id == 4)
                    {
                        p += 4 + nv * 12;
                        int ni = I32(p);
                        p += 4 + ni * 4;
                    }
                    else
                    {
                        p += 4 + 24 + nv * 32;
                        int ni = I32(p), isz = I32(p + 4);
                        p += 8 + ni * isz;
                        if (isz == 2 && (ni & 1) == 1) p += 2;
                    }
                }
                chunks.Add(c);
                byKey[Key(c.ix, c.iz)] = c;
            }
        }

        Mesh RenderMesh(int off, string name)
        {
            int nv = I32(off);
            var mn = new Vector3(data.ReinterpretLoad<float>(off + 4), data.ReinterpretLoad<float>(off + 8), data.ReinterpretLoad<float>(off + 12));
            var mx = new Vector3(data.ReinterpretLoad<float>(off + 16), data.ReinterpretLoad<float>(off + 20), data.ReinterpretLoad<float>(off + 24));
            int vo = off + 28;
            int io = vo + nv * 32;
            int ni = I32(io), isz = I32(io + 4);
            io += 8;
            var m = new Mesh { name = name };
            var bounds = new Bounds((mn + mx) * 0.5f, mx - mn + Vector3.one * 0.5f);
            const MeshUpdateFlags fl = MeshUpdateFlags.DontRecalculateBounds | MeshUpdateFlags.DontValidateIndices | MeshUpdateFlags.DontNotifyMeshUsers;
            if (packedOk)
            {
                m.SetVertexBufferParams(nv, Layout);
                m.SetVertexBufferData(data.GetSubArray(vo, nv * 32).Reinterpret<Vtx>(1), 0, 0, nv, 0, fl);
            }
            else
            {
                var src = data.GetSubArray(vo, nv * 32).Reinterpret<Vtx>(1);
                var P = new Vector3[nv];
                var N = new Vector3[nv];
                var C = new Color32[nv];
                var U = new Vector2[nv];
                var X = new Vector4[nv];
                for (int i = 0; i < nv; i++)
                {
                    Vtx v = src[i];
                    P[i] = new Vector3(v.px, v.py, v.pz);
                    N[i] = new Vector3((sbyte)(v.n & 255), (sbyte)((v.n >> 8) & 255), (sbyte)((v.n >> 16) & 255)) / 127f;
                    C[i] = new Color32((byte)(v.c & 255), (byte)((v.c >> 8) & 255), (byte)((v.c >> 16) & 255), (byte)(v.c >> 24));
                    U[i] = new Vector2(v.u, v.v);
                    X[i] = new Vector4((v.x & 255) / 255f, ((v.x >> 8) & 255) / 255f, ((v.x >> 16) & 255) / 255f, (v.x >> 24) / 255f);
                }
                if (nv > 65000) m.indexFormat = IndexFormat.UInt32;
                m.vertices = P;
                m.normals = N;
                m.colors32 = C;
                m.uv = U;
                m.SetUVs(1, X);
            }
            if (isz == 2)
            {
                m.SetIndexBufferParams(ni, IndexFormat.UInt16);
                m.SetIndexBufferData(data.GetSubArray(io, ni * 2).Reinterpret<ushort>(1), 0, 0, ni, fl);
            }
            else
            {
                m.SetIndexBufferParams(ni, IndexFormat.UInt32);
                m.SetIndexBufferData(data.GetSubArray(io, ni * 4).Reinterpret<uint>(1), 0, 0, ni, fl);
            }
            m.subMeshCount = 1;
            m.SetSubMesh(0, new SubMeshDescriptor(0, ni) { bounds = bounds, vertexCount = nv }, fl);
            m.bounds = bounds;
            m.UploadMeshData(true);
            return m;
        }

        Mesh CollisionMesh(int off)
        {
            int nv = I32(off);
            var P = new Vector3[nv];
            var src = data.GetSubArray(off + 4, nv * 12).Reinterpret<Vector3>(1);
            src.CopyTo(P);
            int io = off + 4 + nv * 12;
            int ni = I32(io);
            var I = new int[ni];
            data.GetSubArray(io + 4, ni * 4).Reinterpret<int>(1).CopyTo(I);
            var m = new Mesh { name = "coll" };
            if (nv > 65000) m.indexFormat = IndexFormat.UInt32;
            m.vertices = P;
            m.triangles = I;
            return m;
        }

        void LoadChunk(Chunk c)
        {
            c.go = new GameObject("chunk_" + c.ix + "_" + c.iz);
            c.go.transform.SetParent(transform, false);
            foreach (var g in c.groups)
            {
                if (g.id == 4) continue;
                Mesh m = RenderMesh(g.off, "g" + g.id);
                c.meshes.Add(m);
                var go = new GameObject("g" + g.id);
                go.transform.SetParent(c.go.transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = m;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = mats[Mathf.Clamp(g.id, 0, 3)];
                mr.shadowCastingMode = ShadowCastingMode.Off;
                mr.receiveShadows = false;
                mr.lightProbeUsage = LightProbeUsage.Off;
                mr.reflectionProbeUsage = ReflectionProbeUsage.Off;
            }
            loadedChunks++;
        }

        void UnloadChunk(Chunk c)
        {
            if (c.go != null) Destroy(c.go);
            foreach (var m in c.meshes) Destroy(m);
            c.meshes.Clear();
            c.go = null;
            loadedChunks--;
        }

        void LoadColl(Chunk c)
        {
            foreach (var g in c.groups)
            {
                if (g.id != 4) continue;
                c.collMesh = CollisionMesh(g.off);
                c.coll = new GameObject("coll_" + c.ix + "_" + c.iz);
                c.coll.transform.SetParent(transform, false);
                c.coll.AddComponent<MeshCollider>().sharedMesh = c.collMesh;
            }
            foreach (var b in c.boxes) b.SetActive(true);
        }

        void UnloadColl(Chunk c)
        {
            if (c.coll != null) Destroy(c.coll);
            if (c.collMesh != null) Destroy(c.collMesh);
            c.coll = null;
            c.collMesh = null;
            foreach (var b in c.boxes) b.SetActive(false);
        }

        /// <summary>Loads the chunks near 'focus' (at most a few per call) and drops the far ones.</summary>
        public void Stream(Vector3 focus, int budget)
        {
            if (chunks.Count == 0) return;
            int n = chunks.Count;
            float r2 = renderDist + chunkSize * 0.71f, c2 = collDist + chunkSize * 0.71f;
            for (int k = 0; k < n && budget > 0; k++)
            {
                cursor = (cursor + 1) % n;
                Chunk c = chunks[cursor];
                float d = Vector2.Distance(new Vector2(c.centre.x, c.centre.z), new Vector2(focus.x, focus.z));
                bool wantR = d < r2, wantC = d < c2;
                if (wantR && !c.rLoaded) { LoadChunk(c); c.rLoaded = true; budget--; }
                else if (!wantR && d > r2 + 60f && c.rLoaded) { UnloadChunk(c); c.rLoaded = false; }
                if (wantC && !c.cLoaded) { LoadColl(c); c.cLoaded = true; budget--; }
                else if (!wantC && d > c2 + 40f && c.cLoaded) { UnloadColl(c); c.cLoaded = false; }
            }
        }

        /// <summary>Loads everything near a point at once (start, teleports).</summary>
        public void StreamNow(Vector3 focus)
        {
            for (int i = 0; i < 4; i++) Stream(focus, 100000);
        }

        public bool CollisionReady(Vector3 p)
        {
            int ix = Mathf.FloorToInt((p.x + Half) / chunkSize), iz = Mathf.FloorToInt((p.z + Half) / chunkSize);
            Chunk c;
            return !byKey.TryGetValue(Key(ix, iz), out c) || c.cLoaded;
        }

        void LoadExtras()
        {
            var ta = Resources.Load<TextAsset>("Gen/City/extras");
            if (ta == null) return;
            NativeArray<byte> d = ta.GetData<byte>();
            byte[] all = ta.bytes;
            int p = 8, count = System.BitConverter.ToInt32(all, 4);
            for (int k = 0; k < count; k++)
            {
                int len = System.BitConverter.ToInt32(all, p);
                string name = System.Text.Encoding.UTF8.GetString(all, p + 4, len);
                p += 4 + len;
                // the render-group block is copied to an aligned buffer and read like a chunk group
                int nv = System.BitConverter.ToInt32(all, p);
                int io = p + 28 + nv * 32;
                int ni = System.BitConverter.ToInt32(all, io), isz = System.BitConverter.ToInt32(all, io + 4);
                int size = 28 + nv * 32 + 8 + ni * isz + ((isz == 2 && (ni & 1) == 1) ? 2 : 0);
                var tmp = new NativeArray<byte>(size, Allocator.Temp);
                NativeArray<byte>.Copy(d, p, tmp, 0, size);
                var saved = data;
                data = tmp;
                Mesh m = RenderMesh(0, name);
                data = saved;
                tmp.Dispose();
                p += size;
                var go = new GameObject("extra_" + name);
                go.transform.SetParent(transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = m;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = name == "sea" ? seaMat : mats[0];
                mr.shadowCastingMode = ShadowCastingMode.Off;
                mr.receiveShadows = false;
            }
        }

        void LoadColliders()
        {
            var ta = Resources.Load<TextAsset>("Gen/City/colliders");
            if (ta == null) return;
            var b = new Bin(ta.bytes);
            b.I32();
            int n = b.I32();
            float[] f = b.Floats(n * 7);
            var groups = new Dictionary<long, GameObject>();
            for (int i = 0; i < n; i++)
            {
                float cx = f[i * 7], cy = f[i * 7 + 1], cz = f[i * 7 + 2], sx = f[i * 7 + 3], sy = f[i * 7 + 4], sz = f[i * 7 + 5], yaw = f[i * 7 + 6];
                int ix = Mathf.FloorToInt((cx + Half) / chunkSize), iz = Mathf.FloorToInt((cz + Half) / chunkSize);
                int yk = Mathf.RoundToInt(Mathf.Repeat(yaw, 360f) * 4f);
                long key = Key(ix, iz) * 2000 + yk;
                GameObject g;
                if (!groups.TryGetValue(key, out g))
                {
                    g = new GameObject("boxes");
                    g.transform.SetParent(transform, false);
                    g.transform.SetPositionAndRotation(new Vector3((ix + 0.5f) * chunkSize - Half, 0f, (iz + 0.5f) * chunkSize - Half), Quaternion.Euler(0f, yk / 4f, 0f));
                    groups[key] = g;
                    Chunk c;
                    if (byKey.TryGetValue(Key(ix, iz), out c)) { c.boxes.Add(g); g.SetActive(false); }
                }
                var bc = g.AddComponent<BoxCollider>();
                Vector3 world = new Vector3(cx, cy + sy * 0.5f, cz);
                bc.center = g.transform.InverseTransformPoint(world);
                bc.size = new Vector3(Mathf.Max(0.05f, sx), Mathf.Max(0.05f, sy), Mathf.Max(0.05f, sz));
            }
            Resources.UnloadAsset(ta);
        }

        void LoadWater()
        {
            var ta = Resources.Load<TextAsset>("Gen/City/water");
            if (ta == null) return;
            byte[] b = ta.bytes;
            wn = System.BitConverter.ToInt32(b, 4);
            wcell = System.BitConverter.ToSingle(b, 8);
            water = new short[wn * wn];
            System.Buffer.BlockCopy(b, 12, water, 0, wn * wn * 2);
            Resources.UnloadAsset(ta);
        }

        /// <summary>Water surface height at (x, z), or NaN on dry land.</summary>
        public float WaterLevel(float x, float z)
        {
            if (water == null) return float.NaN;
            float sea = Json.F(meta, "sea_level", -1f);
            int i = Mathf.FloorToInt((x + Half) / wcell), j = Mathf.FloorToInt((z + Half) / wcell);
            if (i < 0 || j < 0 || i >= wn || j >= wn) return sea;      // the open sea past the map
            short v = water[j * wn + i];
            return v == short.MinValue ? float.NaN : v / 100f;
        }

        public float Ground(Vector3 p, float fallback = 0f)
        {
            RaycastHit h;
            if (Physics.Raycast(new Vector3(p.x, p.y + 30f, p.z), Vector3.down, out h, 80f, 1 << LayerWorld, QueryTriggerInteraction.Ignore)) return h.point.y;
            return fallback;
        }

        void BuildLampGlows()
        {
            if (lamps.Count == 0) return;
            var glow = Resources.Load<Texture2D>("UI/glow");
            Shader s = Shader.Find("Danga/GlowBillboard");
            if (s == null) return;
            int n = lamps.Count;
            var P = new Vector3[n * 4];
            var U = new Vector2[n * 4];
            var U2 = new Vector2[n * 4];
            var C = new Color32[n * 4];
            var I = new int[n * 6];
            Vector2[] corners = { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            for (int i = 0; i < n; i++)
            {
                for (int k = 0; k < 4; k++)
                {
                    P[i * 4 + k] = lamps[i];
                    U[i * 4 + k] = corners[k];
                    U2[i * 4 + k] = new Vector2(1.6f, 0f);
                    C[i * 4 + k] = new Color32(255, 214, 150, 230);
                }
                I[i * 6] = i * 4; I[i * 6 + 1] = i * 4 + 2; I[i * 6 + 2] = i * 4 + 1;
                I[i * 6 + 3] = i * 4; I[i * 6 + 4] = i * 4 + 3; I[i * 6 + 5] = i * 4 + 2;
            }
            var m = new Mesh { name = "lamps" };
            m.indexFormat = IndexFormat.UInt32;
            m.vertices = P;
            m.uv = U;
            m.uv2 = U2;
            m.colors32 = C;
            m.triangles = I;
            m.bounds = new Bounds(Vector3.zero, new Vector3(Half * 2, 200f, Half * 2));
            var go = new GameObject("lamp_glows");
            go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mat = new Material(s);
            if (glow != null) mat.SetTexture("_MainTex", glow);
            mat.SetFloat("_NightOnly", 1f);
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = ShadowCastingMode.Off;
        }
    }
}
