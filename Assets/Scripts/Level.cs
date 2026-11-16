using System;
using System.Collections.Generic;
using UnityEngine;

namespace Moulika
{
    /// <summary>
    /// The school: the Blender-built model (Resources/School.prefab, made from the same school.glb as the Godot
    /// version, with photo textures and the baked lightmaps already on it), plus everything school_meta.json
    /// describes: collisions, doors, items, hiding places, the walk grid Moulika uses and the lamps that light her.
    /// Port of game/scripts/level.gd.
    /// </summary>
    public class Level : MonoBehaviour
    {
        public class Leaf { public Transform node; public Quaternion rest; public float deg; }

        public class Door
        {
            public string name, kind, o, room, lockId;
            public Vector3 pos;
            public bool open;
            public float t, target, w;
            public BoxCollider shape;
            public readonly List<Leaf> leaves = new List<Leaf>();
            public bool Locked { get { return !string.IsNullOrEmpty(lockId); } }
        }

        public class Item
        {
            public string id, label;
            public Transform node;
            public bool held;
            public Vector3 home;
            public Renderer[] rends;
        }

        public class Hide
        {
            public Vector3 pos, front;
            public float t, target;
        }

        public class Plank
        {
            public Transform node;
            public Vector3 pos;
            public bool gone;
            public int hits;
        }

        public class Target
        {
            public string kind, label;
            public Vector3 pos;
            public object obj;
            public float r;
        }

        public struct Lamp { public Vector3 pos; public Color color; }

        public const int WallMask = 1;            // Default layer: walls, floors, furniture, closed doors
        public event Action<Vector3, float> Noise;

        public object meta;
        public Transform model;
        public readonly Dictionary<string, Transform> nodes = new Dictionary<string, Transform>();
        public readonly Dictionary<string, Door> doors = new Dictionary<string, Door>();
        public readonly Dictionary<string, Item> items = new Dictionary<string, Item>();
        public readonly List<Hide> hides = new List<Hide>();
        public readonly List<Plank> planks = new List<Plank>();
        public readonly List<Transform> padlockNodes = new List<Transform>();
        public readonly List<Transform> rotors = new List<Transform>();
        public readonly List<Lamp> lamps = new List<Lamp>();
        public int planksLeft;
        public GameAudio sound;

        // walk grid (meta "grid": cells of 0.4 m over the Blender XY plane = Unity XZ)
        bool[] solid;
        int gnx, gny;
        float gx0, gy0, gcell = 0.4f;
        MaterialPropertyBlock mpb;

        public static object LoadMeta()
        {
            var ta = Resources.Load<TextAsset>("school_meta");
            return ta != null ? Json.Parse(ta.text) : null;
        }

        // ---------------------------------------------------------------------------------------- light of a room
        /// <summary>Brightness of a room from its baked lightmap's mean (level.gd room_light).</summary>
        public static Dictionary<string, float> RoomLights(object meta)
        {
            var res = new Dictionary<string, float>();
            var lms = Json.O(meta, "lightmaps");
            foreach (object r in Json.A(meta, "rooms"))
            {
                string name = Json.S(r, "name");
                object e = lms != null ? Json.Get(lms, "arch_" + name) : null;
                res[name] = Mathf.Clamp(e != null ? Json.F(e, "mean") * 3.2f : 0.1f, 0.05f, 0.6f);
            }
            return res;
        }

        /// <summary>Light used where there is no lightmap: that of the room containing p (Unity space).</summary>
        public static float LightAt(object meta, Dictionary<string, float> roomLight, Vector3 p)
        {
            foreach (object r in Json.A(meta, "rooms"))
            {
                object rc = Json.Get(r, "rect");
                if (p.x >= Json.At(rc, 0) && p.x <= Json.At(rc, 2) && p.z >= Json.At(rc, 1) && p.z <= Json.At(rc, 3))
                {
                    float v;
                    return roomLight.TryGetValue(Json.S(r, "name"), out v) ? v : 0.12f;
                }
            }
            return 0.12f;
        }

        Dictionary<string, float> roomLight;

        public float LightAt(Vector3 p)
        {
            return LightAt(meta, roomLight, p);
        }

