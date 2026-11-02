using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

namespace NightClass.EditorTools
{
    /// <summary>Furniture, doors, hiding places, puzzles, items, scares and the logic points.</summary>
    public static partial class NCWorld
    {
        static TeacherAI teacherAI;
        static Transform teacherSpawn;
        static readonly Dictionary<ItemType, PickupItem> worldItems = new Dictionary<ItemType, PickupItem>();

        // ------------------------------------------------------------------ furniture (merged per cell)
        static void Desk(Vector3 p, float yaw)
        {
            Matrix4x4 m = Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one);
            string g = Cell(p);
            Draw(g, mWood, m, b => { b.Box(new Vector3(0f, 0.74f, 0f), new Vector3(1.1f, 0.035f, 0.55f)); b.Box(new Vector3(0f, 0.62f, 0.05f), new Vector3(1.0f, 0.18f, 0.4f)); });
            Draw(g, mMetalDark, m, b =>
            {
                foreach (var o in new[] { new Vector2(-0.5f, -0.23f), new Vector2(0.5f, -0.23f), new Vector2(-0.5f, 0.23f), new Vector2(0.5f, 0.23f) })
                    b.Box(new Vector3(o.x, 0.36f, o.y), new Vector3(0.03f, 0.72f, 0.03f));
            });
            Draw(g, mWood, m, b => b.Box(new Vector3(0f, 0.45f, -0.55f), new Vector3(0.42f, 0.035f, 0.4f)));
            Draw(g, mWood, m, b => b.Box(new Vector3(0f, 0.75f, -0.76f), new Vector3(0.42f, 0.3f, 0.025f)));
            Draw(g, mMetalDark, m, b =>
            {
                foreach (var o in new[] { new Vector2(-0.18f, -0.38f), new Vector2(0.18f, -0.38f), new Vector2(-0.18f, -0.73f), new Vector2(0.18f, -0.73f) })
                    b.Box(new Vector3(o.x, 0.22f, o.y), new Vector3(0.025f, 0.45f, 0.025f));
                b.Box(new Vector3(-0.18f, 0.6f, -0.76f), new Vector3(0.025f, 0.3f, 0.025f));
                b.Box(new Vector3(0.18f, 0.6f, -0.76f), new Vector3(0.025f, 0.3f, 0.025f));
            });
            Collider(p + Quaternion.Euler(0f, yaw, 0f) * new Vector3(0f, 0.4f, 0f), new Vector3(1.1f, 0.8f, 0.55f), yaw);
        }

