using System.Collections.Generic;
using UnityEngine;

namespace RealFPS.EditorTools
{
    /// <summary>Mesh helpers for the build: simplification, model parts, water and far mountains.</summary>
    public static class RFMeshUtil
    {
        /// <summary>
        /// Vertex-clustering simplification (for distant LODs of photo-scanned rocks).
        /// gridRes = number of cells along the longest side.
        /// </summary>
        public static Mesh Cluster(Mesh src, int gridRes, string name)
        {
            Vector3[] v = src.vertices;
            Vector3[] n = src.normals;
            Vector2[] uv = src.uv;
            bool hasN = n != null && n.Length == v.Length;
            bool hasUv = uv != null && uv.Length == v.Length;
            Bounds b = src.bounds;
            float cell = Mathf.Max(b.size.x, Mathf.Max(b.size.y, b.size.z)) / Mathf.Max(2, gridRes);
            var map = new Dictionary<long, int>();
            var pos = new List<Vector3>();
            var nor = new List<Vector3>();
            var tex = new List<Vector2>();
            var cnt = new List<int>();
            var remap = new int[v.Length];
            for (int i = 0; i < v.Length; i++)
            {
                Vector3 q = (v[i] - b.min) / cell;
                long key = ((long)Mathf.FloorToInt(q.x) & 0x1FFFFF) | (((long)Mathf.FloorToInt(q.y) & 0x1FFFFF) << 21) | (((long)Mathf.FloorToInt(q.z) & 0x1FFFFF) << 42);
                int idx;
                if (!map.TryGetValue(key, out idx))
                {
                    idx = pos.Count;
                    map[key] = idx;
                    pos.Add(Vector3.zero);
                    nor.Add(Vector3.zero);
                    tex.Add(hasUv ? uv[i] : Vector2.zero);
                    cnt.Add(0);
                }
                pos[idx] += v[i];
                if (hasN) nor[idx] += n[i];
                cnt[idx]++;
                remap[i] = idx;
            }
            for (int i = 0; i < pos.Count; i++)
            {
                pos[i] /= cnt[i];
                nor[i] = nor[i].sqrMagnitude > 1e-8f ? nor[i].normalized : Vector3.up;
            }
            var m = new Mesh { name = name };
            if (pos.Count > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            m.SetVertices(pos);
            m.SetNormals(nor);
            m.SetUVs(0, tex);
            m.subMeshCount = src.subMeshCount;
            for (int s = 0; s < src.subMeshCount; s++)
            {
                int[] t = src.GetTriangles(s);
                var outT = new List<int>(t.Length / 4);
                var seen = new HashSet<long>();
                for (int i = 0; i + 2 < t.Length; i += 3)
                {
                    int a = remap[t[i]], c = remap[t[i + 1]], d = remap[t[i + 2]];
                    if (a == c || c == d || a == d) continue;
                    // drop duplicate faces
                    int lo = Mathf.Min(a, Mathf.Min(c, d)), hi = Mathf.Max(a, Mathf.Max(c, d)), mid = a + c + d - lo - hi;
                    long k = ((long)lo << 42) ^ ((long)mid << 21) ^ hi;
                    if (!seen.Add(k)) continue;
                    outT.Add(a); outT.Add(c); outT.Add(d);
                }
                m.SetTriangles(outT, s);
            }
            m.RecalculateBounds();
            m.RecalculateTangents();
            return m;
        }

        public class Part
        {
            public Mesh mesh;
            public string name;
            public Material[] sourceMaterials;
            public Quaternion rotation;
            public Vector3 scale;
            public Vector3 centerOffset;  // bounds centre - pivot (model at the origin)
            public Vector3 size;          // world AABB size (model at the origin)
            public Mesh lod1;
        }

        /// <summary>The meshes inside an imported model, with their upright orientation.</summary>
        public static List<Part> Parts(GameObject model)
        {
            var list = new List<Part>();
            var inst = Object.Instantiate(model);
            inst.transform.position = Vector3.zero;
            inst.transform.rotation = Quaternion.identity;
            inst.transform.localScale = Vector3.one;
            foreach (MeshFilter mf in inst.GetComponentsInChildren<MeshFilter>())
            {
                var mr = mf.GetComponent<MeshRenderer>();
                if (mf.sharedMesh == null || mr == null) continue;
                Bounds wb = mr.bounds;
                list.Add(new Part
                {
                    mesh = mf.sharedMesh,
                    name = mf.name,
                    sourceMaterials = mr.sharedMaterials,
                    rotation = mf.transform.rotation,
                    scale = mf.transform.lossyScale,
                    centerOffset = wb.center - mf.transform.position,
                    size = wb.size
                });
            }
            Object.DestroyImmediate(inst);
            return list;
        }

        /// <summary>Water surface: a grid that only covers the lake (plus a margin).</summary>
        public static Mesh WaterMesh(float cell, float water)
        {
            Vector2 c = RFLayout.LakeCenter;
            float R = Mathf.Max(RFLayout.LakeRadii.x, RFLayout.LakeRadii.y) * 1.3f;
            int n = Mathf.CeilToInt(2f * R / cell);
            var verts = new List<Vector3>();
            var tris = new List<int>();
            var index = new Dictionary<int, int>();
            System.Func<int, int, int> vtx = (i, j) =>
            {
                int key = i * 10000 + j;
                int id;
                if (index.TryGetValue(key, out id)) return id;
                id = verts.Count;
                verts.Add(new Vector3(c.x - R + i * cell, water, c.y - R + j * cell));
                index[key] = id;
                return id;
            };
            for (int i = 0; i < n; i++)
            {
                for (int j = 0; j < n; j++)
                {
                    float x0 = c.x - R + i * cell, z0 = c.y - R + j * cell;
                    float e = Mathf.Min(Mathf.Min(RFLayout.LakeE(x0, z0), RFLayout.LakeE(x0 + cell, z0)),
                                        Mathf.Min(RFLayout.LakeE(x0, z0 + cell), RFLayout.LakeE(x0 + cell, z0 + cell)));
                    if (e > 1.12f) continue;
                    int a = vtx(i, j), b = vtx(i + 1, j), d = vtx(i, j + 1), f = vtx(i + 1, j + 1);
                    tris.Add(a); tris.Add(d); tris.Add(f);
                    tris.Add(a); tris.Add(f); tris.Add(b);
                }
            }
            var m = new Mesh { name = "Lake" };
            if (verts.Count > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            m.SetVertices(verts);
            var normals = new Vector3[verts.Count];
            for (int i = 0; i < normals.Length; i++) normals[i] = Vector3.up;
            m.normals = normals;
            m.SetTriangles(tris, 0);
            m.RecalculateBounds();
            return m;
        }

        /// <summary>A ring of distant mountains outside the terrain (hazy silhouettes).</summary>
        public static Mesh FarMountains(Vector2 center, float inner, float outer, int segments, int rings, float baseY)
        {
            var v = new List<Vector3>();
            var col = new List<Color>();
            var tris = new List<int>();
            Color forest = new Color(0.12f, 0.16f, 0.11f);
            Color rock = new Color(0.36f, 0.35f, 0.34f);
            Color snow = new Color(0.86f, 0.88f, 0.9f);
            for (int r = 0; r <= rings; r++)
            {
                float k = r / (float)rings;
                float rad = Mathf.Lerp(inner, outer, Mathf.Pow(k, 0.85f));
                for (int s = 0; s <= segments; s++)
                {
                    float a = s / (float)segments * Mathf.PI * 2f;
                    float x = center.x + Mathf.Cos(a) * rad, z = center.y + Mathf.Sin(a) * rad;
                    float ridge = RFLayout.Ridge(x / 420f, z / 420f, 5, 71f);
                    float envelope = Mathf.Sin(Mathf.Clamp01(k * 1.15f) * Mathf.PI);   // rises then falls
                    float h = baseY + 30f + envelope * (90f + 230f * ridge) + RFLayout.Fbm(x / 90f, z / 90f, 3, 9f) * 25f;
                    if (r == 0) h = baseY + 25f;
                    v.Add(new Vector3(x, h, z));
                    float alt = h - baseY;
                    Color c = Color.Lerp(forest, rock, Mathf.Clamp01((alt - 90f) / 110f));
                    c = Color.Lerp(c, snow, Mathf.Clamp01((alt - 255f) / 45f));
                    col.Add(c);
                }
            }
            int row = segments + 1;
            for (int r = 0; r < rings; r++)
            {
                for (int s = 0; s < segments; s++)
                {
                    int a = r * row + s, b = a + 1, c = a + row, d = c + 1;
                    tris.Add(a); tris.Add(c); tris.Add(b);
                    tris.Add(b); tris.Add(c); tris.Add(d);
                }
            }
            var m = new Mesh { name = "FarMountains" };
            if (v.Count > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            m.SetVertices(v);
            m.SetColors(col);
            m.SetTriangles(tris, 0);
            m.RecalculateNormals();
            m.RecalculateBounds();
            return m;
        }

        public static Mesh Quad(string name, float w, float h, float pivotY)
        {
            var m = new Mesh { name = name };
            m.vertices = new[]
            {
                new Vector3(-w * 0.5f, -h * pivotY, 0f), new Vector3(w * 0.5f, -h * pivotY, 0f),
                new Vector3(w * 0.5f, h * (1f - pivotY), 0f), new Vector3(-w * 0.5f, h * (1f - pivotY), 0f)
            };
            m.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            m.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.back };
            m.triangles = new[] { 0, 2, 1, 0, 3, 2 };
            m.RecalculateBounds();
            return m;
        }
    }
}
