using System.Collections.Generic;
using UnityEngine;

namespace RealFPS.EditorTools
{
    /// <summary>
    /// Procedural fir/spruce trees: a tapered bark trunk and whorls of branch cards
    /// textured with photo-scanned fir sprays (Poly Haven "fir_tree_01" twig atlas).
    /// Card normals point away from the trunk so the crown shades like a volume.
    /// Submesh 0 = bark, submesh 1 = needles.
    /// </summary>
    public static class RFTrees
    {
        public class TreeMesh
        {
            public Mesh lod0, lod1, lod2;
            public float height, trunkRadius;
        }

        class Builder
        {
            public readonly List<Vector3> v = new List<Vector3>();
            public readonly List<Vector3> n = new List<Vector3>();
            public readonly List<Vector2> uv = new List<Vector2>();
            public readonly List<Color> c = new List<Color>();
            public readonly List<int> bark = new List<int>();
            public readonly List<int> leaves = new List<int>();

            public Mesh ToMesh(string name)
            {
                var m = new Mesh { name = name };
                if (v.Count > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                m.SetVertices(v);
                m.SetNormals(n);
                m.SetUVs(0, uv);
                m.SetColors(c);
                m.subMeshCount = 2;
                m.SetTriangles(bark, 0);
                m.SetTriangles(leaves, 1);
                m.RecalculateBounds();
                m.RecalculateTangents();
                return m;
            }
        }

        static float Rnd(System.Random r, float a, float b) { return a + (float)r.NextDouble() * (b - a); }

        public static TreeMesh Build(int seed, float height, float[] twigRects)
        {
            var t = new TreeMesh { height = height };
            t.trunkRadius = 0.16f + height * 0.012f;
            t.lod0 = BuildLod(seed, height, t.trunkRadius, twigRects, 0);
            t.lod1 = BuildLod(seed, height, t.trunkRadius, twigRects, 1);
            t.lod2 = BuildFar(seed, height);
            return t;
        }

        static Vector3 Bend(float y, float height, float seed)
        {
            float k = y / height;
            return new Vector3(Mathf.Sin(seed * 1.7f + k * 2.1f), 0f, Mathf.Cos(seed * 2.3f + k * 1.7f)) * (0.18f * k * k);
        }

        static float TrunkR(float y, float height, float r0)
        {
            float k = Mathf.Clamp01(y / height);
            float r = r0 * Mathf.Pow(1f - k, 0.85f) + 0.025f;
            r *= 1f + 0.55f * Mathf.Exp(-y / 0.35f); // root flare
            return r;
        }

