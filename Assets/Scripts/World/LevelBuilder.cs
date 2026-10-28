using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Rendering;

namespace ZombieStrike
{
    /// <summary>
    /// Builds the night-time walled town square: ground, walls, buildings, wrecked cars,
    /// cover, trees, lamps and burning barrels. Static geometry is merged into a few meshes,
    /// collisions use plain box colliders, and a NavMesh is baked at start-up for the zombies.
    /// </summary>
    public class LevelBuilder : MonoBehaviour
    {
        public const float Half = 44f;

        public readonly List<Vector3> SpawnPoints = new List<Vector3>();
        public Vector3 PlayerStart { get; private set; }
        public float PlayerYaw { get; private set; }
        public bool HasNavMesh { get; private set; }

        Transform root, solids;
        StaticBatch batch;
        System.Random rng;
        NavMeshDataInstance navInstance;

        public void Build()
        {
            rng = new System.Random(1234);
            root = new GameObject("Level").transform;
            solids = new GameObject("Colliders").transform;
            solids.SetParent(root, false);
            batch = new StaticBatch(24f);

            SetupLighting();
            BuildGround();
            BuildWalls();
            BuildBuildings();
            BuildCars();
            BuildCover();
            BuildTrees();
            BuildLamps();
            BuildFires();
            BuildDecals();
            batch.Finish(root);

            BuildNavMesh();
            FindSpawnPoints();
            PlayerStart = new Vector3(0f, 0.05f, -4f);
            PlayerYaw = 0f;
        }

        void OnDestroy()
        {
            if (navInstance.valid) navInstance.Remove();
        }

        float R(float a, float b)
        {
            return a + (float)rng.NextDouble() * (b - a);
        }

        // ----------------------------------------------------------------- helpers

        void Solid(Vector3 center, Vector3 size, Quaternion rot)
        {
            var go = new GameObject("Solid");
            go.transform.SetParent(solids, false);
            go.transform.position = center;
            go.transform.rotation = rot;
            go.AddComponent<BoxCollider>().size = size;
        }

        void Geo(Material m, Vector3 center, Vector3 size, Quaternion rot, float uvTile = 0f, float cell = 0f, int faces = 63)
        {
            batch.For(m, center).AddBox(center, size, rot, uvTile, cell, faces);
        }

        void Block(Material m, Vector3 center, Vector3 size, Quaternion rot, float uvTile = 0f, float cell = 0f)
        {
            Geo(m, center, size, rot, uvTile, cell);
            Solid(center, size, rot);
        }

        static Color Shade(Color c, float k)
        {
            return new Color(c.r * k, c.g * k, c.b * k, 1f);
        }

        // ----------------------------------------------------------------- lighting

        void SetupLighting()
        {
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = 0.042f;
            RenderSettings.fogColor = new Color(0.06f, 0.075f, 0.09f);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.25f, 0.27f, 0.33f);

            var moonGo = new GameObject("Moonlight");
            moonGo.transform.SetParent(root, false);
            moonGo.transform.rotation = Quaternion.Euler(48f, -35f, 0f);
            var moon = moonGo.AddComponent<Light>();
            moon.type = LightType.Directional;
            moon.color = new Color(0.62f, 0.7f, 0.95f);
            moon.intensity = 0.5f;
            moon.shadows = LightShadows.None;
        }

        // ----------------------------------------------------------------- ground & walls

