using UnityEngine;

namespace RealFPS.EditorTools
{
    /// <summary>
    /// The valley's layout as pure functions of world position: terrain height,
    /// the lake, the trail, forest density and the splat weights. Shared by the
    /// terrain, the scatter passes and the water so everything lines up.
    /// </summary>
    public static class RFLayout
    {
        public const float TerrainSize = 512f;
        public const float TerrainHeight = 160f;
        public static readonly Vector3 TerrainPos = new Vector3(-256f, 0f, -256f);
        public const float Water = 20f;

        // valley (elliptical metric centred on the lake region)
        public static readonly Vector2 ValleyCenter = new Vector2(0f, 35f);
        public const float PlayRadius = 158f;
        public static readonly Vector2 PlayCenter = new Vector2(0f, 40f);

        // lake ellipse
        public static readonly Vector2 LakeCenter = new Vector2(8f, 62f);
        public static readonly Vector2 LakeRadii = new Vector2(72f, 46f);
        public const float LakeAngle = 12f;
        public const float LakeDepth = 8f;

        public static readonly Vector2 Spawn = new Vector2(-6f, -50f);
        public static readonly Vector2 Campfire = new Vector2(-32f, -16f);
        public static readonly Vector2 Lookout = new Vector2(-98f, 14f);

        // the trail: spawn -> lake (pier), a loop around the lake, spurs to the campfire and the lookout
        public static readonly Vector2[][] Trails = BuildTrails();

        static Vector2[][] BuildTrails()
        {
            var loop = new Vector2[19];
            for (int i = 0; i < loop.Length; i++)
            {
                float t = (-100f + i * 360f / (loop.Length - 1)) * Mathf.Deg2Rad;
                float e = 1.3f + 0.06f * Mathf.Sin(i * 2.3f);
                loop[i] = LakePoint(t, e);
            }
            Vector2 south = LakePoint(-100f * Mathf.Deg2Rad, 1.3f);
            Vector2 west = LakePoint(180f * Mathf.Deg2Rad, 1.3f);
            return new[]
            {
                new[] { new Vector2(-6f, -66f), new Vector2(-5f, -46f), new Vector2(-1f, -26f), new Vector2(3f, -10f), south, PierShore(1.02f) },
                new[] { new Vector2(-1f, -26f), new Vector2(-14f, -22f), Campfire + new Vector2(5f, 1f) },
                loop,
                new[] { west, Vector2.Lerp(west, Lookout, 0.5f) + new Vector2(4f, 3f), Lookout },
            };
        }

        public const float PierAngle = -100f;
        public static Vector2 PierShore(float e) { return LakePoint(PierAngle * Mathf.Deg2Rad, e); }

        // ------------------------------------------------------------------ noise
        static float N(float x, float z) { return Mathf.PerlinNoise(x, z); }

        public static float Fbm(float x, float z, int octaves, float seed)
        {
            float sum = 0f, amp = 0.5f, norm = 0f, f = 1f;
            for (int i = 0; i < octaves; i++)
            {
                sum += N(x * f + seed + i * 17.13f, z * f - seed + i * 29.71f) * amp;
                norm += amp;
                amp *= 0.5f;
                f *= 2.03f;
            }
            return sum / norm;
        }

        public static float Ridge(float x, float z, int octaves, float seed)
        {
            float sum = 0f, amp = 0.5f, norm = 0f, f = 1f, prev = 1f;
            for (int i = 0; i < octaves; i++)
            {
                float n = 1f - Mathf.Abs(N(x * f + seed + i * 11.3f, z * f + seed * 0.7f - i * 7.9f) * 2f - 1f);
                n = n * n;
                sum += n * amp * prev;
                prev = Mathf.Clamp01(n * 1.6f);
                norm += amp;
                amp *= 0.5f;
                f *= 2.1f;
            }
            return sum / norm;
        }