        static Mesh BuildLod(int seed, float height, float r0, float[] rects, int lod)
        {
            var r = new System.Random(seed);
            var b = new Builder();
            float seedF = seed * 0.37f;

            // ---------------------------------------------------------------- trunk
            int sides = lod == 0 ? 9 : 5;
            int rings = lod == 0 ? Mathf.CeilToInt(height / 1.4f) : 3;
            float top = height * 0.92f;
            float circ = 2f * Mathf.PI * r0;
            float vScale = 2f / circ; // two texture repeats around the trunk, square texels
            int baseIndex = b.v.Count;
            for (int i = 0; i <= rings; i++)
            {
                float y = top * i / rings;
                if (i == 0) y = -0.4f; // a little below ground
                float rad = TrunkR(Mathf.Max(0f, y), height, r0);
                Vector3 off = Bend(y, height, seedF);
                for (int s = 0; s <= sides; s++)
                {
                    float a = s / (float)sides * Mathf.PI * 2f;
                    var dir = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                    b.v.Add(off + dir * rad + Vector3.up * y);
                    b.n.Add(dir);
                    b.uv.Add(new Vector2(s / (float)sides * 2f, y * vScale));
                    b.c.Add(new Color(Mathf.Lerp(0.55f, 1f, Mathf.Clamp01(y / 2f)), 0f, 0f, 1f));
                }
            }
            for (int i = 0; i < rings; i++)
            {
                for (int s = 0; s < sides; s++)
                {
                    int a0 = baseIndex + i * (sides + 1) + s;
                    int a1 = a0 + sides + 1;
                    b.bark.Add(a0); b.bark.Add(a1); b.bark.Add(a0 + 1);
                    b.bark.Add(a0 + 1); b.bark.Add(a1); b.bark.Add(a1 + 1);
                }
            }

            // ---------------------------------------------------------------- branches
            float crownStart = height * Rnd(r, 0.1f, 0.2f);
            float crownR = height * Rnd(0.21f, 0.26f, r);
            float y0 = crownStart;
            float spacing = lod == 0 ? 0.52f : 1.5f;
            float whorlRot = Rnd(r, 0f, 6.28f);
            while (y0 < height - 0.9f)
            {
                float tt = (y0 - crownStart) / (height - crownStart);
                int count = lod == 0 ? Mathf.RoundToInt(Mathf.Lerp(7f, 4f, tt)) : (tt > 0.7f ? 3 : 4);
                for (int k = 0; k < count; k++)
                {
                    float az = whorlRot + k * Mathf.PI * 2f / count + Rnd(r, -0.3f, 0.3f);
                    float len = crownR * Mathf.Pow(1f - tt, 0.85f) * Rnd(r, 0.85f, 1.15f) + 0.35f;
                    if (lod == 1) len *= 1.15f;
                    float pitch = Mathf.Lerp(-24f, 10f, tt) + Rnd(r, -7f, 7f);
                    float droop = Mathf.Lerp(-16f, 6f, tt) + Rnd(r, -6f, 6f);
                    int cell = tt > 0.82f ? 2 + r.Next(2) : r.Next(2);
                    if (r.NextDouble() < 0.3) cell = r.Next(4);
                    float y = y0 + Rnd(r, -0.12f, 0.12f);
                    Vector3 origin = Bend(y, height, seedF) + Vector3.up * y;
                    float width = len * (lod == 0 ? Rnd(r, 0.85f, 1.05f) : 1.35f);
                    float roll = Rnd(r, -22f, 22f);
                    float ao = Mathf.Lerp(0.45f, 1f, Mathf.Pow(tt, 0.6f));
                    AddCard(b, origin, az, pitch, lod == 0 ? droop : 0f, roll, len, width, TrunkR(y, height, r0) * 0.6f, rects, cell, ao, Rnd(r, 0f, 1f), height, lod == 0);
                    // a second, steeper card fills the crown when seen from the side
                    if (lod == 0 && tt < 0.85f && r.NextDouble() < 0.75)
                        AddCard(b, origin, az + Rnd(r, -0.25f, 0.25f), pitch + 10f, droop, roll + Rnd(r, 50f, 75f) * (r.NextDouble() < 0.5 ? -1f : 1f),
                                len * 0.85f, width * 0.7f, TrunkR(y, height, r0) * 0.6f, rects, r.Next(4), ao * 0.9f, Rnd(r, 0f, 1f), height, true);
                }
                whorlRot += Rnd(r, 0.5f, 1.3f);
                y0 += spacing * Rnd(r, 0.85f, 1.2f);
            }
            // the leader at the top
            Vector3 tip = Bend(height - 1.2f, height, seedF) + Vector3.up * (height - 1.5f);
            for (int k = 0; k < 2; k++)
            {
                float az = k * Mathf.PI * 0.5f + whorlRot;
                AddUpright(b, tip, az, 1.9f, 1.1f, rects, 2 + k, height);
            }
            return b.ToMesh("Fir_" + seed + "_LOD" + lod);
        }

        /// <summary>Far LOD: three stacked irregular cones (dark needle green, vertex coloured).</summary>
        static Mesh BuildFar(int seed, float height)
        {
            var r = new System.Random(seed + 991);
            var v = new List<Vector3>();
            var n = new List<Vector3>();
            var c = new List<Color>();
            var t = new List<int>();
            float crownR = height * 0.24f;
            float[] baseY = { height * 0.14f, height * 0.38f, height * 0.6f };
            float[] radius = { crownR, crownR * 0.74f, crownR * 0.48f };
            float[] topY = { height * 0.62f, height * 0.84f, height * 1.0f };
            int sides = 7;
            for (int tier = 0; tier < 3; tier++)
            {
                int apex = v.Count;
                v.Add(new Vector3(0f, topY[tier], 0f));
                n.Add(Vector3.up);
                c.Add(new Color(0.075f, 0.1f, 0.045f, 1f));
                for (int s = 0; s < sides; s++)
                {
                    float a = s / (float)sides * Mathf.PI * 2f + tier * 0.4f;
                    float rr = radius[tier] * Rnd(r, 0.85f, 1.15f);
                    var d = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                    v.Add(new Vector3(d.x * rr, baseY[tier] - rr * 0.25f, d.z * rr));
                    n.Add((d + Vector3.up * 0.6f).normalized);
                    c.Add(new Color(0.045f, 0.065f, 0.03f, 1f));
                }
                for (int s = 0; s < sides; s++)
                {
                    t.Add(apex); t.Add(apex + 1 + (s + 1) % sides); t.Add(apex + 1 + s);
                }
            }
            var m = new Mesh { name = "Fir_" + seed + "_LOD2" };
            m.SetVertices(v);
            m.SetNormals(n);
            m.SetColors(c);
            m.SetTriangles(t, 0);
            m.RecalculateBounds();
            return m;
        }