        void BuildGround()
        {
            Material asphalt = Art.Lit(new Color(0.82f, 0.82f, 0.85f), "asphalt");
            for (int x = -3; x < 3; x++)
            {
                for (int z = -3; z < 3; z++)
                {
                    var c = new Vector3(x * 20f + 10f, -0.5f, z * 20f + 10f);
                    Geo(asphalt, c, new Vector3(20f, 1f, 20f), Quaternion.identity, 4f, 2.5f, 1 << 2);
                }
            }
            Solid(new Vector3(0f, -0.5f, 0f), new Vector3(140f, 1f, 140f), Quaternion.identity);

            // road markings
            Material yellow = Art.Lit(new Color(0.85f, 0.72f, 0.25f));
            Material white = Art.Lit(new Color(0.75f, 0.75f, 0.75f));
            for (float x = -40f; x <= 40f; x += 5f)
                Geo(yellow, new Vector3(x, 0.01f, 0f), new Vector3(2.4f, 0.02f, 0.18f), Quaternion.identity);
            Geo(white, new Vector3(0f, 0.01f, 6.5f), new Vector3(86f, 0.02f, 0.15f), Quaternion.identity);
            Geo(white, new Vector3(0f, 0.01f, -6.5f), new Vector3(86f, 0.02f, 0.15f), Quaternion.identity);
            // crossing
            for (int i = 0; i < 7; i++)
                Geo(white, new Vector3(-16f, 0.01f, -5.4f + i * 1.8f), new Vector3(3.2f, 0.02f, 0.9f), Quaternion.identity);
        }

        void BuildWalls()
        {
            Material brick = Art.Lit(new Color(0.9f, 0.85f, 0.82f), "brick");
            Material cap = Art.Lit(new Color(0.5f, 0.5f, 0.52f), "concrete");
            const float h = 4.6f, t = 1.2f;
            float len = Half * 2f + t * 2f;
            Quaternion q = Quaternion.identity;
            Block(brick, new Vector3(0f, h / 2f, Half + t / 2f), new Vector3(len, h, t), q, 2f, 2.5f);
            Block(brick, new Vector3(0f, h / 2f, -Half - t / 2f), new Vector3(len, h, t), q, 2f, 2.5f);
            Block(brick, new Vector3(Half + t / 2f, h / 2f, 0f), new Vector3(t, h, len), q, 2f, 2.5f);
            Block(brick, new Vector3(-Half - t / 2f, h / 2f, 0f), new Vector3(t, h, len), q, 2f, 2.5f);

            Geo(cap, new Vector3(0f, h + 0.15f, Half + t / 2f), new Vector3(len + 0.3f, 0.3f, t + 0.3f), q, 2f);
            Geo(cap, new Vector3(0f, h + 0.15f, -Half - t / 2f), new Vector3(len + 0.3f, 0.3f, t + 0.3f), q, 2f);
            Geo(cap, new Vector3(Half + t / 2f, h + 0.15f, 0f), new Vector3(t + 0.3f, 0.3f, len + 0.3f), q, 2f);
            Geo(cap, new Vector3(-Half - t / 2f, h + 0.15f, 0f), new Vector3(t + 0.3f, 0.3f, len + 0.3f), q, 2f);

            for (float p = -Half; p <= Half + 0.1f; p += 11f)
            {
                Vector3 s = new Vector3(1.4f, h + 0.7f, 1.4f);
                Block(cap, new Vector3(p, s.y / 2f, Half - 0.2f), s, q, 2f);
                Block(cap, new Vector3(p, s.y / 2f, -Half + 0.2f), s, q, 2f);
                Block(cap, new Vector3(Half - 0.2f, s.y / 2f, p), s, q, 2f);
                Block(cap, new Vector3(-Half + 0.2f, s.y / 2f, p), s, q, 2f);
            }
        }

        // ----------------------------------------------------------------- buildings

        void BuildBuildings()
        {
            Building(new Vector3(-30f, 0f, 27f), new Vector3(14f, 9f, 11f), new Color(0.72f, 0.7f, 0.66f));
            Building(new Vector3(29f, 0f, 29f), new Vector3(12f, 6.5f, 10f), new Color(0.6f, 0.64f, 0.7f));
            Building(new Vector3(-30f, 0f, -27f), new Vector3(11f, 7.5f, 13f), new Color(0.72f, 0.62f, 0.55f));
            Building(new Vector3(28f, 0f, -26f), new Vector3(13f, 10f, 11f), new Color(0.66f, 0.66f, 0.66f));
            // small guard shack and a kiosk
            Building(new Vector3(9f, 0f, 16f), new Vector3(4f, 3.2f, 3.2f), new Color(0.55f, 0.6f, 0.55f));
            Building(new Vector3(-10f, 0f, -30f), new Vector3(5f, 3.4f, 3.5f), new Color(0.62f, 0.55f, 0.5f));
        }

