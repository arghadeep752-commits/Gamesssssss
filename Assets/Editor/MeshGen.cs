using System.Collections.Generic;
using UnityEngine;

namespace GridProto.EditorTools
{
    /// <summary>Collects quads and turns them into a mesh. Winding is fixed up automatically from the normal.</summary>
    public class MeshBuilder
    {
        readonly List<Vector3> vertices = new List<Vector3>();
        readonly List<Vector3> normals = new List<Vector3>();
        readonly List<Vector2> uvs = new List<Vector2>();
        readonly List<Color> colors = new List<Color>();
        readonly List<int> triangles = new List<int>();

        public int VertexCount { get { return vertices.Count; } }

        /// <summary>Adds a quad; a, b, c, d go around its edge in order.</summary>
        public void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 normal,
                         Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud, Color color)
        {
            int i = vertices.Count;
            vertices.Add(a); vertices.Add(b); vertices.Add(c); vertices.Add(d);
            uvs.Add(ua); uvs.Add(ub); uvs.Add(uc); uvs.Add(ud);
            for (int k = 0; k < 4; k++)
            {
                normals.Add(normal);
                colors.Add(color);
            }
            // Unity draws a triangle's front side when Cross(b - a, c - a) points at the viewer
            bool front = Vector3.Dot(Vector3.Cross(b - a, c - a), normal) >= 0f;
            if (front)
            {
                triangles.Add(i); triangles.Add(i + 1); triangles.Add(i + 2);
                triangles.Add(i); triangles.Add(i + 2); triangles.Add(i + 3);
            }
            else
            {
                triangles.Add(i); triangles.Add(i + 2); triangles.Add(i + 1);
                triangles.Add(i); triangles.Add(i + 3); triangles.Add(i + 2);
            }
        }

        public Mesh ToMesh(string name, bool withTangents)
        {
            var mesh = new Mesh();
            mesh.name = name;
            if (vertices.Count > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            mesh.SetVertices(vertices);
            mesh.SetNormals(normals);
            mesh.SetUVs(0, uvs);
            mesh.SetColors(colors);
            mesh.SetTriangles(triangles, 0);
            if (withTangents) mesh.RecalculateTangents();
            mesh.RecalculateBounds();
            return mesh;
        }
    }

    public static class MeshGen
    {
        /// <summary>
        /// Box centred on its pivot. UVs are in metres / tile; pass the box's world centre as uvOrigin
        /// to line its grid up with the floor grid (use Vector3.zero for rotated or moving boxes).
        /// </summary>
        public static Mesh Box(string name, Vector3 size, Vector3 uvOrigin, float tile)
        {
            var mb = new MeshBuilder();
            Vector3 h = size * 0.5f;
            Color white = Color.white;
            for (int s = -1; s <= 1; s += 2)
            {
                float x = h.x * s;
                Vector3 a = new Vector3(x, -h.y, -h.z), b = new Vector3(x, h.y, -h.z), c = new Vector3(x, h.y, h.z), d = new Vector3(x, -h.y, h.z);
                mb.Quad(a, b, c, d, new Vector3(s, 0f, 0f), ZY(a, uvOrigin, tile), ZY(b, uvOrigin, tile), ZY(c, uvOrigin, tile), ZY(d, uvOrigin, tile), white);

                float y = h.y * s;
                a = new Vector3(-h.x, y, -h.z); b = new Vector3(-h.x, y, h.z); c = new Vector3(h.x, y, h.z); d = new Vector3(h.x, y, -h.z);
                mb.Quad(a, b, c, d, new Vector3(0f, s, 0f), XZ(a, uvOrigin, tile), XZ(b, uvOrigin, tile), XZ(c, uvOrigin, tile), XZ(d, uvOrigin, tile), white);

                float z = h.z * s;
                a = new Vector3(-h.x, -h.y, z); b = new Vector3(-h.x, h.y, z); c = new Vector3(h.x, h.y, z); d = new Vector3(h.x, -h.y, z);
                mb.Quad(a, b, c, d, new Vector3(0f, 0f, s), XY(a, uvOrigin, tile), XY(b, uvOrigin, tile), XY(c, uvOrigin, tile), XY(d, uvOrigin, tile), white);
            }
            return mb.ToMesh(name, true);
        }