        static void Rect(float[] rects, int cell, out float u0, out float v0, out float u1, out float v1)
        {
            cell = Mathf.Clamp(cell, 0, rects.Length / 4 - 1);
            u0 = rects[cell * 4]; v0 = rects[cell * 4 + 1]; u1 = rects[cell * 4 + 2]; v1 = rects[cell * 4 + 3];
        }

        static Vector3 CrownNormal(Vector3 p, Vector3 axisPoint)
        {
            Vector3 d = p - axisPoint;
            d.y *= 0.6f;
            if (d.sqrMagnitude < 1e-4f) d = Vector3.up;
            return (d.normalized + Vector3.up * 0.35f).normalized;
        }

        /// <summary>A branch card bent in two segments, from the trunk outwards.</summary>
        static void AddCard(Builder b, Vector3 origin, float az, float pitch, float droop, float roll, float len, float width,
                            float startR, float[] rects, int cell, float ao, float phase, float height, bool bent)
        {
            Rect(rects, cell, out float u0, out float v0, out float u1, out float v1);
            var dirH = new Vector3(Mathf.Cos(az), 0f, Mathf.Sin(az));
            Vector3 d1 = (Quaternion.AngleAxis(pitch, Vector3.Cross(dirH, Vector3.up)) * dirH).normalized;
            Vector3 d2 = (Quaternion.AngleAxis(pitch + droop, Vector3.Cross(dirH, Vector3.up)) * dirH).normalized;
            Vector3 side = Vector3.Cross(Vector3.up, dirH).normalized;
            side = Quaternion.AngleAxis(roll, d1) * side;
            Vector3 p0 = origin + dirH * startR;
            Vector3 p1 = p0 + d1 * (len * 0.5f);
            Vector3 p2 = p1 + d2 * (len * 0.5f);
            Vector3 axis = new Vector3(origin.x, origin.y - 0.6f, origin.z);
            float hw = width * 0.5f;
            int i0 = b.v.Count;
            Vector3[] pts = bent ? new[] { p0, p1, p2 } : new[] { p0, p0 + d1 * len };
            float[] vv = bent ? new[] { v0, (v0 + v1) * 0.5f, v1 } : new[] { v0, v1 };
            int rows = pts.Length;
            for (int k = 0; k < rows; k++)
            {
                float along = k / (float)(rows - 1);
                float w = hw * (k == 0 ? 0.55f : 1f);
                Vector3 a = pts[k] - side * w;
                Vector3 c = pts[k] + side * w;
                b.v.Add(a); b.v.Add(c);
                b.uv.Add(new Vector2(u0, vv[k])); b.uv.Add(new Vector2(u1, vv[k]));
                b.n.Add(CrownNormal(a, axis)); b.n.Add(CrownNormal(c, axis));
                float occl = Mathf.Lerp(ao * 0.55f, ao, along);
                var col = new Color(occl, along * Mathf.Lerp(0.5f, 1f, origin.y / height), phase, 1f);
                b.c.Add(col); b.c.Add(col);
            }
            for (int k = 0; k < rows - 1; k++)
            {
                int a = i0 + k * 2;
                b.leaves.Add(a); b.leaves.Add(a + 2); b.leaves.Add(a + 1);
                b.leaves.Add(a + 1); b.leaves.Add(a + 2); b.leaves.Add(a + 3);
            }
        }

        static void AddUpright(Builder b, Vector3 basePos, float az, float h, float w, float[] rects, int cell, float height)
        {
            Rect(rects, cell, out float u0, out float v0, out float u1, out float v1);
            var side = new Vector3(Mathf.Cos(az), 0f, Mathf.Sin(az)) * (w * 0.5f);
            int i0 = b.v.Count;
            Vector3 topP = basePos + Vector3.up * h;
            b.v.Add(basePos - side); b.v.Add(basePos + side); b.v.Add(topP + side); b.v.Add(topP - side);
            b.uv.Add(new Vector2(u0, v0)); b.uv.Add(new Vector2(u1, v0)); b.uv.Add(new Vector2(u1, v1)); b.uv.Add(new Vector2(u0, v1));
            Vector3 nn = (Vector3.up + Vector3.Cross(side.normalized, Vector3.up) * 0.3f).normalized;
            for (int k = 0; k < 4; k++) b.n.Add(nn);
            var c0 = new Color(0.8f, 0.4f, 0.3f, 1f);
            var c1 = new Color(1f, 1f, 0.3f, 1f);
            b.c.Add(c0); b.c.Add(c0); b.c.Add(c1); b.c.Add(c1);
            b.leaves.Add(i0); b.leaves.Add(i0 + 2); b.leaves.Add(i0 + 1);
            b.leaves.Add(i0); b.leaves.Add(i0 + 3); b.leaves.Add(i0 + 2);
        }

        static float Rnd(float a, float b, System.Random r) { return a + (float)r.NextDouble() * (b - a); }
    }
}