        // ---------------------------------------------------------------------------------------- build
        public bool Build()
        {
            meta = LoadMeta();
            if (meta == null) { Debug.LogError("[MOULIKA] school_meta.json missing"); return false; }
            var prefab = Resources.Load<GameObject>("School");
            if (prefab == null) { Debug.LogError("[MOULIKA] School prefab missing"); return false; }
            model = Instantiate(prefab, transform).transform;
            model.name = "School";
            foreach (Transform c in model) nodes[c.name] = c;
            roomLight = RoomLights(meta);
            mpb = new MaterialPropertyBlock();
            BuildColliders();
            BuildDoors();
            BuildItems();
            BuildHides();
            BuildGrid();
            BuildLamps();
            foreach (object d in Json.A(meta, "dynamic"))
                if (Json.S(d, "part") == "rotor" && nodes.ContainsKey(Json.S(d, "name")))
                    rotors.Add(nodes[Json.S(d, "name")]);
            return true;
        }

        void BuildColliders()
        {
            var walls = new GameObject("Walls");
            walls.transform.SetParent(transform, false);
            var floor = new GameObject("Floor");
            floor.transform.SetParent(walls.transform, false);
            floor.transform.localPosition = new Vector3(0f, -0.5f, 0f);
            floor.AddComponent<BoxCollider>().size = new Vector3(120f, 1f, 120f);
            int i = 0;
            foreach (object c in Json.A(meta, "colliders"))
            {
                var go = new GameObject("Wall " + i++);
                go.transform.SetParent(walls.transform, false);
                go.transform.localPosition = new Vector3(Json.At(c, 0), Json.At(c, 1), -Json.At(c, 2));
                go.transform.localRotation = Quaternion.Euler(0f, -Json.At(c, 6) * Mathf.Rad2Deg, 0f);
                go.AddComponent<BoxCollider>().size = new Vector3(Json.At(c, 3), Json.At(c, 4), Json.At(c, 5));
            }
        }

        void BuildDoors()
        {
            foreach (object d in Json.A(meta, "doors"))
            {
                if (Json.S(d, "kind") == "arch") continue;
                float h = Json.F(d, "h");
                var door = new Door
                {
                    name = Json.S(d, "name"),
                    pos = Json.GV(Json.Get(d, "pos")) + new Vector3(0f, 1.15f, 0f),
                    lockId = Json.Get(d, "lock") as string,
                    kind = Json.S(d, "kind"),
                    w = Json.F(d, "w"),
                    o = Json.S(d, "o"),
                    room = Json.S(d, "room"),
                };
                var go = new GameObject("Door " + door.name);
                go.transform.SetParent(transform, false);
                go.transform.localPosition = Json.GV(Json.Get(d, "pos")) + new Vector3(0f, h / 2f, 0f);
                var box = go.AddComponent<BoxCollider>();
                box.size = door.o == "h" ? new Vector3(door.w, h, 0.12f) : new Vector3(0.12f, h, door.w);
                door.shape = box;
                doors[door.name] = door;
            }
            foreach (object dy in Json.A(meta, "dynamic"))
            {
                string name = Json.S(dy, "name");
                if (!nodes.ContainsKey(name)) continue;
                if (Json.Has(dy, "door") && doors.ContainsKey(Json.S(dy, "door")))
                {
                    object into = Json.Get(dy, "into");
                    int leaf = Json.I(dy, "leaf");
                    float deg = Json.S(dy, "o") == "h"
                        ? 96f * Json.At(into, 1) * (leaf == 0 ? 1f : -1f)
                        : -96f * Json.At(into, 0) * (leaf == 0 ? 1f : -1f);
                    Transform n = nodes[name];
                    doors[Json.S(dy, "door")].leaves.Add(new Leaf { node = n, rest = n.localRotation, deg = deg });
                }
                else if (Json.Has(dy, "plank"))
                    planks.Add(new Plank { node = nodes[name], pos = Json.GV(Json.Get(dy, "pivot")) });
                else if (Json.Has(dy, "lock"))
                    padlockNodes.Add(nodes[name]);
            }
            planksLeft = planks.Count;
        }

        public static string DoorLabel(Door d)
        {
            if (d.lockId == "main") return "";
            if (d.Locked) return "Locked";
            return d.open ? "Close" : "Open";
        }

