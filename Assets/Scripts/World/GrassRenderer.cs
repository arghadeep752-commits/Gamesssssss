using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace RealFPS
{
    /// <summary>
    /// Instanced grass: small patches of grass cards (cut from the Poly Haven grass
    /// atlas) scattered over the meadow parts of the terrain, drawn only near the
    /// camera and faded out with distance.
    /// </summary>
    public class GrassRenderer : MonoBehaviour
    {
        public Terrain terrain;
        public Material material;
        public float[] rects;      // atlas cells: u0,v0,u1,v1 per cell
        public int[] kinds;        // 0 tall plant, 1 wide tuft, 2 small tuft
        public float waterLevel = 21f;
        public Vector3 worldCenter;
        public float worldRadius = 180f;
        public float spacing = 1.35f;

        class Chunk
        {
            public Bounds bounds;
            public List<Matrix4x4>[] lists;
            public Matrix4x4[][] arrays;
        }

        const float ChunkSize = 16f;
        const int PatchVariants = 4;
        Mesh[] patches;
        readonly List<Chunk> chunks = new List<Chunk>();
        readonly Plane[] planes = new Plane[6];
        float distance = 30f;
        static readonly int FadeStartId = Shader.PropertyToID("_FadeStart");
        static readonly int FadeEndId = Shader.PropertyToID("_FadeEnd");

        public int InstanceCount { get; private set; }

        void Start()
        {
            if (terrain == null || material == null || rects == null || rects.Length < 4) { enabled = false; return; }
            patches = new Mesh[PatchVariants];
            for (int i = 0; i < PatchVariants; i++) patches[i] = BuildPatch(1000 + i * 77);
            Scatter();
            SetDistance(distance);
            Debug.Log("[RF] grass instances " + InstanceCount + " in " + chunks.Count + " chunks");
        }

        public void SetDistance(float d)
        {
            distance = d;
            if (material != null)
            {
                material.SetFloat(FadeStartId, d * 0.6f);
                material.SetFloat(FadeEndId, Mathf.Max(1f, d));
            }
        }

        Mesh BuildPatch(int seed)
        {
            var r = new System.Random(seed);
            System.Func<float, float, float> rnd = (a, b) => a + (float)r.NextDouble() * (b - a);
            var v = new List<Vector3>();
            var uv = new List<Vector2>();
            var n = new List<Vector3>();
            var c = new List<Color>();
            var tri = new List<int>();
            int cells = rects.Length / 4;
            int cards = 8;
            for (int k = 0; k < cards; k++)
            {
                // favour the small tufts, mix in tall plants and wide clumps
                double pick = r.NextDouble();
                int kind = pick < 0.5 ? 2 : (pick < 0.78 ? 1 : 0);
                var options = new List<int>();
                for (int i = 0; i < cells; i++) if (kinds == null || i >= kinds.Length || kinds[i] == kind) options.Add(i);
                if (options.Count == 0) for (int i = 0; i < cells; i++) options.Add(i);
                int cell = options[r.Next(options.Count)];
                float u0 = rects[cell * 4], v0 = rects[cell * 4 + 1], u1 = rects[cell * 4 + 2], v1 = rects[cell * 4 + 3];
                float aspect = (u1 - u0) / Mathf.Max(0.001f, v1 - v0);
                float h = kind == 0 ? rnd(0.5f, 0.85f) : (kind == 1 ? rnd(0.26f, 0.4f) : rnd(0.3f, 0.48f));
                float w = h * aspect;
                float ang = rnd(0f, Mathf.PI * 2f);
                float rad = Mathf.Sqrt(rnd(0f, 1f)) * 0.62f;
                Vector3 center = new Vector3(Mathf.Cos(ang) * rad, -0.03f, Mathf.Sin(ang) * rad);
                int quads = kind == 0 ? 2 : 3;
                float yaw0 = rnd(0f, 180f);
                float phase = rnd(0f, 1f);
                Vector3 lean = new Vector3(rnd(-0.08f, 0.08f), 0f, rnd(-0.08f, 0.08f));
                for (int q = 0; q < quads; q++)
                {
                    float yaw = (yaw0 + q * 180f / quads) * Mathf.Deg2Rad;
                    Vector3 dir = new Vector3(Mathf.Cos(yaw), 0f, Mathf.Sin(yaw)) * (w * 0.5f);
                    int b = v.Count;
                    Vector3 top = Vector3.up * h + lean * h;
                    v.Add(center - dir); v.Add(center + dir); v.Add(center + dir + top); v.Add(center - dir + top);
                    uv.Add(new Vector2(u0, v0)); uv.Add(new Vector2(u1, v0)); uv.Add(new Vector2(u1, v1)); uv.Add(new Vector2(u0, v1));
                    Vector3 side = Vector3.Cross(dir.normalized, Vector3.up) * 0.25f;
                    Vector3 nb = (Vector3.up + side).normalized;
                    Vector3 nt = (Vector3.up * 1.2f + side * 0.6f).normalized;
                    n.Add(nb); n.Add(nb); n.Add(nt); n.Add(nt);
                    Color bottom = new Color(0.5f, 0f, phase, 1f);
                    Color topC = new Color(1f, 1f, phase, 1f);
                    c.Add(bottom); c.Add(bottom); c.Add(topC); c.Add(topC);
                    tri.Add(b); tri.Add(b + 2); tri.Add(b + 1);
                    tri.Add(b); tri.Add(b + 3); tri.Add(b + 2);
                }
            }
            var m = new Mesh { name = "GrassPatch" + seed };
            m.SetVertices(v);
            m.SetUVs(0, uv);
            m.SetNormals(n);
            m.SetColors(c);
            m.SetTriangles(tri, 0);
            m.RecalculateBounds();
            m.bounds = new Bounds(new Vector3(0f, 0.5f, 0f), new Vector3(2.4f, 1.4f, 2.4f));
            m.UploadMeshData(true);
            return m;
        }

        void Scatter()
        {
            TerrainData td = terrain.terrainData;
            int aw = td.alphamapWidth, ah = td.alphamapHeight;
            float[,,] alpha = td.GetAlphamaps(0, 0, aw, ah);
            int layers = alpha.GetLength(2);
            Vector3 tpos = terrain.transform.position;
            Vector3 size = td.size;
            var r = new System.Random(4242);
            var map = new Dictionary<long, Chunk>();
            float R = worldRadius + 10f;
            for (float x = worldCenter.x - R; x < worldCenter.x + R; x += spacing)
            {
                for (float z = worldCenter.z - R; z < worldCenter.z + R; z += spacing)
                {
                    float px = x + ((float)r.NextDouble() - 0.5f) * spacing * 0.9f;
                    float pz = z + ((float)r.NextDouble() - 0.5f) * spacing * 0.9f;
                    float dx = px - worldCenter.x, dz = pz - worldCenter.z;
                    if (dx * dx + dz * dz > R * R) continue;
                    float u = (px - tpos.x) / size.x, w = (pz - tpos.z) / size.z;
                    if (u < 0f || u > 1f || w < 0f || w > 1f) continue;
                    int ax = Mathf.Clamp((int)(u * (aw - 1) + 0.5f), 0, aw - 1);
                    int az = Mathf.Clamp((int)(w * (ah - 1) + 0.5f), 0, ah - 1);
                    float g = alpha[az, ax, 0];
                    float dirt = layers > 1 ? alpha[az, ax, 1] : 0f;
                    float keep = Mathf.Clamp01((g - 0.3f) * 1.7f) * (1f - dirt * 0.6f);
                    keep *= Mathf.Lerp(0.45f, 1.15f, Mathf.PerlinNoise(px * 0.045f + 11f, pz * 0.045f + 7f));
                    if ((float)r.NextDouble() > keep) continue;
                    float y = terrain.SampleHeight(new Vector3(px, 0f, pz)) + tpos.y;
                    if (y < waterLevel + 0.25f) continue;
                    Vector3 nrm = td.GetInterpolatedNormal(u, w);
                    if (nrm.y < 0.82f) continue;
                    Quaternion rot = Quaternion.FromToRotation(Vector3.up, nrm) * Quaternion.Euler(0f, (float)r.NextDouble() * 360f, 0f);
                    float s = 0.78f + (float)r.NextDouble() * 0.5f;
                    int variant = r.Next(PatchVariants);
                    int cx = Mathf.FloorToInt(px / ChunkSize), cz = Mathf.FloorToInt(pz / ChunkSize);
                    long key = ((long)cx << 32) ^ (uint)cz;
                    Chunk ch;
                    if (!map.TryGetValue(key, out ch))
                    {
                        ch = new Chunk
                        {
                            bounds = new Bounds(new Vector3((cx + 0.5f) * ChunkSize, y, (cz + 0.5f) * ChunkSize), new Vector3(ChunkSize + 3f, 4f, ChunkSize + 3f)),
                            lists = new List<Matrix4x4>[PatchVariants]
                        };
                        for (int i = 0; i < PatchVariants; i++) ch.lists[i] = new List<Matrix4x4>();
                        map[key] = ch;
                    }
                    ch.bounds.Encapsulate(new Vector3(px, y + 1.2f, pz));
                    ch.bounds.Encapsulate(new Vector3(px, y - 0.5f, pz));
                    ch.lists[variant].Add(Matrix4x4.TRS(new Vector3(px, y, pz), rot, Vector3.one * s));
                    InstanceCount++;
                }
            }
            foreach (Chunk ch in map.Values)
            {
                ch.arrays = new Matrix4x4[PatchVariants][];
                for (int i = 0; i < PatchVariants; i++)
                {
                    List<Matrix4x4> l = ch.lists[i];
                    if (l.Count > 1023) l.RemoveRange(1023, l.Count - 1023);
                    ch.arrays[i] = l.ToArray();
                }
                ch.lists = null;
                chunks.Add(ch);
            }
        }

        void Update()
        {
            if (distance <= 0.5f || patches == null) return;
            Camera cam = Camera.main;
            if (cam == null) return;
            GeometryUtility.CalculateFrustumPlanes(cam, planes);
            Vector3 cp = cam.transform.position;
            float maxD = distance + ChunkSize;
            for (int i = 0; i < chunks.Count; i++)
            {
                Chunk ch = chunks[i];
                Vector3 c = ch.bounds.center;
                float dx = c.x - cp.x, dz = c.z - cp.z;
                if (dx * dx + dz * dz > maxD * maxD) continue;
                if (!GeometryUtility.TestPlanesAABB(planes, ch.bounds)) continue;
                for (int k = 0; k < PatchVariants; k++)
                {
                    Matrix4x4[] arr = ch.arrays[k];
                    if (arr.Length == 0) continue;
                    Graphics.DrawMeshInstanced(patches[k], 0, material, arr, arr.Length, null, ShadowCastingMode.Off, true, 0, null, LightProbeUsage.BlendProbes);
                }
            }
        }
    }
}
