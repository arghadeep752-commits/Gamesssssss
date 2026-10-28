using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace ZombieStrike
{
    /// <summary>Accumulates quads into one mesh. Faces are wound clockwise (Unity front faces).</summary>
    public class MeshBuilder
    {
        readonly List<Vector3> verts = new List<Vector3>();
        readonly List<Vector3> normals = new List<Vector3>();
        readonly List<Vector2> uvs = new List<Vector2>();
        readonly List<Color32> colors = new List<Color32>();
        readonly List<int> tris = new List<int>();

        static readonly Vector3[] FaceNormals =
        {
            Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back
        };

        static readonly Vector3[] FaceUps =
        {
            Vector3.up, Vector3.up, Vector3.forward, Vector3.forward, Vector3.up, Vector3.up
        };

        public Color32 Tint = new Color32(255, 255, 255, 255);

        public int VertexCount { get { return verts.Count; } }

        public void AddQuad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 na, Vector3 nb, Vector3 nc, Vector3 nd,
            Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud)
        {
            int i = verts.Count;
            verts.Add(a); verts.Add(b); verts.Add(c); verts.Add(d);
            normals.Add(na); normals.Add(nb); normals.Add(nc); normals.Add(nd);
            uvs.Add(ua); uvs.Add(ub); uvs.Add(uc); uvs.Add(ud);
            colors.Add(Tint); colors.Add(Tint); colors.Add(Tint); colors.Add(Tint);
            tris.Add(i); tris.Add(i + 1); tris.Add(i + 2);
            tris.Add(i); tris.Add(i + 2); tris.Add(i + 3);
        }

        public void AddTri(Vector3 a, Vector3 b, Vector3 c, Vector3 n, Vector2 ua, Vector2 ub, Vector2 uc)
        {
            int i = verts.Count;
            verts.Add(a); verts.Add(b); verts.Add(c);
            normals.Add(n); normals.Add(n); normals.Add(n);
            uvs.Add(ua); uvs.Add(ub); uvs.Add(uc);
            colors.Add(Tint); colors.Add(Tint); colors.Add(Tint);
            tris.Add(i); tris.Add(i + 1); tris.Add(i + 2);
        }

        /// <summary>
        /// Adds a box. uvTile &gt; 0 tiles the texture every uvTile metres; 0 maps 0..1 on each face.
        /// cell &gt; 0 subdivides faces (better vertex lighting on big surfaces). faces is a bit mask (bit i = FaceNormals[i]).
        /// </summary>
        public void AddBox(Vector3 center, Vector3 size, Quaternion rot, float uvTile, float cell = 0f, int faces = 63)
        {
            Vector3 h = size * 0.5f;
            for (int f = 0; f < 6; f++)
            {
                if ((faces & (1 << f)) == 0) continue;
                Vector3 n = FaceNormals[f];
                Vector3 v = FaceUps[f];
                Vector3 u = Vector3.Cross(v, -n);
                float hn = Mathf.Abs(Vector3.Dot(h, n));
                float hu = Mathf.Abs(Vector3.Dot(h, u));
                float hv = Mathf.Abs(Vector3.Dot(h, v));
                Vector3 fc = n * hn;
                int su = 1, sv = 1;
                if (cell > 0f)
                {
                    su = Mathf.Clamp(Mathf.CeilToInt(2f * hu / cell), 1, 64);
                    sv = Mathf.Clamp(Mathf.CeilToInt(2f * hv / cell), 1, 64);
                }
                Vector3 wn = rot * n;
                for (int i = 0; i < su; i++)
                {
                    float u0 = -hu + 2f * hu * i / su;
                    float u1 = -hu + 2f * hu * (i + 1) / su;
                    for (int j = 0; j < sv; j++)
                    {
                        float v0 = -hv + 2f * hv * j / sv;
                        float v1 = -hv + 2f * hv * (j + 1) / sv;
                        Vector3 p0 = fc + u * u0 + v * v0;
                        Vector3 p1 = fc + u * u0 + v * v1;
                        Vector3 p2 = fc + u * u1 + v * v1;
                        Vector3 p3 = fc + u * u1 + v * v0;
                        Vector2 t0, t1, t2, t3;
                        if (uvTile > 0f)
                        {
                            t0 = new Vector2((u0 + hu) / uvTile, (v0 + hv) / uvTile);
                            t1 = new Vector2((u0 + hu) / uvTile, (v1 + hv) / uvTile);
                            t2 = new Vector2((u1 + hu) / uvTile, (v1 + hv) / uvTile);
                            t3 = new Vector2((u1 + hu) / uvTile, (v0 + hv) / uvTile);
                        }
                        else
                        {
                            t0 = new Vector2((float)i / su, (float)j / sv);
                            t1 = new Vector2((float)i / su, (float)(j + 1) / sv);
                            t2 = new Vector2((float)(i + 1) / su, (float)(j + 1) / sv);
                            t3 = new Vector2((float)(i + 1) / su, (float)j / sv);
                        }
                        AddQuad(center + rot * p0, center + rot * p1, center + rot * p2, center + rot * p3,
                            wn, wn, wn, wn, t0, t1, t2, t3);
                    }
                }
            }
        }

        /// <summary>Upright cylinder standing on baseCenter (then rotated by rot around baseCenter).</summary>
        public void AddCylinder(Vector3 baseCenter, float radius, float height, int segments, Quaternion rot, float uvTile, bool caps = true)
        {
            float circumference = Mathf.PI * 2f * radius;
            for (int i = 0; i < segments; i++)
            {
                float a0 = i * Mathf.PI * 2f / segments;
                float a1 = (i + 1) * Mathf.PI * 2f / segments;
                Vector3 d0 = new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0));
                Vector3 d1 = new Vector3(Mathf.Cos(a1), 0f, Mathf.Sin(a1));
                Vector3 b0 = d0 * radius, b1 = d1 * radius;
                Vector3 t0 = b0 + Vector3.up * height, t1 = b1 + Vector3.up * height;
                float u0 = uvTile > 0f ? circumference * i / segments / uvTile : (float)i / segments;
                float u1 = uvTile > 0f ? circumference * (i + 1) / segments / uvTile : (float)(i + 1) / segments;
                float vt = uvTile > 0f ? height / uvTile : 1f;
                AddQuad(baseCenter + rot * b0, baseCenter + rot * t0, baseCenter + rot * t1, baseCenter + rot * b1,
                    rot * d0, rot * d0, rot * d1, rot * d1,
                    new Vector2(u0, 0f), new Vector2(u0, vt), new Vector2(u1, vt), new Vector2(u1, 0f));
                if (caps)
                {
                    Vector3 up = rot * Vector3.up;
                    Vector3 top = baseCenter + rot * (Vector3.up * height);
                    AddTri(top, baseCenter + rot * t1, baseCenter + rot * t0, up,
                        new Vector2(0.5f, 0.5f), new Vector2(0.5f + d1.x * 0.5f, 0.5f + d1.z * 0.5f), new Vector2(0.5f + d0.x * 0.5f, 0.5f + d0.z * 0.5f));
                    AddTri(baseCenter, baseCenter + rot * b0, baseCenter + rot * b1, -up,
                        new Vector2(0.5f, 0.5f), new Vector2(0.5f + d0.x * 0.5f, 0.5f + d0.z * 0.5f), new Vector2(0.5f + d1.x * 0.5f, 0.5f + d1.z * 0.5f));
                }
            }
        }

        public Mesh Build(string name)
        {
            var m = new Mesh { name = name };
            if (verts.Count > 65000) m.indexFormat = IndexFormat.UInt32;
            m.SetVertices(verts);
            m.SetNormals(normals);
            m.SetUVs(0, uvs);
            m.SetColors(colors);
            m.SetTriangles(tris, 0);
            m.RecalculateBounds();
            return m;
        }
    }

    public static class MeshUtil
    {
        public static Mesh UnitCube()
        {
            var mb = new MeshBuilder();
            mb.AddBox(Vector3.zero, Vector3.one, Quaternion.identity, 0f);
            return mb.Build("UnitCube");
        }

        /// <summary>1x1 quad in the XY plane, visible from -Z (faces a camera looking along +Z).</summary>
        public static Mesh UnitQuad(Color32 tint)
        {
            var mb = new MeshBuilder { Tint = tint };
            Vector3 n = Vector3.back;
            mb.AddQuad(new Vector3(-0.5f, -0.5f, 0f), new Vector3(-0.5f, 0.5f, 0f), new Vector3(0.5f, 0.5f, 0f), new Vector3(0.5f, -0.5f, 0f),
                n, n, n, n, new Vector2(0f, 0f), new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(1f, 0f));
            return mb.Build("Quad");
        }

        public static Mesh Cylinder(float radius, float height, int segments)
        {
            var mb = new MeshBuilder();
            mb.AddCylinder(Vector3.zero, radius, height, segments, Quaternion.identity, 0f);
            return mb.Build("Cylinder");
        }
    }

    /// <summary>
    /// Merges static level geometry into a few meshes per material and per area chunk,
    /// so the whole level costs only a handful of draw calls.
    /// </summary>
    public class StaticBatch
    {
        readonly float chunk;
        readonly Dictionary<string, MeshBuilder> current = new Dictionary<string, MeshBuilder>();
        readonly List<KeyValuePair<Material, MeshBuilder>> all = new List<KeyValuePair<Material, MeshBuilder>>();

        public StaticBatch(float chunkSize)
        {
            chunk = chunkSize;
        }

        public MeshBuilder For(Material mat, Vector3 position)
        {
            int cx = Mathf.FloorToInt(position.x / chunk);
            int cz = Mathf.FloorToInt(position.z / chunk);
            string key = mat.GetInstanceID() + ":" + cx + ":" + cz;
            MeshBuilder mb;
            if (!current.TryGetValue(key, out mb) || mb.VertexCount > 60000)
            {
                mb = new MeshBuilder();
                current[key] = mb;
                all.Add(new KeyValuePair<Material, MeshBuilder>(mat, mb));
            }
            return mb;
        }

        public void Finish(Transform parent)
        {
            int index = 0;
            foreach (KeyValuePair<Material, MeshBuilder> kv in all)
            {
                if (kv.Value.VertexCount == 0) continue;
                string name = "Static " + kv.Key.name + " " + index++;
                var go = new GameObject(name);
                go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = kv.Value.Build(name);
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterial = kv.Key;
                Art.Plain(r);
            }
            current.Clear();
            all.Clear();
        }
    }
}