        void Building(Vector3 pos, Vector3 size, Color tint)
        {
            Quaternion rot = Quaternion.identity;
            Material wallMat = Art.Lit(tint, "concrete");
            Material trim = Art.Lit(Shade(tint, 0.65f), "concrete");
            Block(wallMat, pos + Vector3.up * size.y * 0.5f, size, rot, 4f, 3f);
            Geo(trim, pos + Vector3.up * (size.y + 0.2f), new Vector3(size.x + 0.4f, 0.4f, size.z + 0.4f), rot, 2f);
            Geo(trim, pos + Vector3.up * 0.25f, new Vector3(size.x + 0.15f, 0.5f, size.z + 0.15f), rot, 2f);

            Material lit = Art.Unlit(new Color(1f, 0.82f, 0.45f));
            Material dim = Art.Unlit(new Color(0.3f, 0.25f, 0.15f));
            Material dark = Art.Unlit(new Color(0.04f, 0.05f, 0.07f));
            Material door = Art.Lit(new Color(0.3f, 0.2f, 0.13f));

            // faces: +X, -X, +Z, -Z
            Vector3[] normals = { Vector3.right, Vector3.left, Vector3.forward, Vector3.back };
            Vector3 toCenter = -pos;
            toCenter.y = 0f;
            int doorFace = 0;
            float best = -2f;
            for (int f = 0; f < 4; f++)
            {
                float d = Vector3.Dot(normals[f], toCenter.normalized);
                if (d > best) { best = d; doorFace = f; }
            }

            for (int f = 0; f < 4; f++)
            {
                Vector3 n = normals[f];
                bool alongX = Mathf.Abs(n.z) > 0.5f; // face spans the X axis
                float width = alongX ? size.x : size.z;
                float depth = alongX ? size.z : size.x;
                Vector3 tangent = alongX ? Vector3.right : Vector3.forward;
                int count = Mathf.Max(1, Mathf.FloorToInt((width - 1.5f) / 3f));
                float start = -(count - 1) * 1.5f;
                for (int k = 0; ; k++)
                {
                    float y = 1.9f + k * 3f;
                    if (y + 0.9f > size.y - 0.3f) break;
                    for (int i = 0; i < count; i++)
                    {
                        float off = start + i * 3f;
                        if (f == doorFace && k == 0 && Mathf.Abs(off) < 1.6f) continue;
                        Vector3 c = pos + n * (depth * 0.5f + 0.04f) + tangent * off + Vector3.up * y;
                        Vector3 s = alongX ? new Vector3(1.3f, 1.5f, 0.08f) : new Vector3(0.08f, 1.5f, 1.3f);
                        double r = rng.NextDouble();
                        Material m = r < 0.22 ? lit : (r < 0.32 ? dim : dark);
                        Geo(m, c, s, rot);
                    }
                }
                if (f == doorFace && size.y > 2.8f)
                {
                    Vector3 c = pos + n * (depth * 0.5f + 0.05f) + Vector3.up * 1.25f;
                    Vector3 s = alongX ? new Vector3(1.6f, 2.5f, 0.1f) : new Vector3(0.1f, 2.5f, 1.6f);
                    Geo(door, c, s, rot);
                }
            }
        }

        // ----------------------------------------------------------------- cars

        void BuildCars()
        {
            Car(new Vector3(-12f, 0f, 9f), 25f, new Color(0.6f, 0.13f, 0.1f));
            Car(new Vector3(13f, 0f, 5f), -65f, new Color(0.22f, 0.32f, 0.55f));
            Car(new Vector3(-7f, 0f, -17f), 95f, new Color(0.78f, 0.78f, 0.75f));
            Car(new Vector3(10f, 0f, -13f), 12f, new Color(0.24f, 0.4f, 0.27f));
            Car(new Vector3(-21f, 0f, -3f), -40f, new Color(0.85f, 0.66f, 0.15f));
            Car(new Vector3(20f, 0f, 14f), 120f, new Color(0.42f, 0.42f, 0.45f));
            Car(new Vector3(2f, 0f, 27f), 80f, new Color(0.14f, 0.14f, 0.16f));
            Car(new Vector3(-2f, 0f, -33f), -15f, new Color(0.5f, 0.25f, 0.45f));
        }