        public void ToggleDoor(Door d, bool byMoulika = false)
        {
            if (d.Locked && !byMoulika) return;
            d.open = !d.open;
            d.target = d.open ? 1f : 0f;
            d.shape.enabled = !d.open;
            if (sound != null) sound.Play3D(d.open ? "door_open" : "door_close", d.pos, -11f);
            if (!byMoulika) EmitNoise(d.pos, 7f);
        }

        public void OpenMain()
        {
            Door d = doors["door_main"];
            d.lockId = null;
            d.open = true;
            d.target = 1f;
            d.shape.enabled = false;
            if (sound != null) sound.Play3D("door_open", d.pos, -7f);
        }

        public void EmitNoise(Vector3 p, float radius)
        {
            if (Noise != null) Noise(p, radius);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            foreach (Door d in doors.Values)
            {
                if (d.t == d.target) continue;
                d.t = Mathf.MoveTowards(d.t, d.target, dt * 1.8f);
                float e = Mathf.SmoothStep(0f, 1f, d.t);
                foreach (Leaf lf in d.leaves)
                    lf.node.localRotation = lf.rest * Quaternion.Euler(0f, -lf.deg * e, 0f);
            }
            foreach (Transform r in rotors)
                r.Rotate(0f, -dt * 2.2f * Mathf.Rad2Deg, 0f, Space.Self);
        }

        // ---------------------------------------------------------------------------------------- items
        static readonly Dictionary<string, string> ItemNodes = new Dictionary<string, string>
        {
            { "hammer", "item_hammer" }, { "main_key", "item_main_key" }, { "office_key", "item_office_key" }, { "store_key", "item_store_key" },
        };

        public static string Capitalize(string s)
        {
            // Godot String.capitalize: "MAIN DOOR KEY" -> "Main Door Key"
            var words = s.Replace('_', ' ').ToLowerInvariant().Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
            for (int i = 0; i < words.Length; i++)
                words[i] = char.ToUpperInvariant(words[i][0]) + words[i].Substring(1);
            return string.Join(" ", words);
        }

