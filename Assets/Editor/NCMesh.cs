using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace NightClass.EditorTools
{
    /// <summary>Builds meshes from boxes, cylinders, spheres and tori with metre-scaled UVs.</summary>
    public class MeshBuilder
    {
        public readonly List<Vector3> v = new List<Vector3>();
        public readonly List<Vector3> n = new List<Vector3>();
        public readonly List<Vector2> uv = new List<Vector2>();
        public readonly List<Color> col = new List<Color>();
        public readonly List<int> t = new List<int>();
        public float uvScale = 1f;      // texture repeats per metre
        public bool HasGeometry { get { return t.Count > 0; } }

        public Matrix4x4 m = Matrix4x4.identity;

        void Vert(Vector3 p, Vector3 normal, Vector2 tex, Color c)
        {
            v.Add(m.MultiplyPoint3x4(p));
            n.Add(m.MultiplyVector(normal).normalized);
            uv.Add(tex);
            col.Add(c);
        }

        public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 normal, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud, Color color)
        {
            int i = v.Count;
            Vert(a, normal, ua, color); Vert(b, normal, ub, color); Vert(c, normal, uc, color); Vert(d, normal, ud, color);
            // keep the winding facing the normal after mirroring transforms
            Vector3 wn = Vector3.Cross(v[i + 1] - v[i], v[i + 2] - v[i]);
            if (Vector3.Dot(wn, n[i]) >= 0f) { t.Add(i); t.Add(i + 1); t.Add(i + 2); t.Add(i); t.Add(i + 2); t.Add(i + 3); }
            else { t.Add(i); t.Add(i + 2); t.Add(i + 1); t.Add(i); t.Add(i + 3); t.Add(i + 2); }
        }

        /// <summary>Axis-aligned (in local space) box. World-scaled UVs so textures tile evenly.</summary>
        public void Box(Vector3 center, Vector3 size, Color? color = null, bool skipBottom = false, bool skipTop = false)
        {
            Color c = color ?? Color.white;
            Vector3 h = size * 0.5f;
            float s = uvScale;
            Vector3 p = center;
            // world-ish UV offsets so neighbouring boxes line up
            Vector3 o = m.MultiplyPoint3x4(center);
            // +X / -X
            Quad(p + new Vector3(h.x, -h.y, -h.z), p + new Vector3(h.x, -h.y, h.z), p + new Vector3(h.x, h.y, h.z), p + new Vector3(h.x, h.y, -h.z), Vector3.right,
                 new Vector2((o.z - h.z) * s, (o.y - h.y) * s), new Vector2((o.z + h.z) * s, (o.y - h.y) * s), new Vector2((o.z + h.z) * s, (o.y + h.y) * s), new Vector2((o.z - h.z) * s, (o.y + h.y) * s), c);
            Quad(p + new Vector3(-h.x, -h.y, h.z), p + new Vector3(-h.x, -h.y, -h.z), p + new Vector3(-h.x, h.y, -h.z), p + new Vector3(-h.x, h.y, h.z), Vector3.left,
                 new Vector2(-(o.z + h.z) * s, (o.y - h.y) * s), new Vector2(-(o.z - h.z) * s, (o.y - h.y) * s), new Vector2(-(o.z - h.z) * s, (o.y + h.y) * s), new Vector2(-(o.z + h.z) * s, (o.y + h.y) * s), c);
            // +Z / -Z
            Quad(p + new Vector3(h.x, -h.y, h.z), p + new Vector3(-h.x, -h.y, h.z), p + new Vector3(-h.x, h.y, h.z), p + new Vector3(h.x, h.y, h.z), Vector3.forward,
                 new Vector2(-(o.x + h.x) * s, (o.y - h.y) * s), new Vector2(-(o.x - h.x) * s, (o.y - h.y) * s), new Vector2(-(o.x - h.x) * s, (o.y + h.y) * s), new Vector2(-(o.x + h.x) * s, (o.y + h.y) * s), c);
            Quad(p + new Vector3(-h.x, -h.y, -h.z), p + new Vector3(h.x, -h.y, -h.z), p + new Vector3(h.x, h.y, -h.z), p + new Vector3(-h.x, h.y, -h.z), Vector3.back,
                 new Vector2((o.x - h.x) * s, (o.y - h.y) * s), new Vector2((o.x + h.x) * s, (o.y - h.y) * s), new Vector2((o.x + h.x) * s, (o.y + h.y) * s), new Vector2((o.x - h.x) * s, (o.y + h.y) * s), c);
            // +Y / -Y
            if (!skipTop)
                Quad(p + new Vector3(-h.x, h.y, -h.z), p + new Vector3(h.x, h.y, -h.z), p + new Vector3(h.x, h.y, h.z), p + new Vector3(-h.x, h.y, h.z), Vector3.up,
                     new Vector2((o.x - h.x) * s, (o.z - h.z) * s), new Vector2((o.x + h.x) * s, (o.z - h.z) * s), new Vector2((o.x + h.x) * s, (o.z + h.z) * s), new Vector2((o.x - h.x) * s, (o.z + h.z) * s), c);
            if (!skipBottom)
                Quad(p + new Vector3(-h.x, -h.y, h.z), p + new Vector3(h.x, -h.y, h.z), p + new Vector3(h.x, -h.y, -h.z), p + new Vector3(-h.x, -h.y, -h.z), Vector3.down,
                     new Vector2((o.x - h.x) * s, (o.z + h.z) * s), new Vector2((o.x + h.x) * s, (o.z + h.z) * s), new Vector2((o.x + h.x) * s, (o.z - h.z) * s), new Vector2((o.x - h.x) * s, (o.z - h.z) * s), c);
        }

        /// <summary>A box with the full texture mapped once on its front (-Z) face (posters, boards, notes).</summary>
        public void Panel(Vector3 center, Vector3 size, Color? color = null)
        {
            Color c = color ?? Color.white;
            Vector3 h = size * 0.5f;
            Vector3 p = center;
            Quad(p + new Vector3(-h.x, -h.y, -h.z), p + new Vector3(h.x, -h.y, -h.z), p + new Vector3(h.x, h.y, -h.z), p + new Vector3(-h.x, h.y, -h.z), Vector3.back,
                 new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1), c);
        }

        public void Cylinder(Vector3 a, Vector3 b, float ra, float rb, int seg = 12, bool caps = true, Color? color = null)
        {
            Color c = color ?? Color.white;
            Vector3 axis = b - a;
            float len = axis.magnitude;
            if (len < 1e-5f) return;
            Vector3 dir = axis / len;
            Vector3 side = Vector3.Cross(dir, Mathf.Abs(dir.y) < 0.95f ? Vector3.up : Vector3.right).normalized;
            Vector3 up = Vector3.Cross(side, dir);
            float circ = Mathf.PI * 2f * Mathf.Max(ra, rb);
            for (int i = 0; i < seg; i++)
            {
                float a0 = i / (float)seg * Mathf.PI * 2f, a1 = (i + 1) / (float)seg * Mathf.PI * 2f;
                Vector3 d0 = side * Mathf.Cos(a0) + up * Mathf.Sin(a0);
                Vector3 d1 = side * Mathf.Cos(a1) + up * Mathf.Sin(a1);
                float u0 = i / (float)seg * circ * uvScale, u1 = (i + 1) / (float)seg * circ * uvScale;
                int s0 = v.Count;
                Vert(a + d0 * ra, d0, new Vector2(u0, 0), c);
                Vert(a + d1 * ra, d1, new Vector2(u1, 0), c);
                Vert(b + d1 * rb, d1, new Vector2(u1, len * uvScale), c);
                Vert(b + d0 * rb, d0, new Vector2(u0, len * uvScale), c);
                Vector3 wn = Vector3.Cross(v[s0 + 1] - v[s0], v[s0 + 2] - v[s0]);
                if (Vector3.Dot(wn, n[s0] + n[s0 + 1]) >= 0f) { t.Add(s0); t.Add(s0 + 1); t.Add(s0 + 2); t.Add(s0); t.Add(s0 + 2); t.Add(s0 + 3); }
                else { t.Add(s0); t.Add(s0 + 2); t.Add(s0 + 1); t.Add(s0); t.Add(s0 + 3); t.Add(s0 + 2); }
                if (caps)
                {
                    if (ra > 1e-4f) Tri(a, a + d1 * ra, a + d0 * ra, -dir, c);
                    if (rb > 1e-4f) Tri(b, b + d0 * rb, b + d1 * rb, dir, c);
                }
            }
        }

        void Tri(Vector3 a, Vector3 b, Vector3 cc, Vector3 normal, Color color)
        {
            int i = v.Count;
            Vert(a, normal, new Vector2(0.5f, 0.5f), color);
            Vert(b, normal, new Vector2(b.x, b.z) * uvScale, color);
            Vert(cc, normal, new Vector2(cc.x, cc.z) * uvScale, color);
            Vector3 wn = Vector3.Cross(v[i + 1] - v[i], v[i + 2] - v[i]);
            if (Vector3.Dot(wn, n[i]) >= 0f) { t.Add(i); t.Add(i + 1); t.Add(i + 2); }
            else { t.Add(i); t.Add(i + 2); t.Add(i + 1); }
        }

        /// <summary>Ellipsoid (UV sphere). Optional per-vertex displacement for faces / rocks.</summary>
        public void Sphere(Vector3 center, Vector3 radii, int seg = 14, int rings = 10, System.Func<Vector3, float> displace = null, Color? color = null, bool frontUV = false)
        {
            Color c = color ?? Color.white;
            int start = v.Count;
            for (int r = 0; r <= rings; r++)
            {
                float lat = Mathf.PI * r / rings - Mathf.PI * 0.5f;
                for (int s = 0; s <= seg; s++)
                {
                    float lon = Mathf.PI * 2f * s / seg;
                    Vector3 d = new Vector3(Mathf.Cos(lat) * Mathf.Sin(lon), Mathf.Sin(lat), Mathf.Cos(lat) * Mathf.Cos(lon));
                    float k = displace != null ? displace(d) : 1f;
                    Vector3 p = center + Vector3.Scale(d, radii) * k;
                    Vector3 nn = Vector3.Scale(d, new Vector3(1f / radii.x, 1f / radii.y, 1f / radii.z)).normalized;
                    Vector2 tex = frontUV ? new Vector2(0.5f + d.x * 0.5f, 0.5f + d.y * 0.5f) : new Vector2(s / (float)seg, r / (float)rings);
                    Vert(p, nn, tex, c);
                }
            }
            int row = seg + 1;
            for (int r = 0; r < rings; r++)
                for (int s = 0; s < seg; s++)
                {
                    int a = start + r * row + s, b = a + row;
                    t.Add(a); t.Add(a + 1); t.Add(b);
                    t.Add(a + 1); t.Add(b + 1); t.Add(b);
                }
        }

        public void Torus(Vector3 center, Vector3 axis, float R, float r, int seg = 16, int tube = 6, Color? color = null)
        {
            Color c = color ?? Color.white;
            axis = axis.normalized;
            Vector3 side = Vector3.Cross(axis, Mathf.Abs(axis.y) < 0.95f ? Vector3.up : Vector3.right).normalized;
            Vector3 up = Vector3.Cross(side, axis);
            int start = v.Count;
            for (int i = 0; i <= seg; i++)
            {
                float a = Mathf.PI * 2f * i / seg;
                Vector3 ring = side * Mathf.Cos(a) + up * Mathf.Sin(a);
                for (int j = 0; j <= tube; j++)
                {
                    float b = Mathf.PI * 2f * j / tube;
                    Vector3 nn = ring * Mathf.Cos(b) + axis * Mathf.Sin(b);
                    Vert(center + ring * R + nn * r, nn, new Vector2(i / (float)seg, j / (float)tube), c);
                }
            }
            int row = tube + 1;
            for (int i = 0; i < seg; i++)
                for (int j = 0; j < tube; j++)
                {
                    int a = start + i * row + j, b = a + row;
                    t.Add(a); t.Add(a + 1); t.Add(b);
                    t.Add(a + 1); t.Add(b + 1); t.Add(b);
                }
        }

        public Mesh ToMesh(string name)
        {
            var mesh = new Mesh { name = name };
            if (v.Count > 65000) mesh.indexFormat = IndexFormat.UInt32;
            mesh.SetVertices(v);
            mesh.SetNormals(n);
            mesh.SetUVs(0, uv);
            mesh.SetColors(col);
            mesh.SetTriangles(t, 0);
            mesh.RecalculateBounds();
            mesh.RecalculateTangents();
            return mesh;
        }
    }
}