        void Car(Vector3 pos, float yaw, Color paint)
        {
            Quaternion rot = Quaternion.Euler(0f, yaw, 0f);
            Material body = Art.Lit(paint, "metal");
            Material glass = Art.Lit(new Color(0.08f, 0.1f, 0.13f));
            Material tire = Art.Lit(new Color(0.07f, 0.07f, 0.07f));
            Material trim = Art.Lit(new Color(0.12f, 0.12f, 0.12f));
            Material head = Art.Unlit(new Color(0.95f, 0.92f, 0.75f));
            Material tail = Art.Unlit(new Color(0.6f, 0.04f, 0.04f));

            Geo(body, pos + rot * new Vector3(0f, 0.72f, 0f), new Vector3(4.3f, 0.72f, 1.9f), rot, 1.5f);
            Geo(glass, pos + rot * new Vector3(-0.25f, 1.38f, 0f), new Vector3(2.3f, 0.62f, 1.7f), rot);
            Geo(body, pos + rot * new Vector3(-0.25f, 1.72f, 0f), new Vector3(2.4f, 0.08f, 1.76f), rot, 1.5f);
            Geo(trim, pos + rot * new Vector3(2.2f, 0.5f, 0f), new Vector3(0.14f, 0.22f, 1.95f), rot);
            Geo(trim, pos + rot * new Vector3(-2.2f, 0.5f, 0f), new Vector3(0.14f, 0.22f, 1.95f), rot);
            for (int s = -1; s <= 1; s += 2)
            {
                Geo(head, pos + rot * new Vector3(2.16f, 0.83f, s * 0.62f), new Vector3(0.05f, 0.15f, 0.38f), rot);
                Geo(tail, pos + rot * new Vector3(-2.16f, 0.83f, s * 0.62f), new Vector3(0.05f, 0.15f, 0.38f), rot);
            }
            Quaternion wheelRot = rot * Quaternion.Euler(90f, 0f, 0f);
            for (int sx = -1; sx <= 1; sx += 2)
            {
                for (int sz = -1; sz <= 1; sz += 2)
                {
                    Vector3 basePos = pos + rot * new Vector3(sx * 1.38f, 0.37f, sz * 0.92f - 0.15f);
                    batch.For(tire, basePos).AddCylinder(basePos, 0.37f, 0.3f, 10, wheelRot, 0f);
                }
            }
            Solid(pos + Vector3.up * 0.85f, new Vector3(4.3f, 1.7f, 1.9f), rot);
        }

        // ----------------------------------------------------------------- cover