        static float Smooth(float a, float b, float x)
        {
            float t = Mathf.Clamp01((x - a) / (b - a));
            return t * t * (3f - 2f * t);
        }

        // ------------------------------------------------------------------ shapes
        public static float ValleyR(float x, float z)
        {
            float dx = x - ValleyCenter.x, dz = (z - ValleyCenter.y) / 1.12f;
            float r = Mathf.Sqrt(dx * dx + dz * dz);
            return r + (Fbm(x / 130f, z / 130f, 3, 51f) - 0.5f) * 50f;
        }

        /// <summary>0 at the lake centre, 1 on the shoreline.</summary>
        public static float LakeE(float x, float z)
        {
            float a = LakeAngle * Mathf.Deg2Rad;
            float dx = x - LakeCenter.x, dz = z - LakeCenter.y;
            float lx = dx * Mathf.Cos(a) + dz * Mathf.Sin(a);
            float lz = -dx * Mathf.Sin(a) + dz * Mathf.Cos(a);
            float e = Mathf.Sqrt((lx / LakeRadii.x) * (lx / LakeRadii.x) + (lz / LakeRadii.y) * (lz / LakeRadii.y));
            float wobble = (Fbm(x / 45f, z / 45f, 2, 91f) - 0.5f) * 0.18f;
            return e * (1f + wobble);
        }

        /// <summary>Point on the lake shoreline at parameter angle t (radians).</summary>
        public static Vector2 LakePoint(float t, float e = 1f)
        {
            float a = LakeAngle * Mathf.Deg2Rad;
            float lx = Mathf.Cos(t) * LakeRadii.x * e, lz = Mathf.Sin(t) * LakeRadii.y * e;
            return LakeCenter + new Vector2(lx * Mathf.Cos(a) - lz * Mathf.Sin(a), lx * Mathf.Sin(a) + lz * Mathf.Cos(a));
        }