        static void BigDesk(Vector3 p, float yaw, Material mat)
        {
            Matrix4x4 m = Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one);
            Draw(Cell(p), mat, m, b =>
            {
                b.Box(new Vector3(0f, 0.76f, 0f), new Vector3(1.7f, 0.05f, 0.8f));
                b.Box(new Vector3(-0.62f, 0.37f, 0f), new Vector3(0.42f, 0.74f, 0.74f));
                b.Box(new Vector3(0.62f, 0.37f, 0f), new Vector3(0.42f, 0.74f, 0.74f));
                b.Box(new Vector3(0f, 0.5f, 0.35f), new Vector3(0.8f, 0.5f, 0.03f));
            });
            Collider(p + Vector3.up * 0.39f, new Vector3(1.7f, 0.78f, 0.8f), yaw);
        }

        static void Chalkboard(Vector3 p, float yaw, Material board)
        {
            Matrix4x4 m = Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one);
            Draw(Cell(p), board, m, b => b.Panel(Vector3.zero, new Vector3(3.4f, 1.2f, 0.02f)));
            Draw(Cell(p), mWoodDark, m, b =>
            {
                b.Box(new Vector3(0f, 0.63f, 0.01f), new Vector3(3.55f, 0.07f, 0.05f));
                b.Box(new Vector3(0f, -0.63f, -0.02f), new Vector3(3.55f, 0.06f, 0.12f));
                b.Box(new Vector3(-1.74f, 0f, 0.01f), new Vector3(0.07f, 1.3f, 0.05f));
                b.Box(new Vector3(1.74f, 0f, 0.01f), new Vector3(0.07f, 1.3f, 0.05f));
            });
        }

        static void Shelf(Vector3 p, float yaw, float w, float h, int rows, bool books, int seed)
        {
            Matrix4x4 m = Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one);
            string g = Cell(p);
            Draw(g, mWoodDark, m, b =>
            {
                b.Box(new Vector3(-w * 0.5f, h * 0.5f, 0f), new Vector3(0.04f, h, 0.36f));
                b.Box(new Vector3(w * 0.5f, h * 0.5f, 0f), new Vector3(0.04f, h, 0.36f));
                b.Box(new Vector3(0f, h * 0.5f, 0.17f), new Vector3(w, h, 0.02f));
                for (int r = 0; r <= rows; r++) b.Box(new Vector3(0f, 0.05f + (h - 0.08f) * r / rows, 0f), new Vector3(w, 0.03f, 0.36f));
            });
            if (books)
            {
                var rnd = new System.Random(seed);
                Material[] mats = { mBook1, mBook2, mBook3, mPaper };
                for (int r = 0; r < rows; r++)
                {
                    float y = 0.07f + (h - 0.08f) * r / rows;
                    float x = -w * 0.5f + 0.04f;
                    while (x < w * 0.5f - 0.08f)
                    {
                        float bw = 0.03f + (float)rnd.NextDouble() * 0.04f, bh = 0.2f + (float)rnd.NextDouble() * 0.12f;
                        if (rnd.NextDouble() < 0.12) { x += 0.08f; continue; }
                        Material bm = mats[rnd.Next(mats.Length)];
                        float bx = x;
                        Draw(g, bm, m, b => b.Box(new Vector3(bx + bw * 0.5f, y + bh * 0.5f, -0.02f), new Vector3(bw, bh, 0.24f)));
                        x += bw + 0.004f;
                    }
                }
            }
            Collider(p + Vector3.up * h * 0.5f, new Vector3(w, h, 0.38f), yaw);
        }

        static void Poster(Vector3 p, float yaw, int i, float w = 0.6f, float h = 0.85f)
        {
            Draw(Cell(p), mPosters[i % mPosters.Length], Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one), b => b.Panel(Vector3.zero, new Vector3(w, h, 0.01f)));
        }

        static void Clock(Vector3 p, float yaw)
        {
            Matrix4x4 m = Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one);
            Draw(Cell(p), mClock, m, b => b.Panel(new Vector3(0f, 0f, -0.035f), new Vector3(0.34f, 0.34f, 0.01f)));
            Draw(Cell(p), mMetalDark, m, b => b.Cylinder(new Vector3(0f, 0f, 0f), new Vector3(0f, 0f, -0.03f), 0.18f, 0.18f, 18));
        }

        static void Radiator(Vector3 p, float yaw)
        {
            Draw(Cell(p), mMetalGrey, Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one), b =>
            {
                for (int i = 0; i < 10; i++) b.Box(new Vector3(-0.45f + i * 0.1f, 0.42f, 0f), new Vector3(0.06f, 0.6f, 0.1f));
                b.Box(new Vector3(0f, 0.14f, 0f), new Vector3(1f, 0.04f, 0.05f));
            });
        }

        static void Bench(Vector3 p, float yaw, float len)
        {
            Matrix4x4 m = Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one);
            Draw(Cell(p), mWood, m, b => b.Box(new Vector3(0f, 0.44f, 0f), new Vector3(len, 0.05f, 0.32f)));
            Draw(Cell(p), mMetalDark, m, b => { b.Box(new Vector3(-len * 0.42f, 0.21f, 0f), new Vector3(0.04f, 0.42f, 0.28f)); b.Box(new Vector3(len * 0.42f, 0.21f, 0f), new Vector3(0.04f, 0.42f, 0.28f)); });
            Collider(p + Vector3.up * 0.23f, new Vector3(len, 0.46f, 0.32f), yaw);
        }

        static void Table(Vector3 p, float yaw, float w, float d, Material top)
        {
            Matrix4x4 m = Matrix4x4.TRS(p, Quaternion.Euler(0f, yaw, 0f), Vector3.one);
            Draw(Cell(p), top, m, b => b.Box(new Vector3(0f, 0.75f, 0f), new Vector3(w, 0.05f, d)));
            Draw(Cell(p), mMetalDark, m, b =>
            {
                foreach (var o in new[] { new Vector2(-1, -1), new Vector2(1, -1), new Vector2(-1, 1), new Vector2(1, 1) })
                    b.Box(new Vector3(o.x * (w * 0.5f - 0.06f), 0.37f, o.y * (d * 0.5f - 0.06f)), new Vector3(0.05f, 0.74f, 0.05f));
            });
            Collider(p + Vector3.up * 0.39f, new Vector3(w, 0.78f, d), yaw);
        }

        static void Crate(Vector3 p, float s, bool physics, int seed = 0)
        {
            if (!physics)
            {
                SBox(mCrate, p + Vector3.up * s * 0.5f, Vector3.one * s);
                return;
            }
            GameObject go = Obj("Box", null, p + Vector3.up * s * 0.5f, Quaternion.Euler(0f, seed * 23f, 0f));
            go.layer = LayerProp;
            Part(go.transform, "Mesh", mCrate, b => b.Box(Vector3.zero, Vector3.one * s));
            go.AddComponent<BoxCollider>().size = Vector3.one * s;
            var rb = go.AddComponent<Rigidbody>();
            rb.mass = 6f;
            go.AddComponent<NoiseMaker>().loudness = 16f;
        }

        static void Bucket(Vector3 p)
        {
            GameObject go = Obj("Bucket", null, p, Quaternion.identity);
            go.layer = LayerProp;
            Part(go.transform, "Mesh", mMetalGrey, b => b.Cylinder(new Vector3(0f, 0f, 0f), new Vector3(0f, 0.34f, 0f), 0.14f, 0.17f, 12, true));
            var cc = go.AddComponent<CapsuleCollider>();
            cc.radius = 0.16f; cc.height = 0.34f; cc.center = new Vector3(0f, 0.17f, 0f);
            go.AddComponent<Rigidbody>().mass = 2f;
            go.AddComponent<NoiseMaker>().loudness = 18f;
        }

        // ------------------------------------------------------------------ doors
        static Door MakeDoor(Vector3 doorwayCenter, bool alongX, Material leafMat, bool locked = false, string lockedText = "It's locked.")
        {
            float yaw = alongX ? 0f : -90f;
            Quaternion r = Quaternion.Euler(0f, yaw, 0f);
            Vector3 hingePos = doorwayCenter - r * Vector3.right * 0.53f;
            GameObject go = Obj("Door", null, hingePos, r);
            go.layer = LayerDoor;
            Part(go.transform, "Leaf", leafMat, b =>
            {
                b.Box(new Vector3(0.53f, 1.08f, 0f), new Vector3(1.04f, 2.14f, 0.05f));
                b.Box(new Vector3(0.53f, 1.55f, 0.03f), new Vector3(0.7f, 0.65f, 0.01f));
                b.Box(new Vector3(0.53f, 1.55f, -0.03f), new Vector3(0.7f, 0.65f, 0.01f));
            });
            Part(go.transform, "Handle", mBrass, b =>
            {
                b.Box(new Vector3(0.95f, 1.0f, 0.05f), new Vector3(0.12f, 0.025f, 0.03f));
                b.Box(new Vector3(0.95f, 1.0f, -0.05f), new Vector3(0.12f, 0.025f, 0.03f));
            });
            var bc = go.AddComponent<BoxCollider>();
            bc.center = new Vector3(0.53f, 1.08f, 0f);
            bc.size = new Vector3(1.04f, 2.14f, 0.06f);
            Door d = go.AddComponent<Door>();
            d.hinge = go.transform;
            d.locked = locked;
            d.lockedText = lockedText;
            // frame
            Draw(Cell(doorwayCenter), mWoodDark, Matrix4x4.TRS(doorwayCenter, r, Vector3.one), b =>
            {
                b.Box(new Vector3(-0.58f, 1.1f, 0f), new Vector3(0.06f, 2.24f, 0.26f));
                b.Box(new Vector3(0.58f, 1.1f, 0f), new Vector3(0.06f, 2.24f, 0.26f));
                b.Box(new Vector3(0f, 2.23f, 0f), new Vector3(1.22f, 0.06f, 0.26f));
            });
            return d;
        }

        // ------------------------------------------------------------------ hiding places
        static HidingSpot HideCabinet(Vector3 p, float yaw, bool wardrobe)
        {
            float w = wardrobe ? 1.0f : 0.55f, h = wardrobe ? 2.05f : 1.95f, d = wardrobe ? 0.62f : 0.52f;
            Quaternion r = Quaternion.Euler(0f, yaw, 0f);
            Material mat = wardrobe ? mWoodDark : mMetalGreen;
            GameObject go = Obj(wardrobe ? "Wardrobe" : "Locker", null, p, r);
            go.layer = LayerTrigger;   // the HIDE zone lives on this object (excluded from navmesh + hand ray)
            Part(go.transform, "Body", mat, b =>
            {
                b.Box(new Vector3(0f, h * 0.5f, d * 0.5f - 0.02f), new Vector3(w, h, 0.03f));
                b.Box(new Vector3(-w * 0.5f, h * 0.5f, 0f), new Vector3(0.03f, h, d));
                b.Box(new Vector3(w * 0.5f, h * 0.5f, 0f), new Vector3(0.03f, h, d));
                b.Box(new Vector3(0f, h - 0.015f, 0f), new Vector3(w, 0.03f, d));
                b.Box(new Vector3(0f, 0.04f, 0f), new Vector3(w, 0.08f, d));
            });
            Collider(p + r * new Vector3(0f, h * 0.5f, d * 0.5f - 0.02f), new Vector3(w, h, 0.04f), yaw);
            Collider(p + r * new Vector3(-w * 0.5f, h * 0.5f, 0f), new Vector3(0.04f, h, d), yaw);
            Collider(p + r * new Vector3(w * 0.5f, h * 0.5f, 0f), new Vector3(0.04f, h, d), yaw);
            // door with vent slats (you can peek out)
            Transform hinge = Child(go.transform, "Hinge");
            hinge.localPosition = new Vector3(-w * 0.5f, 0f, -d * 0.5f);
            Part(hinge, "Door", mat, b =>
            {
                b.Box(new Vector3(w * 0.5f, 0.6f, 0f), new Vector3(w, 1.1f, 0.025f));
                b.Box(new Vector3(w * 0.5f, h - 0.2f, 0f), new Vector3(w, 0.32f, 0.025f));
                for (int i = 0; i < 7; i++) b.Box(new Vector3(w * 0.5f, 1.2f + i * 0.075f, 0f), new Vector3(w - 0.06f, 0.035f, 0.025f));
                b.Box(new Vector3(0.02f, h * 0.5f, 0f), new Vector3(0.04f, h - 0.1f, 0.03f));
                b.Box(new Vector3(w - 0.02f, h * 0.5f, 0f), new Vector3(0.04f, h - 0.1f, 0.03f));
            });
            Part(hinge, "Handle", mMetalDark, b => b.Box(new Vector3(w - 0.08f, 1.05f, -0.03f), new Vector3(0.03f, 0.12f, 0.03f)));
            HidingSpot hs = go.AddComponent<HidingSpot>();
            hs.doorHinge = hinge;
            hs.hidePoint = Point("HidePoint", p + r * new Vector3(0f, 1.63f, 0.02f), yaw + 180f, 0f, go.transform);
            hs.hidePoint.rotation = r * Quaternion.Euler(0f, 180f, 0f);
            hs.exitPoint = Point("ExitPoint", p + r * new Vector3(0f, 0.02f, -0.85f), yaw + 180f, 0f, go.transform);
            hs.exitPoint.rotation = r * Quaternion.Euler(0f, 180f, 0f);
            var zone = go.AddComponent<BoxCollider>();
            zone.isTrigger = true;
            zone.center = new Vector3(0f, 1f, -0.8f);
            zone.size = new Vector3(w + 0.6f, 2f, 1.2f);
            return hs;
        }

        // ------------------------------------------------------------------ items
        static void ItemMesh(ItemType t, Transform parent, bool view)
        {
            switch (t)
            {
                case ItemType.MainKey:
                case ItemType.SafeKey:
                {
                    float s = t == ItemType.MainKey ? 1.3f : 0.9f;
                    Part(parent, "Key", mBrass, b =>
                    {
                        b.Torus(new Vector3(0f, 0f, -0.05f * s), Vector3.up, 0.025f * s, 0.007f * s, 14, 6);
                        b.Cylinder(new Vector3(0f, 0f, -0.025f * s), new Vector3(0f, 0f, 0.07f * s), 0.006f * s, 0.006f * s, 6);
                        b.Box(new Vector3(0.012f * s, 0f, 0.055f * s), new Vector3(0.02f * s, 0.006f * s, 0.008f * s));
                        b.Box(new Vector3(0.01f * s, 0f, 0.035f * s), new Vector3(0.016f * s, 0.006f * s, 0.008f * s));
                    });
                    break;
                }
                case ItemType.Hammer:
                    Part(parent, "Handle", mWood, b => b.Cylinder(new Vector3(0f, -0.15f, 0f), new Vector3(0f, 0.13f, 0f), 0.014f, 0.016f, 8));
                    Part(parent, "Head", mMetalDark, b => { b.Box(new Vector3(0.02f, 0.15f, 0f), new Vector3(0.13f, 0.035f, 0.035f)); b.Box(new Vector3(-0.07f, 0.16f, 0f), new Vector3(0.05f, 0.025f, 0.03f)); });
                    break;
                case ItemType.Torch:
                    Part(parent, "Stick", mWoodDark, b => b.Cylinder(new Vector3(0f, -0.25f, 0f), new Vector3(0f, 0.12f, 0f), 0.016f, 0.02f, 8));
                    Part(parent, "Wrap", mRubber, b => b.Cylinder(new Vector3(0f, 0.08f, 0f), new Vector3(0f, 0.19f, 0f), 0.032f, 0.036f, 10));
                    break;
                case ItemType.CodeNote:
                    Part(parent, "Note", mNote, b => b.Panel(Vector3.zero, new Vector3(0.15f, 0.2f, 0.004f)));
                    Part(parent, "Back", mPaper, b => b.Box(new Vector3(0f, 0f, 0.002f), new Vector3(0.15f, 0.2f, 0.002f)));
                    break;
                case ItemType.Spring:
                    Part(parent, "Coil", mMetalGrey, b =>
                    {
                        Vector3 prev = Vector3.zero;
                        for (int i = 0; i <= 48; i++)
                        {
                            float a = i * 0.5f;
                            Vector3 q = new Vector3(Mathf.Cos(a) * 0.03f, -0.07f + i * 0.003f, Mathf.Sin(a) * 0.03f);
                            if (i > 0) b.Cylinder(prev, q, 0.005f, 0.005f, 5, false);
                            prev = q;
                        }
                    });
                    break;
                case ItemType.Dynamite:
                    Part(parent, "Sticks", mRed, b =>
                    {
                        for (int i = 0; i < 3; i++)
                        {
                            float x = (i - 1) * 0.034f;
                            b.Cylinder(new Vector3(x, -0.09f, 0f), new Vector3(x, 0.09f, 0f), 0.017f, 0.017f, 10);
                        }
                    });
                    Part(parent, "Tape", mRubber, b => { b.Box(new Vector3(0f, 0.04f, 0f), new Vector3(0.11f, 0.02f, 0.04f)); b.Box(new Vector3(0f, -0.04f, 0f), new Vector3(0.11f, 0.02f, 0.04f)); });
                    Part(parent, "Fuse", mMetalDark, b => b.Cylinder(new Vector3(0f, 0.09f, 0f), new Vector3(0.03f, 0.16f, 0.01f), 0.003f, 0.003f, 4, false));
                    break;
            }
        }

        static PickupItem PlaceItem(ItemType t, Vector3 p, Quaternion rot, bool locked = false, Transform parent = null)
        {
            GameObject go = Obj("Item_" + t, parent, p, rot);
            go.layer = LayerProp;
            ItemMesh(t, go.transform, false);
            var bc = go.AddComponent<BoxCollider>();
            bc.size = t == ItemType.Torch ? new Vector3(0.12f, 0.5f, 0.12f) : new Vector3(0.22f, 0.22f, 0.22f);
            bc.center = t == ItemType.Torch ? new Vector3(0f, -0.05f, 0f) : Vector3.zero;
            PickupItem pi = go.AddComponent<PickupItem>();
            pi.type = t;
            pi.locked = locked;
            if (t == ItemType.Torch)
            {
                Fire(go.transform, new Vector3(0f, 0.2f, 0f), 0.35f);
                Light l = PointLight(go.transform, p + rot * new Vector3(0f, 0.35f, 0f), new Color(1f, 0.6f, 0.28f), 2.2f, 6.5f, "TorchLight");
                l.gameObject.AddComponent<FlickerLight>().lamp = l;
            }
            SetLayer(go, LayerProp);
            worldItems[t] = pi;
            return pi;
        }

        static void BuildTemplates(Inventory inv)
        {
            foreach (ItemType t in new[] { ItemType.MainKey, ItemType.Hammer, ItemType.Torch, ItemType.CodeNote, ItemType.SafeKey, ItemType.Spring, ItemType.Dynamite })
            {
                GameObject go = Obj("Template_" + t, templRoot, new Vector3(0f, -50f, 0f), Quaternion.identity);
                ItemMesh(t, go.transform, false);
                var bc = go.AddComponent<BoxCollider>();
                bc.size = t == ItemType.Torch ? new Vector3(0.1f, 0.45f, 0.1f) : new Vector3(0.14f, 0.14f, 0.14f);
                var rb = go.AddComponent<Rigidbody>();
                rb.mass = 0.6f;
                rb.isKinematic = true;
                rb.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
                PickupItem pi = go.AddComponent<PickupItem>();
                pi.type = t;
                pi.isTemplate = true;
                go.AddComponent<NoiseMaker>().loudness = 14f;
                if (t == ItemType.Torch)
                {
                    Fire(go.transform, new Vector3(0f, 0.2f, 0f), 0.35f);
                    Light l = PointLight(go.transform, new Vector3(0f, -49.7f, 0f), new Color(1f, 0.6f, 0.28f), 2f, 6f, "TorchLight");
                    l.gameObject.AddComponent<FlickerLight>().lamp = l;
                }
                SetLayer(go, LayerProp);
                go.SetActive(false);
                inv.templates[(int)t] = pi;
            }
        }

        static void BuildViewModels(Transform cam, Inventory inv)
        {
            Transform root = Child(cam, "ViewModels");
            root.localPosition = new Vector3(0.2f, -0.2f, 0.42f);
            inv.viewRoot = root;
            foreach (ItemType t in new[] { ItemType.MainKey, ItemType.Hammer, ItemType.Torch, ItemType.CodeNote, ItemType.SafeKey, ItemType.Spring, ItemType.Dynamite })
            {
                Transform v = Child(root, "View_" + t);
                switch (t)
                {
                    case ItemType.Torch: v.localPosition = new Vector3(0.02f, -0.02f, 0.05f); v.localRotation = Quaternion.Euler(-12f, 0f, -8f); break;
                    case ItemType.Hammer: v.localPosition = new Vector3(0f, 0.02f, 0f); v.localRotation = Quaternion.Euler(-20f, -20f, -15f); break;
                    case ItemType.CodeNote: v.localPosition = new Vector3(-0.08f, 0.04f, 0.02f); v.localRotation = Quaternion.Euler(-25f, 8f, 0f); break;
                    default: v.localPosition = new Vector3(0f, 0.03f, 0f); v.localRotation = Quaternion.Euler(-30f, -35f, 0f); break;
                }
                ItemMesh(t, v, true);
                if (t == ItemType.Torch)
                {
                    Fire(v, new Vector3(0f, 0.2f, 0f), 0.3f);
                    var lgo = new GameObject("TorchLight");
                    lgo.transform.SetParent(v, false);
                    lgo.transform.localPosition = new Vector3(0f, 0.35f, 0.1f);
                    Light l = lgo.AddComponent<Light>();
                    l.type = LightType.Point; l.color = new Color(1f, 0.62f, 0.3f); l.intensity = 2.4f; l.range = 7.5f; l.shadows = LightShadows.None;
                    l.enabled = false;
                    inv.torchLight = l;
                    ParticleSystem burst = Particles(v, "FlameBurst", new Vector3(0f, 0.22f, 0.1f), mFire, false, 0f, 0.5f, 6f, 0.5f,
                        new Color(1f, 0.7f, 0.3f, 1f), new Color(0.9f, 0.2f, 0.05f, 0.5f), 14f, 0.05f, 0f, 80);
                    burst.transform.localRotation = Quaternion.identity;
                    BurstOnce(burst, 45);
                    inv.flameBurst = burst;
                    var fgo = new GameObject("Flash");
                    fgo.transform.SetParent(v, false);
                    fgo.transform.localPosition = new Vector3(0f, 0.3f, 0.8f);
                    Light f = fgo.AddComponent<Light>();
                    f.type = LightType.Point; f.color = new Color(1f, 0.55f, 0.2f); f.range = 9f; f.intensity = 0f; f.enabled = false; f.shadows = LightShadows.None;
                    inv.flameFlash = f;
                }
                v.gameObject.SetActive(false);
                inv.views[(int)t] = v.gameObject;
            }
        }

        // ------------------------------------------------------------------ props + puzzles
        static void BuildProps()
        {
            Classrooms();
            Lounge();
            Toilets();
            WestWing();
            Cafeteria();
            Janitor();
            Entrance();
            Gym();
            Garage();
            Basement();
            SecretRoom();
            Corridor();
            LogicPoints();
        }

        static void Classrooms()
        {
            float[] x0s = { -24f, -14f, 4f };
            float[][] windows = { new[] { -21f, -17f }, new[] { -12f, -6f }, new[] { 7f, 11f } };
            float[] wardrobeX = { -15.4f, -4.65f, 5.2f };
            for (int c = 0; c < 3; c++)
            {
                float x0 = x0s[c];
                bool flip = c == 2;   // class C faces the east wall
                float boardX = flip ? x0 + 9.88f : x0 + 0.12f;
                float boardYaw = flip ? 90f : -90f;
                Chalkboard(new Vector3(boardX, 1.65f, 7f), boardYaw, mChalkboard);
                Clock(new Vector3(boardX + (flip ? -0.02f : 0.02f), 2.75f, 7f), boardYaw);
                BigDesk(new Vector3(flip ? x0 + 8.2f : x0 + 1.8f, 0f, 7f), flip ? -90f : 90f, mWoodDark);
                for (int row = 0; row < 4; row++)
                    for (int col = 0; col < 3; col++)
                    {
                        float x = flip ? x0 + 6.6f - row * 1.45f : x0 + 3.4f + row * 1.45f;
                        float z = 4.6f + col * 2.3f;
                        Desk(new Vector3(x, 0f, z), flip ? 90f : -90f);
                    }
                Shelf(new Vector3(windows[c][0], 0f, 11.72f), 0f, 1.5f, 0.95f, 2, true, c * 7 + 1);   // low bookcase under a window
                Radiator(new Vector3(windows[c][1], 0f, 11.83f), 0f);
                Poster(new Vector3(x0 + (flip ? 5f : 3.5f), 1.7f, 2.12f), 180f, c);
                Poster(new Vector3(x0 + (flip ? 7f : 5.5f), 1.7f, 2.12f), 180f, c + 1);
                HideCabinet(new Vector3(wardrobeX[c], 0f, 11.6f), 0f, true);
                patrol.Add(Point("Patrol_class" + c, new Vector3(x0 + 5f, 0f, 3.2f)));
            }
            MakeDoor(new Vector3(-16f, 0f, 2f), true, mWood);
            MakeDoor(new Vector3(-6f, 0f, 2f), true, mWood);
            MakeDoor(new Vector3(6f, 0f, 2f), true, mWood);
            // the start classroom: the player's desk and a bag
            // you wake up with your head on the last desk of class B
            playerSpawn = Point("PlayerSpawn", new Vector3(-5.0f, 0.05f, 6.9f), -90f);
            introCam = Point("IntroCam", new Vector3(-5.65f, 1.1f, 6.9f), -90f, 34f);
            Poster(new Vector3(-13.87f, 2.3f, 9.7f), -90f, 2, 0.5f, 0.7f);
            GameObject info = Trigger("Info_start", new Vector3(-7f, 1f, 3.5f), new Vector3(3f, 2f, 2f));
            info.AddComponent<InfoZone>().text = "Look around and tap the HAND button to open doors and take things.";
        }

        static void Lounge()
        {
            MakeDoor(new Vector3(0f, 0f, 2f), true, mWood);
            // sofa
            Matrix4x4 m = Matrix4x4.TRS(new Vector3(3.3f, 0f, 7f), Quaternion.Euler(0f, 90f, 0f), Vector3.one);
            Draw(Cell(new Vector3(3.3f, 0f, 7f)), mFabric, m, b =>
            {
                b.Box(new Vector3(0f, 0.25f, 0f), new Vector3(2f, 0.4f, 0.8f));
                b.Box(new Vector3(0f, 0.6f, 0.35f), new Vector3(2f, 0.55f, 0.18f));
                b.Box(new Vector3(-0.95f, 0.45f, 0f), new Vector3(0.18f, 0.5f, 0.8f));
                b.Box(new Vector3(0.95f, 0.45f, 0f), new Vector3(0.18f, 0.5f, 0.8f));
            });
            Collider(new Vector3(3.3f, 0.4f, 7f), new Vector3(0.9f, 0.8f, 2f));
            Table(new Vector3(1.9f, 0f, 7f), 90f, 1.1f, 0.6f, mWoodDark);
            Table(new Vector3(-1.8f, 0f, 5.5f), 0f, 1.6f, 0.9f, mWood);
            Draw(Cell(new Vector3(-3.6f, 0f, 9f)), mWoodDark, Matrix4x4.identity, b => { b.Box(new Vector3(-3.55f, 0.45f, 9.5f), new Vector3(0.6f, 0.9f, 2.4f)); b.Box(new Vector3(-3.55f, 0.93f, 9.5f), new Vector3(0.64f, 0.05f, 2.44f)); });
            Collider(new Vector3(-3.55f, 0.47f, 9.5f), new Vector3(0.6f, 0.94f, 2.4f));
            Draw(Cell(new Vector3(-3.5f, 1f, 9f)), mMetalDark, Matrix4x4.identity, b => b.Box(new Vector3(-3.55f, 1.15f, 9.1f), new Vector3(0.3f, 0.4f, 0.3f)));
            Poster(new Vector3(-2.2f, 1.7f, 11.87f), 0f, 3, 0.9f, 0.6f);
            HideCabinet(new Vector3(-3.62f, 0f, 3.2f), -90f, false);
            HideCabinet(new Vector3(-3.62f, 0f, 3.8f), -90f, false);
            // the safe (needs the small key from the boiler room; holds the spring)
            Vector3 sp = new Vector3(2.6f, 0f, 11.5f);
            GameObject safe = Obj("Safe", null, sp, Quaternion.Euler(0f, 180f, 0f));
            Part(safe.transform, "Body", mMetalDark, b =>
            {
                b.Box(new Vector3(0f, 0.45f, -0.27f), new Vector3(0.7f, 0.9f, 0.04f));
                b.Box(new Vector3(-0.33f, 0.45f, 0f), new Vector3(0.04f, 0.9f, 0.6f));
                b.Box(new Vector3(0.33f, 0.45f, 0f), new Vector3(0.04f, 0.9f, 0.6f));
                b.Box(new Vector3(0f, 0.88f, 0f), new Vector3(0.7f, 0.04f, 0.6f));
                b.Box(new Vector3(0f, 0.02f, 0f), new Vector3(0.7f, 0.04f, 0.6f));
                b.Box(new Vector3(0f, 0.45f, 0f), new Vector3(0.62f, 0.03f, 0.5f));
            });
            // walls of the safe only, so the hand can reach inside once it's open
            Quaternion sr = Quaternion.Euler(0f, 180f, 0f);
            Collider(sp + sr * new Vector3(0f, 0.45f, -0.2f), new Vector3(0.7f, 0.9f, 0.2f), 180f);
            Collider(sp + sr * new Vector3(-0.33f, 0.45f, 0.05f), new Vector3(0.04f, 0.9f, 0.5f), 180f);
            Collider(sp + sr * new Vector3(0.33f, 0.45f, 0.05f), new Vector3(0.04f, 0.9f, 0.5f), 180f);
            Collider(sp + sr * new Vector3(0f, 0.88f, 0.05f), new Vector3(0.7f, 0.04f, 0.5f), 180f);
            Transform sh = Child(safe.transform, "DoorHinge");
            sh.localPosition = new Vector3(-0.35f, 0f, 0.3f);
            Part(sh, "Door", mMetalGrey, b => b.Box(new Vector3(0.35f, 0.45f, 0.02f), new Vector3(0.7f, 0.88f, 0.05f)));
            Part(sh, "Dial", mBrass, b => { b.Cylinder(new Vector3(0.45f, 0.55f, 0.04f), new Vector3(0.45f, 0.55f, 0.07f), 0.06f, 0.06f, 14); b.Box(new Vector3(0.45f, 0.3f, 0.06f), new Vector3(0.05f, 0.08f, 0.02f)); });
            var sbc = safe.AddComponent<BoxCollider>();
            sbc.center = new Vector3(0f, 0.45f, 0.32f);
            sbc.size = new Vector3(0.72f, 0.9f, 0.08f);
            SafeBox box = safe.AddComponent<SafeBox>();
            box.doorHinge = sh;
            box.contents = PlaceItem(ItemType.Spring, sp + new Vector3(0f, 0.55f, -0.1f), Quaternion.identity, true);
            teacherSpawn = Point("TeacherSpawn", new Vector3(0.5f, 0f, 8.5f), 180f);
            patrol.Add(Point("Patrol_lounge", new Vector3(0f, 0f, 5f)));
        }

        static void Toilets()
        {
            MakeDoor(new Vector3(16f, 0f, 2f), true, mMetalGreen);
            foreach (float px in new[] { 17.4f, 19.2f, 21.0f, 22.8f })
                SBox(mMetalGreen, new Vector3(px, 1.02f, 10.31f), new Vector3(0.05f, 1.9f, 3.18f));
            for (int i = 0; i < 3; i++)
            {
                float x = 18.3f + i * 1.8f;
                SBox(mMetalGreen, new Vector3(x - 0.55f, 1.05f, 8.72f), new Vector3(0.7f, 1.9f, 0.04f));
                Draw(Cell(new Vector3(x, 1f, 8.7f)), mMetalGreen, Matrix4x4.TRS(new Vector3(x + 0.88f, 0f, 8.72f), Quaternion.Euler(0f, 55f + i * 12f, 0f), Vector3.one),
                    b => b.Box(new Vector3(-0.52f, 1.02f, 0f), new Vector3(1.02f, 1.8f, 0.03f)));
                Draw(Cell(new Vector3(x, 0f, 11.3f)), mCeramic, Matrix4x4.identity, b => { b.Cylinder(new Vector3(x, 0f, 11.3f), new Vector3(x, 0.42f, 11.3f), 0.2f, 0.22f, 12); b.Box(new Vector3(x, 0.7f, 11.75f), new Vector3(0.45f, 0.55f, 0.2f)); });
            }
            for (int i = 0; i < 3; i++)
            {
                float z = 4f + i * 1.6f;
                Draw(Cell(new Vector3(14.3f, 0.8f, z)), mCeramic, Matrix4x4.identity, b => { b.Box(new Vector3(14.38f, 0.82f, z), new Vector3(0.45f, 0.14f, 0.55f)); b.Cylinder(new Vector3(14.35f, 0f, z), new Vector3(14.35f, 0.76f, z), 0.08f, 0.08f, 8); });
                Draw(Cell(new Vector3(14.3f, 1.6f, z)), mMirror, Matrix4x4.TRS(new Vector3(14.13f, 1.6f, z), Quaternion.Euler(0f, -90f, 0f), Vector3.one), b => b.Panel(Vector3.zero, new Vector3(0.5f, 0.7f, 0.01f)));
            }
            // sprinkler valve on the east wall
            Vector3 vp = new Vector3(23.75f, 1.3f, 5f);
            SBox(mRust, new Vector3(23.85f, 1.6f, 5f), new Vector3(0.12f, 3.2f, 0.12f), false);
            SBox(mRust, new Vector3(23.85f, 2.95f, 3.5f), new Vector3(0.1f, 0.1f, 3f), false);
            GameObject valve = Obj("Valve", null, vp, Quaternion.Euler(0f, 90f, 0f));
            Transform wheel = Child(valve.transform, "Wheel");
            wheel.localPosition = new Vector3(0f, 0f, -0.12f);
            Part(wheel, "Rim", mRed, b =>
            {
                b.Torus(Vector3.zero, Vector3.forward, 0.16f, 0.015f, 18, 6);
                b.Box(Vector3.zero, new Vector3(0.32f, 0.02f, 0.02f));
                b.Box(Vector3.zero, new Vector3(0.02f, 0.32f, 0.02f));
            });
            var vbc = valve.AddComponent<BoxCollider>();
            vbc.center = new Vector3(0f, 0f, -0.12f);
            vbc.size = new Vector3(0.4f, 0.4f, 0.12f);
            WaterValve wv = valve.AddComponent<WaterValve>();
            wv.wheel = wheel;
            waterValve = wv;
            Poster(new Vector3(23.86f, 1.9f, 5.6f), 90f, 0, 0.3f, 0.2f);
            patrol.Add(Point("Patrol_toilets", new Vector3(18f, 0f, 5f)));
            GameObject bugs = BugPatch(new Vector3(19f, 0.02f, 4.5f), Quaternion.Euler(90f, 0f, 0f), 6, new Vector2(2f, 1.6f));
            bugs.name = "Bugs_toilets";
        }

        static WaterValve waterValve;

        static void WestWing()
        {
            MakeDoor(new Vector3(-28f, 0f, 2f), true, mWoodDark);
            MakeDoor(new Vector3(-28f, 0f, -2f), true, mWood);
            // principal's office
            BigDesk(new Vector3(-30.5f, 0f, 6.6f), 180f, mWoodDark);
            Shelf(new Vector3(-35.75f, 0f, 3.4f), -90f, 2f, 2.1f, 5, true, 31);
            for (int i = 0; i < 3; i++) SBox(mMetalGrey, new Vector3(-25f, 0.66f, 4f + i * 0.6f), new Vector3(0.55f, 1.32f, 0.5f));
            SBox(mFabric, new Vector3(-30f, 0.005f, 5.2f), new Vector3(3f, 0.01f, 2f), false);
            Draw(Cell(new Vector3(-31.1f, 0.8f, 6.7f)), mBrass, Matrix4x4.identity, b => { b.Cylinder(new Vector3(-31.1f, 0.79f, 6.75f), new Vector3(-31.1f, 1.2f, 6.75f), 0.012f, 0.012f, 6); b.Cylinder(new Vector3(-31.1f, 1.15f, 6.75f), new Vector3(-31.1f, 1.32f, 6.75f), 0.13f, 0.06f, 12); });
            PlaceItem(ItemType.CodeNote, new Vector3(-30.2f, 0.795f, 6.45f), Quaternion.Euler(90f, 20f, 0f));
            Poster(new Vector3(-24.13f, 1.8f, 6.4f), 90f, 1, 0.8f, 1f);
            patrol.Add(Point("Patrol_office", new Vector3(-29f, 0f, 4f)));
            // library
            for (int i = 0; i < 3; i++)
            {
                Shelf(new Vector3(-33.5f + i * 2.6f, 0f, -7.2f), 180f, 1.8f, 2.1f, 5, true, 40 + i);
                Shelf(new Vector3(-33.5f + i * 2.6f, 0f, -5.3f), 0f, 1.8f, 2.1f, 5, true, 50 + i);
            }
            Table(new Vector3(-32f, 0f, -3.6f), 0f, 2.4f, 0.9f, mWoodDark);
            HideCabinet(new Vector3(-24.42f, 0f, -8.6f), 90f, true);
            patrol.Add(Point("Patrol_library", new Vector3(-27f, 0f, -4f)));
            GameObject whisper = Trigger("Scare_library", new Vector3(-28f, 1f, -3f), new Vector3(2f, 2f, 1.5f));
            ScareTrigger sc = whisper.AddComponent<ScareTrigger>();
            sc.kind = ScareKind.Sound;
            sc.soundPoint = Point("WhisperPoint", new Vector3(-34f, 1.5f, -8f));
        }

        static void Cafeteria()
        {
            MakeDoor(new Vector3(-17f, 0f, -2f), true, mWood);
            for (int i = 0; i < 3; i++)
            {
                float z = -4.6f - i * 2.4f;
                Table(new Vector3(-20f, 0f, z), 0f, 4f, 0.9f, mWood);
                Bench(new Vector3(-20f, 0f, z - 0.75f), 0f, 3.8f);
                Bench(new Vector3(-20f, 0f, z + 0.75f), 0f, 3.8f);
            }
            // serving counter + cake
            SBox(mMetalGrey, new Vector3(-14.75f, 0.5f, -5.5f), new Vector3(0.9f, 1f, 5f));
            SBox(mMetalGrey, new Vector3(-14.75f, 1.02f, -5.5f), new Vector3(1f, 0.04f, 5.1f), false);
            GameObject cake = Obj("Cake", null, new Vector3(-14.75f, 1.04f, -5f), Quaternion.identity);
            GameObject slice = new GameObject("Slice");
            slice.transform.SetParent(cake.transform, false);
            Part(slice.transform, "Cake", mCake, b => b.Cylinder(Vector3.zero, new Vector3(0f, 0.11f, 0f), 0.12f, 0.12f, 16));
            Part(cake.transform, "Plate", mCeramic, b => b.Cylinder(Vector3.zero, new Vector3(0f, 0.012f, 0f), 0.17f, 0.17f, 16));
            var cbc = cake.AddComponent<BoxCollider>();
            cbc.center = new Vector3(0f, 0.06f, 0f);
            cbc.size = new Vector3(0.34f, 0.14f, 0.34f);
            cake.AddComponent<Cake>().slice = slice;
            // food elevator (needs the spring; brings the main key down)
            Vector3 dp = new Vector3(-23.75f, 0f, -7f);
            SBox(mMetalGrey, new Vector3(-23.72f, 0.4f, -7f), new Vector3(0.4f, 0.8f, 1f));
            SBox(mMetalGrey, new Vector3(-23.72f, 2.3f, -7f), new Vector3(0.4f, 1.4f, 1f), false);
            SBox(mMetalGrey, new Vector3(-23.72f, 1.2f, -7.45f), new Vector3(0.4f, 0.8f, 0.1f), false);
            SBox(mMetalGrey, new Vector3(-23.72f, 1.2f, -6.55f), new Vector3(0.4f, 0.8f, 0.1f), false);
            GameObject dumb = Obj("FoodElevator", null, dp + new Vector3(0f, 1.2f, 0f), Quaternion.identity);
            var dbc = dumb.AddComponent<BoxCollider>();
            dbc.size = new Vector3(0.3f, 0.8f, 0.8f);
            dbc.center = new Vector3(0.1f, 0f, 0f);
            Dumbwaiter dw = dumb.AddComponent<Dumbwaiter>();
            Transform car = Child(dumb.transform, "Car");
            car.localPosition = new Vector3(0f, 1.55f, 0f);
            Part(car, "Car", mMetalDark, b => { b.Box(new Vector3(0f, -0.38f, 0f), new Vector3(0.32f, 0.03f, 0.76f)); b.Box(new Vector3(-0.15f, 0f, 0f), new Vector3(0.02f, 0.76f, 0.76f)); b.Box(new Vector3(0f, 0.38f, 0f), new Vector3(0.32f, 0.03f, 0.76f)); });
            dw.car = car;
            dw.downOffset = new Vector3(0f, -1.55f, 0f);
            dw.contents = PlaceItem(ItemType.MainKey, car.position + new Vector3(0.02f, -0.34f, 0f), Quaternion.Euler(0f, 90f, 0f), true, car);
            Poster(new Vector3(-14.12f, 1.9f, -9.4f), 90f, 3, 0.7f, 0.5f);
            patrol.Add(Point("Patrol_cafeteria", new Vector3(-18f, 0f, -3.4f)));
        }

        static void Janitor()
        {
            MakeDoor(new Vector3(-10f, 0f, -2f), true, mMetalGrey);
            Shelf(new Vector3(-8.25f, 0f, -9f), 90f, 2.4f, 2f, 4, false, 0);
            for (int i = 0; i < 4; i++) SBox(mMetalGrey, new Vector3(-8.25f, 0.7f + (i % 2) * 0.5f, -10f + i * 0.5f), new Vector3(0.18f, 0.25f, 0.18f), false);
            Bucket(new Vector3(-9f, 0f, -11f));
            Bucket(new Vector3(-12.8f, 0f, -11.2f));
            Crate(new Vector3(-13.3f, 0f, -2.8f), 0.6f, true, 1);
            Crate(new Vector3(-9f, 0f, -3f), 0.5f, true, 2);
            // the hatch over the basement stairs
            GameObject hatch = Obj("Hatch", null, new Vector3(-12.2f, 0.0f, -4.7f), Quaternion.Euler(0f, -90f, 0f));
            hatch.layer = LayerDoor;
            Transform hinge = Child(hatch.transform, "Hinge");
            Part(hinge, "Leaf", mWoodDark, b =>
            {
                b.Box(new Vector3(0f, 0.025f, -0.7f), new Vector3(2.8f, 0.05f, 1.4f));
                for (int i = 0; i < 3; i++) b.Box(new Vector3(-0.9f + i * 0.9f, 0.055f, -0.7f), new Vector3(0.08f, 0.01f, 1.3f));
            });
            Part(hinge, "Ring", mMetalDark, b => b.Torus(new Vector3(0f, 0.06f, -1.25f), Vector3.up, 0.05f, 0.008f, 12, 5));
            var hbc = hinge.gameObject.AddComponent<BoxCollider>();
            hbc.center = new Vector3(0f, 0.025f, -0.7f);
            hbc.size = new Vector3(2.8f, 0.06f, 1.4f);
            SetLayer(hatch, LayerDoor);
            Trapdoor td = hatch.AddComponent<Trapdoor>();
            td.hinge = hinge;
            td.openAngle = -92f;
            GameObject ob = new GameObject("StairBlocker");
            ob.transform.SetParent(hatch.transform, false);
            ob.transform.position = new Vector3(-11.5f, -0.6f, -4.7f);
            NavMeshObstacle nob = ob.AddComponent<NavMeshObstacle>();
            nob.shape = NavMeshObstacleShape.Box;
            nob.size = new Vector3(2.8f, 1.4f, 1.4f);   // local X runs along world Z here
            nob.carving = true;
            td.blocker = nob;
            // vent duct to the cafeteria (crawl only)
            float vz = -10f;
            SBox(mMetalGrey, new Vector3(-13.2f, 1.03f, vz), new Vector3(1.6f, 0.06f, 1.0f));
            SBox(mMetalGrey, new Vector3(-13.2f, 0.5f, vz - 0.48f), new Vector3(1.6f, 1.0f, 0.05f));
            SBox(mMetalGrey, new Vector3(-13.2f, 0.5f, vz + 0.48f), new Vector3(1.6f, 1.0f, 0.05f));
            GameObject crawl = Trigger("VentCrawl", new Vector3(-13.6f, 0.5f, vz), new Vector3(2.4f, 1f, 0.9f));
            crawl.AddComponent<NoStandZone>();
            GameObject info = Trigger("Info_vent", new Vector3(-12f, 1f, vz), new Vector3(1.2f, 2f, 1.6f));
            info.AddComponent<InfoZone>().text = "A vent to the cafeteria. Crouch to crawl through - she can't follow you in there.";
            patrol.Add(Point("Patrol_janitor", new Vector3(-9.5f, 0f, -7f)));
            BugPatch(new Vector3(-8.12f, 1.3f, -5f), Quaternion.Euler(0f, 90f, 0f), 6, new Vector2(1.4f, 1f));
        }

        static void Entrance()
        {
            // main door: double leaves, planks, needs the main key
            GameObject exit = Obj("MainDoor", null, new Vector3(-2f, 0f, -14f), Quaternion.identity);
            Transform lh = Child(exit.transform, "LeftHinge");
            lh.localPosition = new Vector3(-1.1f, 0f, 0f);
            Part(lh, "Leaf", mWoodDark, b => { b.Box(new Vector3(0.55f, 1.35f, 0f), new Vector3(1.08f, 2.68f, 0.07f)); b.Box(new Vector3(0.95f, 1.1f, 0.06f), new Vector3(0.05f, 0.3f, 0.04f)); });
            Transform rh = Child(exit.transform, "RightHinge");
            rh.localPosition = new Vector3(1.1f, 0f, 0f);
            Part(rh, "Leaf", mWoodDark, b => { b.Box(new Vector3(-0.55f, 1.35f, 0f), new Vector3(1.08f, 2.68f, 0.07f)); b.Box(new Vector3(-0.95f, 1.1f, 0.06f), new Vector3(0.05f, 0.3f, 0.04f)); });
            Part(exit.transform, "Lock", mBrass, b => b.Box(new Vector3(0f, 1.1f, 0.07f), new Vector3(0.14f, 0.2f, 0.05f)));
            var ebc = exit.AddComponent<BoxCollider>();
            ebc.center = new Vector3(0f, 1.35f, 0f);
            ebc.size = new Vector3(2.2f, 2.7f, 0.1f);
            ExitDoor ed = exit.AddComponent<ExitDoor>();
            ed.leftHinge = lh;
            ed.rightHinge = rh;
            NavMeshObstacle eob = exit.AddComponent<NavMeshObstacle>();
            eob.shape = NavMeshObstacleShape.Box;
            eob.center = new Vector3(0f, 1f, 0f);
            eob.size = new Vector3(2.4f, 2f, 1.2f);
            eob.carving = true;
            GameObject planks = Obj("Planks", null, new Vector3(-2f, 0f, -13.8f), Quaternion.identity);
            var pbc = planks.AddComponent<BoxCollider>();
            pbc.center = new Vector3(0f, 1.5f, 0f);
            pbc.size = new Vector3(2.8f, 1.8f, 0.12f);
            var boards = new List<Rigidbody>();
            float[] ys = { 0.85f, 1.5f, 2.15f };
            float[] tilts = { 6f, -4f, 9f };
            for (int i = 0; i < 3; i++)
            {
                GameObject bo = Obj("Board" + i, planks.transform, new Vector3(-2f, ys[i], -13.8f), Quaternion.Euler(0f, 0f, tilts[i]));
                Part(bo.transform, "Wood", mCrate, b => b.Box(Vector3.zero, new Vector3(2.9f, 0.18f, 0.05f)));
                Part(bo.transform, "Nails", mMetalDark, b => { b.Box(new Vector3(-1.3f, 0f, -0.03f), new Vector3(0.02f, 0.02f, 0.02f)); b.Box(new Vector3(1.3f, 0f, -0.03f), new Vector3(0.02f, 0.02f, 0.02f)); });
                var bbc = bo.AddComponent<BoxCollider>();
                bbc.size = new Vector3(2.9f, 0.18f, 0.05f);
                var rb = bo.AddComponent<Rigidbody>();
                rb.isKinematic = true;
                rb.mass = 3f;
                boards.Add(rb);
            }
            Planks pl = planks.AddComponent<Planks>();
            pl.boards = boards.ToArray();
            ed.planks = pl;
            // reception, benches, trophies, map
            BigDesk(new Vector3(2.4f, 0f, -6f), -90f, mWood);
            Bench(new Vector3(-7.6f, 0f, -8f), 90f, 2.4f);
            Bench(new Vector3(3.6f, 0f, -11f), 90f, 2.4f);
            SBox(mWoodDark, new Vector3(-7.75f, 0.6f, -4.5f), new Vector3(0.4f, 1.2f, 1.6f));
            for (int i = 0; i < 3; i++)
            {
                float z = -5f + i * 0.5f;
                Draw(Cell(new Vector3(-7.75f, 1f, -4.5f)), mGold, Matrix4x4.identity, b =>
                {
                    b.Cylinder(new Vector3(-7.75f, 1.2f, z), new Vector3(-7.75f, 1.26f, z), 0.05f, 0.05f, 10);
                    b.Cylinder(new Vector3(-7.75f, 1.26f, z), new Vector3(-7.75f, 1.36f, z), 0.015f, 0.015f, 8);
                    b.Cylinder(new Vector3(-7.75f, 1.36f, z), new Vector3(-7.75f, 1.52f, z), 0.035f, 0.075f, 12);
                });
            }
            Draw(Cell(new Vector3(-7.9f, 1.7f, -9.5f)), mMap, Matrix4x4.TRS(new Vector3(-7.88f, 1.7f, -9.5f), Quaternion.Euler(0f, -90f, 0f), Vector3.one), b => b.Panel(Vector3.zero, new Vector3(1.2f, 0.85f, 0.01f)));
            GameObject info = Trigger("Info_exit", new Vector3(-2f, 1f, -11.5f), new Vector3(3f, 2f, 2f));
            info.AddComponent<InfoZone>().text = "The main entrance. Boarded up and locked... you need a hammer and the main key.";
            patrol.Add(Point("Patrol_entrance", new Vector3(-2f, 0f, -8f)));
        }

        static void Gym()
        {
            // wall bars, hoops, mats, benches
            for (int i = 0; i < 4; i++)
            {
                float z = -10f - i * 1.1f;
                Draw(Cell(new Vector3(4.2f, 1.5f, z)), mWood, Matrix4x4.identity, b =>
                {
                    b.Box(new Vector3(4.2f, 1.4f, z - 0.45f), new Vector3(0.06f, 2.8f, 0.06f));
                    b.Box(new Vector3(4.2f, 1.4f, z + 0.45f), new Vector3(0.06f, 2.8f, 0.06f));
                    for (int k = 0; k < 10; k++) b.Cylinder(new Vector3(4.22f, 0.2f + k * 0.27f, z - 0.45f), new Vector3(4.22f, 0.2f + k * 0.27f, z + 0.45f), 0.015f, 0.015f, 6, false);
                });
            }
            foreach (float x in new[] { 4.3f, 23.7f })
            {
                bool w = x < 10f;
                Draw(Cell(new Vector3(x, 3f, -6.5f)), mWood, Matrix4x4.identity, b => b.Box(new Vector3(x + (w ? 0.35f : -0.35f), 3.25f, -6.5f), new Vector3(0.04f, 1.05f, 1.8f)));
                Draw(Cell(new Vector3(x, 3f, -6.5f)), mMetalDark, Matrix4x4.identity, b => b.Box(new Vector3(x + (w ? 0.17f : -0.17f), 3.25f, -6.5f), new Vector3(0.34f, 0.06f, 0.06f)));
                Draw(Cell(new Vector3(x, 3f, -6.5f)), mRed, Matrix4x4.identity, b => b.Torus(new Vector3(x + (w ? 0.62f : -0.62f), 2.95f, -6.5f), Vector3.up, 0.23f, 0.012f, 16, 5));
            }
            for (int i = 0; i < 3; i++) SBox(mMat, new Vector3(16f, 0.08f + i * 0.16f, -14.6f), new Vector3(2f, 0.15f, 1f));
            Bench(new Vector3(12f, 0f, -2.7f), 0f, 3f);
            Bench(new Vector3(17f, 0f, -2.7f), 0f, 3f);
            // storage room: hammer + easter egg
            MakeDoor(new Vector3(20f, 0f, -11f), true, mWood);
            Crate(new Vector3(21.5f, 0f, -14.8f), 0.8f, false);
            Crate(new Vector3(22.6f, 0f, -14.8f), 0.7f, false);
            Crate(new Vector3(23.2f, 0f, -12f), 0.6f, true, 3);
            Shelf(new Vector3(18.3f, 0f, -13.5f), -90f, 2f, 2f, 3, false, 0);
            PlaceItem(ItemType.Hammer, new Vector3(21.5f, 0.86f, -14.8f), Quaternion.Euler(0f, 30f, 90f));
            GameObject egg = Obj("EasterEgg", null, new Vector3(23.88f, 1.4f, -13.6f), Quaternion.Euler(0f, 90f, 0f));
            MeshRenderer dr = Part(egg.transform, "Drawing", mChalkDraw, b => b.Panel(Vector3.zero, new Vector3(0.8f, 0.6f, 0.01f)));
            var egc = egg.AddComponent<BoxCollider>();
            egc.size = new Vector3(0.8f, 0.6f, 0.05f);
            egg.AddComponent<EasterEgg>().drawing = dr;
            patrol.Add(Point("Patrol_gym", new Vector3(13f, 0f, -9f)));
            patrol.Add(Point("Patrol_gymstore", new Vector3(21f, 0f, -12.6f)));
        }

        static void Garage()
        {
            // roller door + keypad
            GameObject roller = Obj("RollerDoor", null, new Vector3(26f, 0f, 0f), Quaternion.identity);
            roller.layer = LayerProp;   // kept out of the navmesh bake; the carving obstacle blocks her instead
            Part(roller.transform, "Panel", mMetalGrey, b =>
            {
                for (int i = 0; i < 13; i++) b.Box(new Vector3(0f, 0.1f + i * 0.2f, 0f), new Vector3(0.06f + (i % 2) * 0.02f, 0.19f, 3.2f));
            });
            var rbc = roller.AddComponent<BoxCollider>();
            rbc.center = new Vector3(0f, 1.3f, 0f);
            rbc.size = new Vector3(0.12f, 2.6f, 3.2f);
            NavMeshObstacle rob = roller.AddComponent<NavMeshObstacle>();
            rob.shape = NavMeshObstacleShape.Box;
            rob.center = new Vector3(0f, 1f, 0f);
            rob.size = new Vector3(1f, 2f, 3.4f);
            rob.carving = true;
            GameObject pad = Obj("Keypad", null, new Vector3(25.88f, 1.3f, 1.8f), Quaternion.Euler(0f, 90f, 0f));
            Part(pad.transform, "Face", mKeypad, b => b.Panel(Vector3.zero, new Vector3(0.18f, 0.26f, 0.02f)));
            Part(pad.transform, "Body", mMetalDark, b => b.Box(new Vector3(0f, 0f, 0.015f), new Vector3(0.2f, 0.28f, 0.03f)));
            MeshRenderer led = Part(pad.transform, "Led", mLed, b => b.Box(new Vector3(0f, 0.11f, -0.012f), new Vector3(0.025f, 0.012f, 0.01f)));
            var kbc = pad.AddComponent<BoxCollider>();
            kbc.size = new Vector3(0.22f, 0.3f, 0.06f);
            Keypad kp = pad.AddComponent<Keypad>();
            kp.rollerDoor = roller.transform;
            kp.obstacle = rob;
            kp.led = led;
            // car
            Vector3 cp = new Vector3(32f, 0f, -1.5f);
            Draw(Cell(cp), mCarPaint, Matrix4x4.TRS(cp, Quaternion.identity, Vector3.one), b =>
            {
                b.Box(new Vector3(0f, 0.65f, 0f), new Vector3(1.8f, 0.6f, 4.2f));
                b.Box(new Vector3(0f, 1.2f, -0.3f), new Vector3(1.6f, 0.55f, 2.2f));
            });
            Draw(Cell(cp), mGlassDark, Matrix4x4.TRS(cp, Quaternion.identity, Vector3.one), b => { b.Box(new Vector3(0f, 1.22f, 0.82f), new Vector3(1.5f, 0.45f, 0.02f)); b.Box(new Vector3(0f, 1.22f, -1.42f), new Vector3(1.5f, 0.45f, 0.02f)); });
            Draw(Cell(cp), mTire, Matrix4x4.TRS(cp, Quaternion.identity, Vector3.one), b =>
            {
                foreach (var w in new[] { new Vector2(-0.88f, 1.35f), new Vector2(0.88f, 1.35f), new Vector2(-0.88f, -1.35f), new Vector2(0.88f, -1.35f) })
                    b.Cylinder(new Vector3(w.x - 0.12f, 0.34f, w.y), new Vector3(w.x + 0.12f, 0.34f, w.y), 0.34f, 0.34f, 14);
            });
            Collider(cp + Vector3.up * 0.75f, new Vector3(1.9f, 1.5f, 4.3f));
            // workbench with dynamite
            Table(new Vector3(31f, 0f, 5.4f), 0f, 3f, 0.8f, mWoodDark);
            SBox(mWoodDark, new Vector3(31f, 1.6f, 5.9f), new Vector3(3f, 1.2f, 0.04f), false);
            PlaceItem(ItemType.Dynamite, new Vector3(31.3f, 0.795f, 5.3f), Quaternion.Euler(90f, 40f, 0f));
            for (int i = 0; i < 3; i++)
                Draw(Cell(new Vector3(35f, 0f, -4f)), mRust, Matrix4x4.identity, b => b.Cylinder(new Vector3(35.2f, 0f, -4.8f + i * 0.7f), new Vector3(35.2f, 0.9f, -4.8f + i * 0.7f), 0.29f, 0.29f, 14));
            patrol.Add(Point("Patrol_garage", new Vector3(29f, 0f, 3f)));
        }

        static void Basement()
        {
            float y = BY;
            Crate(new Vector3(-13.2f, y, -11.3f), 0.8f, false);
            Crate(new Vector3(-12.3f, y, -11.4f), 0.6f, true, 4);
            Crate(new Vector3(-6f, y, -3.8f), 0.7f, false);
            Shelf(new Vector3(-9f, y, -11.75f), 180f, 2.4f, 2f, 3, false, 0);
            Bucket(new Vector3(-7.5f, y, -11.2f));
            for (int i = 0; i < 2; i++) SBox(mRust, new Vector3(-8.6f, -0.55f - i * 0.18f, -9.5f - i * 0.4f), new Vector3(10.6f, 0.12f, 0.12f), false);
            // the torch on its bracket
            SBox(mMetalDark, new Vector3(-13.86f, y + 1.35f, -9f), new Vector3(0.08f, 0.06f, 0.06f), false);
            PlaceItem(ItemType.Torch, new Vector3(-13.75f, y + 1.45f, -9f), Quaternion.Euler(0f, 0f, -15f));
            // rubble in the doorway to the boiler room
            GameObject rub = Obj("Rubble", null, new Vector3(-4f, y, -8f), Quaternion.identity);
            rub.layer = LayerProp;   // kept out of the navmesh bake; the carving obstacle blocks her instead
            GameObject rocks = new GameObject("Rocks");
            rocks.transform.SetParent(rub.transform, false);
            var rnd = new System.Random(3);
            Part(rocks.transform, "Rocks", mRock, b =>
            {
                for (int i = 0; i < 16; i++)
                {
                    Vector3 c = new Vector3(((float)rnd.NextDouble() - 0.5f) * 1.2f, 0.25f + (float)rnd.NextDouble() * 1.6f * (1f - i / 20f), ((float)rnd.NextDouble() - 0.5f) * 1.9f);
                    float r = 0.25f + (float)rnd.NextDouble() * 0.3f;
                    int seed = i;
                    b.Sphere(c, new Vector3(r, r * 0.8f, r), 8, 6, d => 0.8f + 0.35f * Mathf.PerlinNoise(d.x * 3f + seed, d.z * 3f + d.y));
                }
                b.Box(new Vector3(0.1f, 1.9f, 0.2f), new Vector3(0.12f, 0.12f, 1.9f));
            });
            var rbc = rub.AddComponent<BoxCollider>();
            rbc.center = new Vector3(0f, 1.2f, 0f);
            rbc.size = new Vector3(1.4f, 2.4f, 1.9f);
            Rubble ru = rub.AddComponent<Rubble>();
            ru.rocks = rocks;
            ru.blocker = rbc;
            NavMeshObstacle rob = rub.AddComponent<NavMeshObstacle>();
            rob.shape = NavMeshObstacleShape.Box;
            rob.center = new Vector3(0f, 1f, 0f);
            rob.size = new Vector3(1.6f, 2f, 2f);
            rob.carving = true;
            ru.obstacle = rob;
            GameObject dyn = new GameObject("PlacedDynamite");
            dyn.transform.SetParent(rub.transform, false);
            dyn.transform.localPosition = new Vector3(-0.75f, 0.12f, 0f);
            dyn.transform.localRotation = Quaternion.Euler(0f, 0f, 70f);
            ItemMesh(ItemType.Dynamite, dyn.transform, false);
            dyn.SetActive(false);
            ru.placedDynamite = dyn;
            ru.fuseSparks = Particles(rub.transform, "FuseSparks", new Vector3(-0.72f, 0.3f, 0f), mSpark, false, 40f, 0.4f, 1.2f, 0.06f,
                new Color(1f, 0.85f, 0.4f, 1f), new Color(1f, 0.4f, 0.1f, 0.6f), 40f, 0.02f, 0.5f, 60);
            ru.dust = BurstOnce(Particles(rub.transform, "Dust", new Vector3(0f, 1f, 0f), mDust, false, 0f, 3f, 3f, 1.6f,
                new Color(0.55f, 0.5f, 0.45f, 0.6f), new Color(0.4f, 0.38f, 0.35f, 0f), 70f, 0.8f, 0.1f, 80), 60);
            Light fl = PointLight(rub.transform, rub.transform.position + new Vector3(-1f, 1.2f, 0f), new Color(1f, 0.7f, 0.4f), 0f, 12f, "Flash");
            fl.enabled = false;
            ru.flash = fl;
            // boiler room: the boiler and the small key
            Draw(Cell(new Vector3(1f, y + 1f, -10.6f)), mRust, Matrix4x4.identity, b =>
            {
                b.Cylinder(new Vector3(1f, y, -10.8f), new Vector3(1f, y + 2.3f, -10.8f), 0.85f, 0.85f, 20);
                b.Cylinder(new Vector3(1f, y + 2.3f, -10.8f), new Vector3(1f, -0.35f, -10.8f), 0.18f, 0.18f, 10, false);
                b.Cylinder(new Vector3(1.8f, y + 1.6f, -10.8f), new Vector3(5.8f, y + 1.6f, -10.8f), 0.1f, 0.1f, 8);
            });
            Draw(Cell(new Vector3(1f, y + 0.6f, -9.9f)), mLed, Matrix4x4.identity, b => b.Box(new Vector3(1f, y + 0.55f, -9.93f), new Vector3(0.5f, 0.3f, 0.02f)));
            Table(new Vector3(4.2f, y, -5.2f), 0f, 1.2f, 0.7f, mWoodDark);
            PlaceItem(ItemType.SafeKey, new Vector3(4.1f, y + 0.785f, -5.2f), Quaternion.Euler(0f, 70f, 0f));
            GameObject scare = Trigger("Scare_basement", new Vector3(-11.5f, y + 1f, -8.6f), new Vector3(1.6f, 2f, 1f));
            ScareTrigger sc = scare.AddComponent<ScareTrigger>();
            sc.kind = ScareKind.Sound;
            sc.soundPoint = Point("LaughPoint", new Vector3(3f, y + 1.5f, -9f));
            sc.clip = Clip("teacher_laugh");
            BugPatch(new Vector3(-8f, y + 0.02f, -9.5f), Quaternion.Euler(90f, 0f, 0f), 8, new Vector2(2f, 1.6f));
        }

        static void SecretRoom()
        {
            GameObject shelf = Obj("SecretShelf", null, new Vector3(-9f, 0f, 11.78f), Quaternion.identity);
            Part(shelf.transform, "Frame", mWoodDark, b =>
            {
                b.Box(new Vector3(-0.7f, 1.1f, 0f), new Vector3(0.04f, 2.2f, 0.36f));
                b.Box(new Vector3(0.7f, 1.1f, 0f), new Vector3(0.04f, 2.2f, 0.36f));
                b.Box(new Vector3(0f, 1.1f, 0.17f), new Vector3(1.4f, 2.2f, 0.02f));
                for (int r = 0; r <= 4; r++) b.Box(new Vector3(0f, 0.05f + r * 0.53f, 0f), new Vector3(1.4f, 0.03f, 0.36f));
            });
            var rnd = new System.Random(9);
            Material[] bm = { mBook1, mBook2, mBook3 };
            for (int r = 0; r < 4; r++)
            {
                Material m = bm[r % 3];
                float yy = 0.08f + r * 0.53f;
                Part(shelf.transform, "Books" + r, m, b =>
                {
                    float x = -0.66f;
                    while (x < 0.62f)
                    {
                        float bw = 0.035f + (float)rnd.NextDouble() * 0.03f, bh = 0.22f + (float)rnd.NextDouble() * 0.1f;
                        b.Box(new Vector3(x + bw * 0.5f, yy + bh * 0.5f, -0.02f), new Vector3(bw, bh, 0.24f));
                        x += bw + 0.005f;
                    }
                });
            }
            var sbc = shelf.AddComponent<BoxCollider>();
            sbc.center = new Vector3(0f, 1.1f, 0f);
            sbc.size = new Vector3(1.42f, 2.2f, 0.38f);
            shelf.AddComponent<SecretShelf>().slide = new Vector3(-1.3f, 0f, 0f);
            // inside: trophy + message
            Draw(Cell(new Vector3(-9f, 0.5f, 14f)), mWoodDark, Matrix4x4.identity, b => b.Box(new Vector3(-9f, 0.5f, 14.3f), new Vector3(0.6f, 1f, 0.5f)));
            Draw(Cell(new Vector3(-9f, 1.2f, 14f)), mGold, Matrix4x4.identity, b =>
            {
                b.Cylinder(new Vector3(-9f, 1f, 14.3f), new Vector3(-9f, 1.08f, 14.3f), 0.1f, 0.1f, 14);
                b.Cylinder(new Vector3(-9f, 1.08f, 14.3f), new Vector3(-9f, 1.3f, 14.3f), 0.03f, 0.03f, 10);
                b.Cylinder(new Vector3(-9f, 1.3f, 14.3f), new Vector3(-9f, 1.55f, 14.3f), 0.06f, 0.16f, 16);
            });
            Draw(Cell(new Vector3(-9f, 1.8f, 14.9f)), NCMats.Picture("secret_board", "secret_board", Color.white, 0.25f), Matrix4x4.TRS(new Vector3(-9f, 1.9f, 14.88f), Quaternion.identity, Vector3.one),
                b => b.Panel(Vector3.zero, new Vector3(2.4f, 0.9f, 0.01f)));
        }

        static void Corridor()
        {
            // lockers along the walls (some you can hide in)
            float[] hideNorth = { -11f, 3f, 12f };
            foreach (float x in hideNorth) HideCabinet(new Vector3(x, 0f, 1.68f), 0f, false);
            float[] hideSouth = { -21f, -6.5f, 15f };
            foreach (float x in hideSouth) HideCabinet(new Vector3(x, 0f, -1.68f), 180f, false);
            for (int i = 0; i < 8; i++)
            {
                float x = -13.4f + i * 0.56f;
                if (Mathf.Abs(x + 11f) < 0.5f) continue;
                SBox(mMetalGreen, new Vector3(x, 0.97f, 1.73f), new Vector3(0.54f, 1.94f, 0.48f));
            }
            for (int i = 0; i < 6; i++) SBox(mMetalGreen, new Vector3(16.1f + i * 0.56f, 0.97f, -1.73f), new Vector3(0.54f, 1.94f, 0.48f));
            float[] posterX = { -32.5f, -22.5f, -19f, -8.2f, 9.5f, 20f };
            for (int i = 0; i < posterX.Length; i++) Poster(new Vector3(posterX[i], 1.75f, 1.88f), 0f, i);
            Clock(new Vector3(-2f, 2.99f, -1.88f), 180f);
            GameObject info = Trigger("Info_hide", new Vector3(-11f, 1f, 0.6f), new Vector3(2f, 2f, 1.4f));
            info.AddComponent<InfoZone>().text = "Lockers! Stand in front of one and tap HIDE when she's coming.";

            // fire barrier in the west corridor + sprinklers
            GameObject fire = Obj("FireBarrier", null, new Vector3(-25f, 0f, 0f), Quaternion.identity);
            FireBarrier fb = fire.AddComponent<FireBarrier>();
            var flames = new List<ParticleSystem>();
            foreach (float z in new[] { -1.4f, -0.45f, 0.5f, 1.4f }) flames.Add(Fire(fire.transform, new Vector3(0f, 0.1f, z), 1.4f));
            fb.flames = flames.ToArray();
            Smoke(fire.transform, new Vector3(0f, 1.5f, 0f), 1.5f);
            fb.steam = BurstOnce(Particles(fire.transform, "Steam", new Vector3(0f, 0.5f, 0f), mSmoke, false, 0f, 3f, 1.5f, 1.4f,
                new Color(0.75f, 0.78f, 0.8f, 0.5f), new Color(0.6f, 0.6f, 0.62f, 0f), 50f, 1.4f, -0.1f, 80), 70);
            fb.fireLight = PointLight(fire.transform, new Vector3(-25f, 1.2f, 0f), new Color(1f, 0.5f, 0.2f), 3f, 8f, "FireLight");
            GameObject blk = new GameObject("Blocker");
            blk.transform.SetParent(fire.transform, false);
            blk.layer = LayerProp;   // blocks the player; kept out of the navmesh bake (the obstacle blocks her)
            var bbc = blk.AddComponent<BoxCollider>();
            bbc.center = new Vector3(0f, 1.2f, 0f);
            bbc.size = new Vector3(0.6f, 2.4f, 4f);
            fb.blocker = bbc;
            var tbc = fire.AddComponent<BoxCollider>();
            tbc.isTrigger = true;
            tbc.center = new Vector3(1f, 1f, 0f);
            tbc.size = new Vector3(2f, 2f, 4f);
            fire.layer = LayerTrigger;
            NavMeshObstacle fob = blk.AddComponent<NavMeshObstacle>();
            fob.shape = NavMeshObstacleShape.Box;
            fob.size = new Vector3(1.2f, 2f, 4.2f);
            fob.center = new Vector3(0f, 1f, 0f);
            fob.carving = true;
            fb.obstacle = fob;
            // charred debris
            SBox(mWoodDark, new Vector3(-25.2f, 0.2f, -0.8f), new Vector3(1.2f, 0.4f, 0.6f), false);
            SBox(mWoodDark, new Vector3(-24.8f, 0.15f, 0.9f), new Vector3(0.9f, 0.3f, 0.7f), false);
            var spr = new List<ParticleSystem>();
            foreach (float x in new[] { -26f, -24f })
            {
                SBox(mMetalDark, new Vector3(x, H - 0.05f, 0f), new Vector3(0.08f, 0.08f, 0.08f), false);
                ParticleSystem s = Particles(fire.transform, "Sprinkler", new Vector3(x + 25f, H - 0.1f, 0f), mWater, false, 120f, 1.2f, 2.5f, 0.06f,
                    new Color(0.7f, 0.8f, 0.95f, 0.7f), new Color(0.6f, 0.7f, 0.9f, 0.3f), 60f, 0.05f, 1f, 300);
                s.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
                spr.Add(s);
            }
            if (waterValve != null)
            {
                waterValve.sprinklers = spr.ToArray();
                waterValve.fire = fb;
            }
            // scares
            GameObject pop = Trigger("Scare_lamp", new Vector3(-2.5f, 1f, 0f), new Vector3(1f, 2f, 4f));
            ScareTrigger ps = pop.AddComponent<ScareTrigger>();
            ps.kind = ScareKind.LampPop;
            ps.sparks = BurstOnce(Particles(pop.transform, "Sparks", new Vector3(2.5f, H - 1.4f, 0f), mSpark, false, 0f, 0.6f, 3f, 0.05f,
                new Color(1f, 0.9f, 0.6f, 1f), new Color(1f, 0.5f, 0.2f, 0.5f), 60f, 0.1f, 1.5f, 60), 40);
            foreach (FlickerLight fl in lightRoot.GetComponentsInChildren<FlickerLight>(true))
                if (Vector3.Distance(fl.transform.position, new Vector3(0f, H, 0f)) < 0.5f) ps.lamp = fl;
            if (ps.lamp == null)
            {
                Transform lampAt0 = null;
                foreach (Transform t in lightRoot)
                    if (t.name == "Lamp" && Vector3.Distance(t.position, new Vector3(0f, H - 0.02f, 0f)) < 0.3f) lampAt0 = t;
                if (lampAt0 != null)
                {
                    FlickerLight f = lampAt0.gameObject.AddComponent<FlickerLight>();
                    f.lamp = lampAt0.GetComponentInChildren<Light>();
                    MeshRenderer[] mrs = lampAt0.GetComponentsInChildren<MeshRenderer>();
                    if (mrs.Length > 1) f.tube = mrs[1];
                    ps.lamp = f;
                }
            }
            foreach (float x in new[] { -30f, -20f, -8f, 4f, 14f, 22f }) patrol.Add(Point("Patrol_corridor" + x, new Vector3(x, 0f, 0f)));
        }

        static GameObject BugPatch(Vector3 center, Quaternion rot, int n, Vector2 area)
        {
            GameObject go = Obj("Bugs", logicRoot, center, rot);
            var list = new List<Transform>();
            for (int i = 0; i < n; i++)
            {
                GameObject bug = new GameObject("Bug" + i);
                bug.transform.SetParent(go.transform, false);
                Part(bug.transform, "Q", mBug, b => b.Panel(new Vector3(0f, 0f, -0.004f), new Vector3(0.05f, 0.07f, 0.001f)));
                list.Add(bug.transform);
            }
            Bugs bg = go.AddComponent<Bugs>();
            bg.bugs = list.ToArray();
            bg.area = area;
            return go;
        }

        static void LogicPoints()
        {
            menuCam.Add(Point("Menu_0", new Vector3(-30f, 1.75f, 0.2f), 90f, 4f));
            menuCam.Add(Point("Menu_1", new Vector3(-9f, 1.8f, 0.6f), 120f, 6f));
            menuCam.Add(Point("Menu_2", new Vector3(-2f, 2.4f, -3f), 180f, 14f));
            menuCam.Add(Point("Menu_3", new Vector3(6f, 3f, -3.5f), 140f, 16f));
            menuCam.Add(Point("Menu_4", new Vector3(18f, 1.75f, 0f), -90f, 4f));
            menuCam.Add(Point("Menu_5", new Vector3(-7f, 1.9f, 3.2f), -60f, 10f));
            Point("Tour_corridor", new Vector3(-12f, 0.05f, 0f), 90f, 4f);
            Point("Tour_lounge", new Vector3(-2.8f, 0.05f, 3.4f), 50f, 6f);
            Point("Tour_toilets", new Vector3(15.2f, 0.05f, 3f), 40f, 4f);
            Point("Tour_fire", new Vector3(-20.5f, 0.05f, 0.3f), -90f, 2f);
            Point("Tour_entrance", new Vector3(-2f, 0.05f, -3.2f), 180f, 4f);
            Point("Tour_gym", new Vector3(5.6f, 0.05f, -3f), 135f, 8f);
            Point("Tour_cafeteria", new Vector3(-15.6f, 0.05f, -3.1f), -130f, 6f);
            Point("Tour_janitor", new Vector3(-8.8f, 0.05f, -2.8f), -125f, 20f);
            Point("Tour_garage", new Vector3(27f, 0.05f, 0.5f), 112f, 6f);
            Point("Tour_office", new Vector3(-25f, 0.05f, 3f), -57f, 8f);
            Point("Tour_basement", new Vector3(-11f, BY + 0.05f, -8.2f), 90f, 4f);
            Point("Tour_boiler", new Vector3(-2.8f, BY + 0.05f, -5.4f), 145f, 6f);
        }
    }
}