        void BuildCover()
        {
            Material crate = Art.Lit(new Color(0.95f, 0.92f, 0.88f), "crate");
            Vector3[] stacks =
            {
                new Vector3(5f, 0f, 9f), new Vector3(-9f, 0f, 18f), new Vector3(16f, 0f, -5f), new Vector3(-15f, 0f, -13f),
                new Vector3(3f, 0f, -24f), new Vector3(-26f, 0f, 8f), new Vector3(26f, 0f, 3f), new Vector3(-2f, 0f, 14f),
                new Vector3(17f, 0f, 26f), new Vector3(-18f, 0f, 30f)
            };
            foreach (Vector3 p in stacks)
            {
                float yaw = R(0f, 90f);
                Quaternion rot = Quaternion.Euler(0f, yaw, 0f);
                int n = 2 + rng.Next(3);
                for (int i = 0; i < n; i++)
                {
                    float s = R(1.0f, 1.3f);
                    Vector3 off = rot * new Vector3((i % 2) * 1.3f, 0f, (i / 2) * 1.3f);
                    Vector3 c = p + off + Vector3.up * (s * 0.5f);
                    Quaternion r2 = Quaternion.Euler(0f, yaw + R(-12f, 12f), 0f);
                    Block(crate, c, new Vector3(s, s, s), r2);
                    if (i == 0 && rng.NextDouble() < 0.6)
                    {
                        float s2 = R(0.8f, 1.0f);
                        Block(crate, c + Vector3.up * (s * 0.5f + s2 * 0.5f), new Vector3(s2, s2, s2), Quaternion.Euler(0f, yaw + R(-30f, 30f), 0f));
                    }
                }
                // barrels next to some stacks
                if (rng.NextDouble() < 0.7)
                {
                    Vector3 b = p + rot * new Vector3(-1.4f, 0f, 0.4f);
                    Barrel(b, BarrelColor());
                    if (rng.NextDouble() < 0.5) Barrel(b + rot * new Vector3(0f, 0f, 1.0f), BarrelColor());
                }
            }

            // concrete jersey barriers
            Material concrete = Art.Lit(new Color(0.62f, 0.62f, 0.6f), "concrete");
            Vector3[] barriers =
            {
                new Vector3(-6f, 0f, 3f), new Vector3(6.5f, 0f, 1.5f), new Vector3(0f, 0f, -11f), new Vector3(-30f, 0f, -12f),
                new Vector3(31f, 0f, -10f), new Vector3(-12f, 0f, 23f), new Vector3(12f, 0f, 35f), new Vector3(22f, 0f, -36f)
            };
            float[] barrierYaw = { 20f, -15f, 90f, 0f, 75f, 40f, 0f, -30f };
            for (int i = 0; i < barriers.Length; i++)
            {
                Quaternion rot = Quaternion.Euler(0f, barrierYaw[i], 0f);
                Vector3 p = barriers[i];
                Geo(concrete, p + Vector3.up * 0.18f, new Vector3(2.4f, 0.36f, 0.7f), rot, 2f);
                Geo(concrete, p + Vector3.up * 0.63f, new Vector3(2.4f, 0.54f, 0.36f), rot, 2f);
                Solid(p + Vector3.up * 0.45f, new Vector3(2.4f, 0.9f, 0.7f), rot);
            }

            // sandbag nests
            Material sand = Art.Lit(new Color(0.62f, 0.56f, 0.42f), "grime");
            SandbagWall(new Vector3(-3f, 0f, -1f), 30f, sand);
            SandbagWall(new Vector3(3.5f, 0f, -6.5f), -60f, sand);
        }

        void SandbagWall(Vector3 pos, float yaw, Material sand)
        {
            Quaternion rot = Quaternion.Euler(0f, yaw, 0f);
            for (int row = 0; row < 2; row++)
            {
                int count = 3 - row;
                for (int i = 0; i < count; i++)
                {
                    float x = (i - (count - 1) * 0.5f) * 0.92f;
                    Vector3 c = pos + rot * new Vector3(x, 0.19f + row * 0.36f, 0f);
                    Geo(sand, c, new Vector3(0.9f, 0.36f, 0.5f), Quaternion.Euler(0f, yaw + R(-6f, 6f), 0f));
                }
            }
            Solid(pos + Vector3.up * 0.4f, new Vector3(2.8f, 0.8f, 0.55f), rot);
        }

        Color BarrelColor()
        {
            Color[] c = { new Color(0.55f, 0.2f, 0.12f), new Color(0.2f, 0.3f, 0.5f), new Color(0.25f, 0.4f, 0.25f), new Color(0.6f, 0.5f, 0.2f) };
            return c[rng.Next(c.Length)];
        }

        void Barrel(Vector3 pos, Color color)
        {
            Material m = Art.Lit(color, "metal");
            batch.For(m, pos).AddCylinder(pos, 0.42f, 1.1f, 12, Quaternion.identity, 0f);
            Solid(pos + Vector3.up * 0.55f, new Vector3(0.84f, 1.1f, 0.84f), Quaternion.identity);
        }