        void BuildItems()
        {
            var its = Json.O(meta, "items");
            if (its == null) return;
            foreach (var kv in its)
            {
                string node;
                if (!ItemNodes.TryGetValue(kv.Key, out node) || !nodes.ContainsKey(node)) continue;
                Transform n = nodes[node];
                List<object> spots = Json.A(kv.Value, "spots");
                object sp = spots[UnityEngine.Random.Range(0, spots.Count)];
                n.localPosition = Json.GV(Json.Get(sp, "pos")) + new Vector3(0f, 0.02f, 0f);
                n.localRotation = Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 360f), 0f);
                var it = new Item { id = kv.Key, label = Capitalize(Json.S(kv.Value, "label")), node = n, home = n.localPosition, rends = n.GetComponentsInChildren<Renderer>(true) };
                items[kv.Key] = it;
                Relight(it);
            }
        }

        public void Relight(Item it, float v = -1f)
        {
            float l = v >= 0f ? v : Mathf.Max(LightAt(it.node.position), 0.16f) * 1.5f;
            foreach (Renderer r in it.rends)
            {
                r.GetPropertyBlock(mpb);
                mpb.SetVector("_FlatLight", new Vector4(l, l, l, 0f));
                r.SetPropertyBlock(mpb);
            }
        }

        void BuildHides()
        {
            foreach (object f in Json.A(meta, "furniture"))
            {
                if (Json.S(f, "kind") != "almirah") continue;
                float a = Json.F(f, "yaw") * Mathf.Deg2Rad;
                hides.Add(new Hide { pos = Json.GV(Json.Get(f, "pos")), front = new Vector3(Mathf.Sin(a), 0f, -Mathf.Cos(a)) });
            }
        }

        public void SetHideDoors(Hide h, float amount)
        {
            // the almirahs of this school have no separate door meshes; kept for parity with the Godot version
        }

        // ---------------------------------------------------------------------------------------- lamps (for Moulika's lighting)
        static Color Srgb(float r, float g, float b)
        {
            return new Color(r, g, b).linear;
        }

        void BuildLamps()
        {
            foreach (object lt in Json.A(meta, "lights"))
            {
                string kind = Json.S(lt, "kind");
                if (kind == "dead") continue;
                lamps.Add(new Lamp
                {
                    pos = Json.GV(Json.Get(lt, "pos")) - new Vector3(0f, 0.35f, 0f),
                    color = (kind == "tube" ? Srgb(0.85f, 0.92f, 1f) : Srgb(1f, 0.75f, 0.5f)) * 1.1f,
                });
            }
        }

        // ---------------------------------------------------------------------------------------- the walk grid
        void BuildGrid()
        {
            object g = Json.Get(meta, "grid");
            gcell = Json.F(g, "cell", 0.4f);
            gx0 = Json.F(g, "x0");
            gy0 = Json.F(g, "y0");
            gnx = Json.I(g, "nx");
            gny = Json.I(g, "ny");
            solid = new bool[gnx * gny];
            List<object> rows = Json.A(g, "rows");
            for (int j = 0; j < rows.Count && j < gny; j++)
            {
                string row = (string)rows[j];
                for (int i = 0; i < row.Length && i < gnx; i++)
                    solid[j * gnx + i] = row[i] == '#';
            }
        }

        bool Solid(int x, int y)
        {
            return x < 0 || y < 0 || x >= gnx || y >= gny || solid[y * gnx + x];
        }

        public Vector2Int CellOf(Vector3 p)
        {
            int x = Mathf.FloorToInt((p.x - gx0) / gcell), y = Mathf.FloorToInt((p.z - gy0) / gcell);
            return new Vector2Int(Mathf.Clamp(x, 0, gnx - 1), Mathf.Clamp(y, 0, gny - 1));
        }

        public Vector3 CellPos(Vector2Int c)
        {
            return new Vector3(gx0 + (c.x + 0.5f) * gcell, 0f, gy0 + (c.y + 0.5f) * gcell);
        }

        Vector2Int NearestFree(Vector2Int c)
        {
            if (!Solid(c.x, c.y)) return c;
            for (int r = 1; r < 8; r++)
                for (int dx = -r; dx <= r; dx++)
                    for (int dy = -r; dy <= r; dy++)
                    {
                        int x = c.x + dx, y = c.y + dy;
                        if (x >= 0 && y >= 0 && x < gnx && y < gny && !Solid(x, y)) return new Vector2Int(x, y);
                    }
            return c;
        }

        // A* over the grid; diagonal steps only where both neighbouring cells are free (AStarGrid2D ONLY_IF_NO_OBSTACLES)
        float[] gScore;
        int[] cameFrom;
        int[] heap;
        float[] fScore;
        int[] heapPos;
        int heapCount;
        static readonly int[] DX = { 1, -1, 0, 0, 1, 1, -1, -1 };
        static readonly int[] DY = { 0, 0, 1, -1, 1, -1, 1, -1 };

        public List<Vector3> FindPath(Vector3 from, Vector3 to)
        {
            var path = new List<Vector3>();
            if (solid == null) return path;
            Vector2Int a = NearestFree(CellOf(from)), b = NearestFree(CellOf(to));
            int n = gnx * gny;
            if (gScore == null || gScore.Length != n)
            {
                gScore = new float[n];
                fScore = new float[n];
                cameFrom = new int[n];
                heap = new int[n];
                heapPos = new int[n];
            }
            for (int i = 0; i < n; i++) { gScore[i] = float.MaxValue; cameFrom[i] = -1; heapPos[i] = -1; }
            int start = a.y * gnx + a.x, goal = b.y * gnx + b.x;
            if (Solid(a.x, a.y) || Solid(b.x, b.y)) return path;
            heapCount = 0;
            gScore[start] = 0f;
            fScore[start] = H(a.x, a.y, b);
            Push(start);
            bool found = false;
            while (heapCount > 0)
            {
                int cur = Pop();
                if (cur == goal) { found = true; break; }
                int cx = cur % gnx, cy = cur / gnx;
                for (int k = 0; k < 8; k++)
                {
                    int x = cx + DX[k], y = cy + DY[k];
                    if (Solid(x, y)) continue;
                    if (k >= 4 && (Solid(cx + DX[k], cy) || Solid(cx, cy + DY[k]))) continue;
                    int nb = y * gnx + x;
                    float ng = gScore[cur] + (k >= 4 ? 1.41421356f : 1f);
                    if (ng < gScore[nb])
                    {
                        gScore[nb] = ng;
                        cameFrom[nb] = cur;
                        fScore[nb] = ng + H(x, y, b);
                        if (heapPos[nb] < 0) Push(nb); else Up(heapPos[nb]);
                    }
                }
            }
            if (!found) return path;
            var cells = new List<int>();
            for (int c = goal; c != -1; c = cameFrom[c]) cells.Add(c);
            cells.Reverse();
            foreach (int c in cells) path.Add(CellPos(new Vector2Int(c % gnx, c / gnx)));
            return path;
        }

        static float H(int x, int y, Vector2Int b)
        {
            float dx = x - b.x, dy = y - b.y;
            return Mathf.Sqrt(dx * dx + dy * dy);
        }

        void Push(int v)
        {
            heap[heapCount] = v;
            heapPos[v] = heapCount;
            heapCount++;
            Up(heapCount - 1);
        }

        int Pop()
        {
            int top = heap[0];
            heapPos[top] = -2;
            heapCount--;
            if (heapCount > 0)
            {
                heap[0] = heap[heapCount];
                heapPos[heap[0]] = 0;
                Down(0);
            }
            return top;
        }

        void Up(int i)
        {
            while (i > 0)
            {
                int p = (i - 1) / 2;
                if (fScore[heap[i]] >= fScore[heap[p]]) break;
                Swap(i, p);
                i = p;
            }
        }

        void Down(int i)
        {
            while (true)
            {
                int l = i * 2 + 1, r = l + 1, m = i;
                if (l < heapCount && fScore[heap[l]] < fScore[heap[m]]) m = l;
                if (r < heapCount && fScore[heap[r]] < fScore[heap[m]]) m = r;
                if (m == i) break;
                Swap(i, m);
                i = m;
            }
        }

        void Swap(int i, int j)
        {
            int t = heap[i];
            heap[i] = heap[j];
            heap[j] = t;
            heapPos[heap[i]] = i;
            heapPos[heap[j]] = j;
        }

        // ---------------------------------------------------------------------------------------- what the player is looking at
        readonly Target found = new Target();
        float bestScore;

        void Consider(string kind, Vector3 pos, string label, object obj, float r, Vector3 camPos, Vector3 fwd)
        {
            Vector3 to = pos - camPos;
            float dist = to.magnitude;
            if (dist > r || dist < 0.05f) return;
            float dot = Vector3.Dot(fwd, to / dist);
            if (dot < (kind != "door" ? 0.9f : 0.8f)) return;
            float score = dot - dist * 0.03f + (kind == "item" ? 0.03f : 0f) + (kind == "plank" ? 0.02f : 0f);
            if (score <= bestScore) return;
            bestScore = score;
            found.kind = kind;
            found.pos = pos;
            found.label = label;
            found.obj = obj;
            found.r = r;
        }

        /// <summary>What the player is aiming at (level.gd target). The result is reused: read it straight away.</summary>
        public Target FindTarget(Vector3 camPos, Vector3 fwd)
        {
            bestScore = 0f;
            found.kind = null;
            foreach (Item it in items.Values)
                if (!it.held && it.node.gameObject.activeInHierarchy) Consider("item", it.node.position, it.label, it, 2.3f, camPos, fwd);
            foreach (Door d in doors.Values)
                if (d.lockId != "main") Consider("door", d.pos, DoorLabel(d), d, 2.4f, camPos, fwd);
            foreach (Hide h in hides)
                Consider("hide", h.pos + new Vector3(0f, 1.1f, 0f), "Hide", h, 2f, camPos, fwd);
            Door main;
            if (doors.TryGetValue("door_main", out main) && main.lockId == "main")
            {
                foreach (Plank p in planks)
                    if (!p.gone) Consider("plank", p.pos, "Planks", p, 2.3f, camPos, fwd);
                if (planksLeft == 0) Consider("padlock", main.pos, "Main Door Lock", null, 2.3f, camPos, fwd);
                else Consider("maindoor", main.pos + new Vector3(0f, -0.5f, 0f), "Main Door", null, 2f, camPos, fwd);
            }
            return found.kind != null ? found : null;
        }
    }
}