        public static float TrailDistance(float x, float z)
        {
            var p = new Vector2(x, z);
            float best = 1e9f;
            foreach (Vector2[] trail in Trails)
            {
                for (int i = 0; i < trail.Length - 1; i++)
                {
                    Vector2 a = trail[i], b = trail[i + 1];
                    Vector2 ab = b - a;
                    float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-4f));
                    float d = (a + ab * t - p).sqrMagnitude;
                    if (d < best) best = d;
                }
            }
            // a little meander so the path edges are not ruler straight
            return Mathf.Sqrt(best) + (Fbm(x / 9f, z / 9f, 2, 13f) - 0.5f) * 1.6f;
        }

        public static float TrailMask(float x, float z)
        {
            return 1f - Smooth(0.9f, 2.6f, TrailDistance(x, z));
        }

        static float Bump(float x, float z, Vector2 c, float radius, float height)
        {
            float dx = x - c.x, dz = z - c.y;
            return height * Mathf.Exp(-(dx * dx + dz * dz) / (radius * radius));
        }

        /// <summary>Terrain height in metres (world space).</summary>
        public static float Height(float x, float z)
        {
            float r = ValleyR(x, z);
            float hillsLow = Fbm(x / 85f, z / 85f, 3, 7f) * 4.5f;
            float hillsDetail = (Fbm(x / 22f, z / 22f, 3, 19f) - 0.5f) * 1.6f;
            float floor = Water + 2.2f + hillsLow + hillsDetail;
            floor += Bump(x, z, Lookout, 26f, 9f);
            floor += Bump(x, z, new Vector2(70f, -40f), 34f, 7f);
            floor += Bump(x, z, new Vector2(-60f, -70f), 30f, 6f);

            float m = Smooth(118f, 215f, r);
            float mountains = Mathf.Pow(m, 1.35f) * (72f + 62f * Ridge(x / 150f, z / 150f, 4, 3f)) + m * 16f * Fbm(x / 40f, z / 40f, 3, 33f);
            float h = floor + mountains;

            // trail: smooth out the small bumps and sink it a few centimetres
            float tm = TrailMask(x, z);
            if (tm > 0f) h = Mathf.Lerp(h, floor - hillsDetail - 0.1f + mountains, tm * 0.6f);

            // campfire clearing
            float dc = Vector2.Distance(new Vector2(x, z), Campfire);
            if (dc < 12f)
            {
                float flat = Water + 2.2f + Fbm(Campfire.x / 85f, Campfire.y / 85f, 3, 7f) * 4.5f;
                h = Mathf.Lerp(flat, h, Smooth(5f, 12f, dc));
            }

            // the lake basin with a gentle beach
            float e = LakeE(x, z);
            if (e < 1.6f)
            {
                float target = e < 1f ? Water - LakeDepth * Mathf.Pow(1f - e * e, 0.7f) : Water + (e - 1f) * 5.5f;
                h = Mathf.Lerp(target, h, Smooth(0.9f, 1.55f, e));
                if (e < 1f) h = Mathf.Min(h, Water - 0.15f - (1f - e) * 0.5f);
            }
            return Mathf.Clamp(h, 0f, TerrainHeight - 1f);
        }

        /// <summary>0..1 how strongly forest grows here.</summary>
        public static float Forest(float x, float z, float h, float slopeDeg)
        {
            float r = ValleyR(x, z);
            float belt = Smooth(78f, 122f, r);
            float patches = Smooth(0.56f, 0.7f, Fbm(x / 62f + 50f, z / 62f + 50f, 3, 77f)) * 0.85f;
            float d = Mathf.Max(belt, patches);
            d *= 1f - Smooth(88f, 108f, h);                       // tree line
            d *= 1f - Smooth(32f, 40f, slopeDeg);                 // too steep
            d *= Smooth(1.18f, 1.45f, LakeE(x, z));               // open shore
            d *= 1f - Mathf.Clamp01(1.2f - Vector2.Distance(new Vector2(x, z), Spawn + new Vector2(2f, 18f)) / 40f); // meadow at the start
            d *= Smooth(9f, 16f, Vector2.Distance(new Vector2(x, z), Campfire));
            d *= Smooth(14f, 24f, Vector2.Distance(new Vector2(x, z), Lookout));
            d *= Smooth(2.5f, 5f, TrailDistance(x, z));
            return Mathf.Clamp01(d);
        }

        /// <summary>Splat weights: grass, dirt (trail / forest floor), rock, shore.</summary>
        public static Vector4 Splat(float x, float z, float h, float slopeDeg)
        {
            float rock = Smooth(30f, 42f, slopeDeg) + Smooth(70f, 110f, h) * 0.7f;
            rock = Mathf.Clamp01(rock + (Fbm(x / 14f, z / 14f, 2, 5f) - 0.5f) * 0.3f * Smooth(24f, 34f, slopeDeg));
            float shore = Smooth(Water + 1.7f, Water + 0.3f, h + (Fbm(x / 7f, z / 7f, 2, 3f) - 0.5f) * 0.8f);
            float trail = TrailMask(x, z);
            float forest = Forest(x, z, h, slopeDeg);
            float patches = Smooth(0.62f, 0.75f, Fbm(x / 18f + 9f, z / 18f - 4f, 3, 41f)) * 0.7f;
            float dirt = Mathf.Max(trail, Mathf.Max(forest * 0.7f, patches));
            dirt = Mathf.Max(dirt, 1f - Smooth(3f, 7f, Vector2.Distance(new Vector2(x, z), Campfire)));
            rock *= 1f - shore * 0.8f;
            dirt *= (1f - rock) * (1f - shore * 0.9f);
            float grass = Mathf.Max(0f, 1f - rock - shore - dirt);
            var w = new Vector4(grass, dirt, rock, shore);
            float s = w.x + w.y + w.z + w.w;
            return s > 1e-4f ? w / s : new Vector4(1, 0, 0, 0);
        }
    }
}