        // ----------------------------------------------------------------- trees

        void BuildTrees()
        {
            Vector3[] trees =
            {
                new Vector3(-40f, 0f, 10f), new Vector3(40f, 0f, -8f), new Vector3(-15f, 0f, 40f), new Vector3(16f, 0f, -40f),
                new Vector3(39f, 0f, 37f), new Vector3(-39f, 0f, -38f), new Vector3(-40f, 0f, 2f), new Vector3(40f, 0f, 12f)
            };
            Material bark = Art.Lit(new Color(0.28f, 0.22f, 0.17f), "grime");
            foreach (Vector3 p in trees)
            {
                float height = R(4.5f, 6f);
                batch.For(bark, p).AddCylinder(p, 0.24f, height, 8, Quaternion.identity, 0f);
                int branches = 4 + rng.Next(3);
                for (int i = 0; i < branches; i++)
                {
                    float y = R(height * 0.45f, height * 0.95f);
                    float len = R(1.0f, 2.2f);
                    Quaternion r = Quaternion.Euler(R(30f, 65f), R(0f, 360f), 0f);
                    Vector3 c = p + Vector3.up * y + r * new Vector3(0f, len * 0.5f, 0f);
                    Geo(bark, c, new Vector3(0.12f, len, 0.12f), r);
                }
                Solid(p + Vector3.up * height * 0.5f, new Vector3(0.5f, height, 0.5f), Quaternion.identity);
            }
        }

        // ----------------------------------------------------------------- lights

        void BuildLamps()
        {
            Lamp(new Vector3(-14f, 0f, 7.5f), 0f);
            Lamp(new Vector3(18f, 0f, -7.5f), 180f);
            Lamp(new Vector3(-24f, 0f, -20f), 90f);
            Lamp(new Vector3(22f, 0f, 22f), -90f);
        }

        void Lamp(Vector3 pos, float yaw)
        {
            Quaternion rot = Quaternion.Euler(0f, yaw, 0f);
            Material metal = Art.Lit(new Color(0.2f, 0.21f, 0.22f));
            Material bulb = Art.Unlit(new Color(1f, 0.85f, 0.6f));
            batch.For(metal, pos).AddCylinder(pos, 0.09f, 5.6f, 8, Quaternion.identity, 0f);
            Geo(metal, pos + rot * new Vector3(0.7f, 5.55f, 0f), new Vector3(1.5f, 0.1f, 0.1f), rot);
            Geo(metal, pos + rot * new Vector3(1.35f, 5.45f, 0f), new Vector3(0.55f, 0.16f, 0.32f), rot);
            Geo(bulb, pos + rot * new Vector3(1.35f, 5.35f, 0f), new Vector3(0.4f, 0.05f, 0.22f), rot);
            Solid(pos + Vector3.up * 2.8f, new Vector3(0.25f, 5.6f, 0.25f), Quaternion.identity);

            var lightGo = new GameObject("LampLight");
            lightGo.transform.SetParent(root, false);
            lightGo.transform.position = pos + rot * new Vector3(1.35f, 5.0f, 0f);
            var l = lightGo.AddComponent<Light>();
            l.type = LightType.Point;
            l.range = 14f;
            l.intensity = 1.5f;
            l.color = new Color(1f, 0.78f, 0.5f);
            l.shadows = LightShadows.None;
        }

        void BuildFires()
        {
            BurningBarrel(new Vector3(-4.5f, 0f, 5.5f));
            BurningBarrel(new Vector3(7f, 0f, -6f));
            BurningBarrel(new Vector3(0.5f, 0f, 31f));
            BurningBarrel(new Vector3(-33f, 0f, 0f));
        }