        static Vector2 ZY(Vector3 p, Vector3 o, float t) { return new Vector2((p.z + o.z) / t, (p.y + o.y) / t); }
        static Vector2 XZ(Vector3 p, Vector3 o, float t) { return new Vector2((p.x + o.x) / t, (p.z + o.z) / t); }
        static Vector2 XY(Vector3 p, Vector3 o, float t) { return new Vector2((p.x + o.x) / t, (p.y + o.y) / t); }

        /// <summary>Flat square floor made of cells (keeps triangles a sensible size for mobile GPUs).</summary>
        public static Mesh Ground(string name, float size, int cells, float tile)
        {
            var mb = new MeshBuilder();
            float step = size / cells, half = size * 0.5f;
            for (int j = 0; j < cells; j++)
            {
                for (int i = 0; i < cells; i++)
                {
                    float x0 = -half + i * step, x1 = x0 + step;
                    float z0 = -half + j * step, z1 = z0 + step;
                    mb.Quad(new Vector3(x0, 0f, z0), new Vector3(x0, 0f, z1), new Vector3(x1, 0f, z1), new Vector3(x1, 0f, z0), Vector3.up,
                            new Vector2(x0 / tile, z0 / tile), new Vector2(x0 / tile, z1 / tile), new Vector2(x1 / tile, z1 / tile), new Vector2(x1 / tile, z0 / tile),
                            Color.white);
                }
            }
            return mb.ToMesh(name, true);
        }

        /// <summary>
        /// Contact shadow ring around a halfX x halfZ footprint (9-slice: the corners fade radially,
        /// the edges linearly). The centre is skipped because the object itself covers it.
        /// </summary>
        public static void AddContactShadow(MeshBuilder mb, Vector3 center, float halfX, float halfZ, float rotY, float margin, float strength)
        {
            float[] xs = { -halfX - margin, -halfX, halfX, halfX + margin };
            float[] zs = { -halfZ - margin, -halfZ, halfZ, halfZ + margin };
            float[] us = { 0f, 0.5f, 0.5f, 1f };
            Quaternion q = Quaternion.Euler(0f, rotY, 0f);
            Color color = new Color(1f, 1f, 1f, strength);
            for (int j = 0; j < 3; j++)
            {
                for (int i = 0; i < 3; i++)
                {
                    if (i == 1 && j == 1) continue;
                    Vector3 a = center + q * new Vector3(xs[i], 0f, zs[j]);
                    Vector3 b = center + q * new Vector3(xs[i], 0f, zs[j + 1]);
                    Vector3 c = center + q * new Vector3(xs[i + 1], 0f, zs[j + 1]);
                    Vector3 d = center + q * new Vector3(xs[i + 1], 0f, zs[j]);
                    mb.Quad(a, b, c, d, Vector3.up,
                            new Vector2(us[i], us[j]), new Vector2(us[i], us[j + 1]), new Vector2(us[i + 1], us[j + 1]), new Vector2(us[i + 1], us[j]),
                            color);
                }
            }
        }

        /// <summary>Contact shadow strip along a wall: dark at the wall line, fading out `margin` metres towards `inward`.</summary>
        public static void AddContactStrip(MeshBuilder mb, Vector3 from, Vector3 to, Vector3 inward, float margin, float strength)
        {
            Vector3 off = inward.normalized * margin;
            Color color = new Color(1f, 1f, 1f, strength);
            Vector2 dark = new Vector2(0.5f, 0.5f), clear = new Vector2(0.5f, 0f);
            mb.Quad(from, to, to + off, from + off, Vector3.up, dark, dark, clear, clear, color);
        }
    }
}