        void BurningBarrel(Vector3 pos)
        {
            Barrel(pos, new Color(0.3f, 0.18f, 0.12f));
            var go = new GameObject("BurningBarrel");
            go.transform.SetParent(root, false);
            go.transform.position = pos;
            Fx.MakeFire(go.transform, new Vector3(0f, 1.05f, 0f), 1f);
            var lightGo = new GameObject("FireLight");
            lightGo.transform.SetParent(go.transform, false);
            lightGo.transform.localPosition = new Vector3(0f, 1.8f, 0f);
            var l = lightGo.AddComponent<Light>();
            l.type = LightType.Point;
            l.range = 10f;
            l.intensity = 1.9f;
            l.color = new Color(1f, 0.55f, 0.2f);
            l.shadows = LightShadows.None;
            lightGo.AddComponent<Flicker>();
        }

        // ----------------------------------------------------------------- decals

        void BuildDecals()
        {
            Material blood = Art.Transparent("blood");
            for (int i = 0; i < 16; i++)
            {
                var c = new Vector3(R(-36f, 36f), 0.012f + i * 0.0005f, R(-36f, 36f));
                float s = R(0.8f, 2.2f) * 0.5f;
                Quaternion r = Quaternion.Euler(0f, R(0f, 360f), 0f);
                Vector3 a = c + r * new Vector3(-s, 0f, -s);
                Vector3 b = c + r * new Vector3(-s, 0f, s);
                Vector3 d = c + r * new Vector3(s, 0f, s);
                Vector3 e = c + r * new Vector3(s, 0f, -s);
                batch.For(blood, c).AddQuad(a, b, d, e, Vector3.up, Vector3.up, Vector3.up, Vector3.up,
                    new Vector2(0f, 0f), new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(1f, 0f));
            }
        }

        // ----------------------------------------------------------------- navigation

        void BuildNavMesh()
        {
            try
            {
                var sources = new List<NavMeshBuildSource>();
                var markups = new List<NavMeshBuildMarkup>();
                UnityEngine.AI.NavMeshBuilder.CollectSources(solids, ~0, NavMeshCollectGeometry.PhysicsColliders, 0, markups, sources);
                NavMeshBuildSettings s = NavMesh.GetSettingsByID(0);
                s.agentRadius = 0.4f;
                s.agentHeight = 1.8f;
                s.agentClimb = 0.3f;
                s.agentSlope = 40f;
                s.overrideVoxelSize = true;
                s.voxelSize = 0.15f;
                s.overrideTileSize = true;
                s.tileSize = 128;
                var bounds = new Bounds(new Vector3(0f, 2f, 0f), new Vector3(Half * 2f + 6f, 12f, Half * 2f + 6f));
                NavMeshData data = UnityEngine.AI.NavMeshBuilder.BuildNavMeshData(s, sources, bounds, Vector3.zero, Quaternion.identity);
                if (data != null)
                {
                    navInstance = NavMesh.AddNavMeshData(data);
                    HasNavMesh = navInstance.valid;
                }
                Debug.Log("[ZS] navmesh " + (HasNavMesh ? "ready" : "FAILED") + " from " + sources.Count + " colliders");
            }
            catch (System.Exception e)
            {
                Debug.LogError("[ZS] navmesh build failed: " + e);
                HasNavMesh = false;
            }
        }

        void FindSpawnPoints()
        {
            float edge = Half - 3f;
            var candidates = new List<Vector3>();
            for (float x = -36f; x <= 36.1f; x += 12f)
            {
                candidates.Add(new Vector3(x, 0f, edge));
                candidates.Add(new Vector3(x, 0f, -edge));
            }
            for (float z = -24f; z <= 24.1f; z += 12f)
            {
                candidates.Add(new Vector3(edge, 0f, z));
                candidates.Add(new Vector3(-edge, 0f, z));
            }
            foreach (Vector3 c in candidates)
            {
                if (HasNavMesh)
                {
                    NavMeshHit hit;
                    if (NavMesh.SamplePosition(c, out hit, 3f, NavMesh.AllAreas)) SpawnPoints.Add(hit.position);
                }
                else
                {
                    SpawnPoints.Add(c);
                }
            }
            Debug.Log("[ZS] spawn points: " + SpawnPoints.Count);
        }
    }
}
