using System;
using System.Collections.Generic;
using UnityEngine;

namespace TradersMadness
{
    /// <summary>
    /// The trader's house: the Blender-built model (Resources/House.prefab, with photo textures and the baked
    /// lightmaps already on it) plus everything house_meta.json describes: collisions, doors, items, hiding places,
    /// the main door's planks / padlocks / keypad, the safe, the locked drawer, the fuse box, the trading PC, the
    /// walk grid over both floors and the stair that the trader uses, and the lamps that light him.
    /// </summary>
    public class Level : MonoBehaviour
    {
        public class Leaf { public Transform node; public Quaternion rest; public float deg; }

        public class Door
        {
            public string name, kind, room, lockId, label;
            public int floor;
            public Vector3 pos;
            public bool open;
            public float t, target, w, h;
            public BoxCollider shape;
            public readonly List<Leaf> leaves = new List<Leaf>();
            public readonly List<int> cells = new List<int>();
            public bool Locked { get { return !string.IsNullOrEmpty(lockId); } }
        }

        public class Item
        {
            public string id, label;
            public Transform node, homeParent;
            public bool held, gone, found = true;
            public Vector3 home;
            public Quaternion homeRot;
            public Renderer[] rends;
        }

        public class Hide { public Vector3 pos, front; public float depth; public string room; }
        public class Plank { public Transform node; public Vector3 pos; public bool gone; }
        public class Padlock { public string id, key, label; public Transform node; public Vector3 pos; public bool gone; }
        public class Plant { public Vector3 pos; public bool searched, hasKey; }

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
        public GameAudio sound;
        public readonly Dictionary<string, Transform> nodes = new Dictionary<string, Transform>();
        public readonly Dictionary<string, Door> doors = new Dictionary<string, Door>();
        public readonly Dictionary<string, Item> items = new Dictionary<string, Item>();
        public readonly List<Hide> hides = new List<Hide>();
        public readonly List<Plank> planks = new List<Plank>();
        public readonly List<Padlock> padlocks = new List<Padlock>();
        public readonly List<Plant> plants = new List<Plant>();
        public readonly List<Lamp> lamps = new List<Lamp>();
        public int planksLeft;
        public bool power, codeSolved, safeOpen, drawerUnlocked, drawerOpen, fuseIn;
        public string doorCode = "000000", safeCode = "0000";
        public Vector3 trophyPos, pcPos, safePos, drawerPos, fuseboxPos, keypadPos, mainDoorPos;
        public float h1 = 3.3f;
        public Screens screens;

        Transform safeDoor, drawerTop, fuseboxDoor, keypadLed, ledStrip;
        Quaternion safeRest, fuseRest;
        Vector3 drawerRest, drawerDir = new Vector3(0f, 0f, -1f);
        float safeT, drawerT, drawerTarget, fuseT;
        readonly List<Renderer> screenRends = new List<Renderer>();
        readonly List<AltLightmap> alts = new List<AltLightmap>();
        readonly List<Material> glowMats = new List<Material>();
        Material keypadMat;
        MaterialPropertyBlock mpb;
        Dictionary<string, float> roomLight;

        public static object LoadMeta()
        {
            var ta = Resources.Load<TextAsset>("house_meta");
            return ta != null ? Json.Parse(ta.text) : null;
        }

        // ---------------------------------------------------------------------------------------- light of a room
        public static Dictionary<string, float> RoomLights(object meta, bool powerOn)
        {
            var res = new Dictionary<string, float>();
            var lms = Json.O(meta, "lightmaps");
            foreach (object r in Json.A(meta, "rooms"))
            {
                string name = Json.S(r, "name");
                object e = lms != null ? Json.Get(lms, "arch_" + name) : null;
                float mean = e != null ? Json.F(e, powerOn && Json.Has(e, "mean_on") ? "mean_on" : "mean") : 0.1f;
                res[name] = Mathf.Clamp(mean * 2.6f, 0.05f, 0.75f);
            }
            return res;
        }

        public static string RoomAt(object meta, Vector3 p)
        {
            foreach (object r in Json.A(meta, "rooms"))
            {
                object rc = Json.Get(r, "rect");
                float y = Json.F(r, "y");
                if (p.y < y - 0.6f || p.y > y + 3.0f) continue;
                if (p.x >= Json.At(rc, 0) && p.x <= Json.At(rc, 2) && p.z >= Json.At(rc, 1) && p.z <= Json.At(rc, 3))
                    return Json.S(r, "name");
            }
            return null;
        }

        public static float LightAt(object meta, Dictionary<string, float> roomLight, Vector3 p)
        {
            string rn = RoomAt(meta, p);
            float v;
            if (rn != null && roomLight.TryGetValue(rn, out v)) return v;
            return 0.08f;
        }

        public float LightAt(Vector3 p) { return LightAt(meta, roomLight, p); }

        // ---------------------------------------------------------------------------------------- build
        public bool Build()
        {
            meta = LoadMeta();
            if (meta == null) { Debug.LogError("[TM] house_meta.json missing"); return false; }
            var prefab = Resources.Load<GameObject>("House");
            if (prefab == null) { Debug.LogError("[TM] House prefab missing"); return false; }
            model = Instantiate(prefab, transform).transform;
            model.name = "House";
            foreach (Transform c in model) nodes[c.name] = c;
            h1 = Json.F(meta, "h1", 3.3f);
            mpb = new MaterialPropertyBlock();
            roomLight = RoomLights(meta, false);
            foreach (AltLightmap a in model.GetComponentsInChildren<AltLightmap>(true)) alts.Add(a);
            safeCode = UnityEngine.Random.Range(1000, 10000).ToString();
            doorCode = UnityEngine.Random.Range(100000, 1000000).ToString();
            BuildColliders();
            BuildGrid();
            BuildDoors();
            BuildProps();
            BuildItems();
            BuildHides();
            BuildLamps();
            SetPower(false, true);
            Debug.Log("[TM] house: " + nodes.Count + " objects, " + doors.Count + " doors, " + items.Count + " items, "
                      + hides.Count + " hiding places, safe " + safeCode + ", door " + doorCode);
            return true;
        }

        void BuildColliders()
        {
            var walls = new GameObject("Colliders");
            walls.transform.SetParent(transform, false);
            int i = 0;
            foreach (object c in Json.A(meta, "colliders"))
            {
                var go = new GameObject("Box " + i++);
                go.transform.SetParent(walls.transform, false);
                go.transform.localPosition = new Vector3(Json.At(c, 0), Json.At(c, 1), Json.At(c, 2));
                go.transform.localRotation = Quaternion.Euler(Json.At(c, 6), Json.At(c, 7), 0f);
                go.AddComponent<BoxCollider>().size = new Vector3(Mathf.Max(Json.At(c, 3), 0.01f), Mathf.Max(Json.At(c, 4), 0.01f), Mathf.Max(Json.At(c, 5), 0.01f));
            }
        }

        void BuildDoors()
        {
            foreach (object d in Json.A(meta, "doors"))
            {
                var door = new Door
                {
                    name = Json.S(d, "name"),
                    kind = Json.S(d, "kind"),
                    room = Json.S(d, "room"),
                    lockId = Json.Get(d, "lock") as string,
                    label = Json.S(d, "label"),
                    floor = Json.I(d, "floor"),
                    w = Json.F(d, "w"),
                    h = Json.F(d, "h"),
                };
                Vector3 p = Json.V3(d, "pos");
                door.pos = p + new Vector3(0f, 1.1f, 0f);
                var go = new GameObject("Door " + door.name);
                go.transform.SetParent(transform, false);
                go.transform.localPosition = p + new Vector3(0f, door.h / 2f, 0f);
                var box = go.AddComponent<BoxCollider>();
                box.size = Json.S(d, "axis") == "x" ? new Vector3(door.w, door.h, 0.14f) : new Vector3(0.14f, door.h, door.w);
                door.shape = box;
                if (door.Locked && door.lockId != "main")
                {
                    bool ax = Json.S(d, "axis") == "x";
                    for (float a = -door.w / 2f; a <= door.w / 2f + 0.01f; a += 0.2f)
                        for (float tt = -0.6f; tt <= 0.61f; tt += 0.2f)
                        {
                            Vector3 q = p + (ax ? new Vector3(a, 0f, tt) : new Vector3(tt, 0f, a));
                            int c = Idx(door.floor, Cx(q.x), Cz(q.z));
                            if (!door.cells.Contains(c)) door.cells.Add(c);
                        }
                    foreach (int c in door.cells) lockedCell[c] = true;
                }
                if (door.name == "door_main") mainDoorPos = door.pos;
                doors[door.name] = door;
            }
            foreach (object dy in Json.A(meta, "dynamic"))
            {
                string name = Json.S(dy, "name");
                Transform n;
                if (!nodes.TryGetValue(name, out n)) continue;
                if (Json.Has(dy, "door") && doors.ContainsKey(Json.S(dy, "door")))
                {
                    Vector3 ld = Json.V3(dy, "leaf_dir");
                    Vector3 into = Json.V3(dy, "into");
                    Vector3 r = Quaternion.Euler(0f, 90f, 0f) * ld;
                    float deg = (Vector3.Dot(r, into) > 0f ? 1f : -1f) * (Json.S(dy, "door") == "door_main" ? 100f : 95f);
                    doors[Json.S(dy, "door")].leaves.Add(new Leaf { node = n, rest = n.localRotation, deg = deg });
                    Relight(n);
                }
                else if (Json.Has(dy, "plank"))
                {
                    planks.Add(new Plank { node = n, pos = n.position });
                    Relight(n);
                }
                else if (Json.Has(dy, "padlock"))
                {
                    bool gold = name.Contains("gold");
                    var pl = new Padlock { id = name, key = gold ? "gold_key" : "silver_key", label = gold ? "Gold Padlock" : "Silver Padlock", node = n, pos = n.position + new Vector3(0f, 0.06f, 0f) };
                    padlocks.Add(pl);
                    Tint(n.GetComponentsInChildren<Renderer>(true), gold ? new Color(1.25f, 0.95f, 0.45f) : new Color(0.95f, 0.97f, 1.05f), gold ? 0f : 1f, LightAt(n.position) * 1.4f);
                }
            }
            planksLeft = planks.Count;
        }

        void BuildProps()
        {
            object pr = Json.Get(meta, "props");
            trophyPos = Json.V3(pr, "trophy");
            pcPos = Json.V3(pr, "pc");
            safePos = Json.V3(pr, "safe");
            drawerPos = Json.V3(pr, "drawer");
            fuseboxPos = Json.V3(pr, "fusebox");
            keypadPos = Json.V3(pr, "keypad");
            nodes.TryGetValue("safe_door", out safeDoor);
            nodes.TryGetValue("drawer_top", out drawerTop);
            nodes.TryGetValue("fusebox_door", out fuseboxDoor);
            nodes.TryGetValue("keypad_led", out keypadLed);
            nodes.TryGetValue("led_strip", out ledStrip);
            if (safeDoor != null) { safeRest = safeDoor.localRotation; Relight(safeDoor); }
            if (drawerTop != null) { drawerRest = drawerTop.localPosition; Relight(drawerTop); }
            foreach (object dy in Json.A(meta, "dynamic"))
                if (Json.S(dy, "name") == "drawer_top")
                {
                    float a = Json.F(dy, "yaw") * Mathf.Deg2Rad;       // Blender yaw: the front faces (sin, -cos)
                    drawerDir = new Vector3(Mathf.Sin(a), 0f, -Mathf.Cos(a));
                }
            if (fuseboxDoor != null) { fuseRest = fuseboxDoor.localRotation; Relight(fuseboxDoor); }
            screens = gameObject.AddComponent<Screens>();
            for (int k = 0; k < 6; k++)
            {
                Transform s;
                if (!nodes.TryGetValue("screen_" + k, out s)) continue;
                var r = s.GetComponent<Renderer>();
                if (r == null) continue;
                r.material.SetTexture("_MainTex", screens.Tex(k));
                screenRends.Add(r);
            }
            if (ledStrip != null)
            {
                var r = ledStrip.GetComponent<Renderer>();
                if (r != null) glowMats.Add(r.material);
            }
            if (keypadLed != null)
            {
                var r = keypadLed.GetComponent<Renderer>();
                if (r != null) keypadMat = r.material;
            }
            if (keypadMat != null)
            {
                keypadMat.SetColor("_Color", new Color(1f, 0.08f, 0.05f));
                keypadMat.SetFloat("_On", 1f);
                keypadMat.SetFloat("_Lines", 0f);
            }
            foreach (Door d in doors.Values)
                foreach (Leaf lf in d.leaves) Relight(lf.node);
        }

        static string Capitalize(string s)
        {
            var words = s.Replace('_', ' ').ToLowerInvariant().Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
            for (int i = 0; i < words.Length; i++) words[i] = char.ToUpperInvariant(words[i][0]) + words[i].Substring(1);
            return string.Join(" ", words);
        }

        void BuildItems()
        {
            var its = Json.O(meta, "items");
            if (its == null) return;
            foreach (var kv in its)
            {
                string node = Json.S(kv.Value, "object", "item_" + kv.Key);
                Transform n;
                if (!nodes.TryGetValue(node, out n)) continue;
                var it = new Item { id = kv.Key, label = Json.S(kv.Value, "label", Capitalize(kv.Key)), node = n, rends = n.GetComponentsInChildren<Renderer>(true) };
                List<object> spots = Json.A(kv.Value, "spots");
                if (spots == null || spots.Count == 0)
                {
                    it.found = false;            // the small key: in one of the plant pots
                    n.gameObject.SetActive(false);
                }
                else
                {
                    object sp = spots[UnityEngine.Random.Range(0, spots.Count)];
                    n.position = Json.V3(sp, "pos") + new Vector3(0f, 0.005f, 0f);
                    n.rotation = Quaternion.Euler(0f, it.id == "gold_key" || it.id == "silver_key" ? 90f : UnityEngine.Random.Range(0f, 360f), 0f);
                }
                if (it.id == "silver_key" && drawerTop != null) n.SetParent(drawerTop, true);   // slides out with the drawer
                it.home = n.position;
                it.homeRot = n.rotation;
                it.homeParent = n.parent;
                items[it.id] = it;
                Look(it);
            }
            // the small key goes into one of the plant pots
            List<object> pls = Json.A(meta, "plants");
            if (pls != null)
            {
                foreach (object p in pls) plants.Add(new Plant { pos = Json.V3(p, "pos") + new Vector3(0f, 0.55f, 0f) });
                if (plants.Count > 0) plants[UnityEngine.Random.Range(0, plants.Count)].hasKey = true;
            }
        }

        /// <summary>Colour and light of an item: keys tinted gold / silver, lit like the room it is in.</summary>
        public void Look(Item it, float light = -1f)
        {
            Color mul = Color.white;
            float gray = 0f;
            if (it.id == "gold_key") mul = new Color(1.3f, 1.0f, 0.45f);
            else if (it.id == "silver_key") { mul = new Color(1.0f, 1.02f, 1.08f); gray = 1f; }
            float l = light >= 0f ? light : Mathf.Max(LightAt(it.node.position), 0.18f) * 1.5f;
            Tint(it.rends, mul, gray, l);
        }

        void Tint(Renderer[] rends, Color mul, float gray, float light)
        {
            foreach (Renderer r in rends)
            {
                r.GetPropertyBlock(mpb);
                mpb.SetColor("_Mul", mul);
                mpb.SetFloat("_Gray", gray);
                mpb.SetVector("_FlatLight", new Vector4(light, light, light * 1.03f, 0f));
                r.SetPropertyBlock(mpb);
            }
        }

        void Relight(Transform n)
        {
            float l = Mathf.Max(LightAt(n.position + new Vector3(0f, 0.8f, 0f)), 0.1f) * 1.25f;
            foreach (Renderer r in n.GetComponentsInChildren<Renderer>(true))
            {
                r.GetPropertyBlock(mpb);
                mpb.SetVector("_FlatLight", new Vector4(l, l, l * 1.03f, 0f));
                r.SetPropertyBlock(mpb);
            }
        }

        void BuildHides()
        {
            foreach (object h in Json.A(meta, "hides"))
                hides.Add(new Hide { pos = Json.V3(h, "pos"), front = Json.V3(h, "front"), depth = Json.F(h, "depth", 0.6f), room = Json.S(h, "room") });
        }

        void BuildLamps()
        {
            lamps.Clear();
            foreach (object lt in Json.A(meta, "lights")) AddLamp(lt);
            if (power)
                foreach (object lt in Json.A(meta, "trading_lights")) AddLamp(lt);
        }

        void AddLamp(object lt)
        {
            object c = Json.Get(lt, "color");
            float e = Mathf.Clamp(Json.F(lt, "energy", 20f) / 20f, 0.4f, 2f);
            lamps.Add(new Lamp
            {
                pos = Json.V3(lt, "pos") - new Vector3(0f, 0.3f, 0f),
                color = new Color(Json.At(c, 0), Json.At(c, 1), Json.At(c, 2)).linear * 1.2f * e,
            });
        }

        // ---------------------------------------------------------------------------------------- power, doors, puzzles
        public void SetPower(bool on, bool initial = false)
        {
            power = on;
            foreach (AltLightmap a in alts) a.Apply(on, mpb);
            foreach (Renderer r in screenRends) r.material.SetFloat("_On", on ? 1f : 0f);
            foreach (Material m in glowMats) m.SetFloat("_On", on ? 1f : 0f);
            if (screens != null) screens.running = on;
            roomLight = RoomLights(meta, on);
            BuildLamps();
            if (!initial && sound != null) sound.Play3D("power_on", fuseboxPos, 0f);
        }

        public static string DoorLabel(Door d)
        {
            if (d.lockId == "main") return "";
            if (d.Locked) return d.label + " (Locked)";
            return d.open ? "Close Door" : "Open Door";
        }

        public void ToggleDoor(Door d, bool byTrader = false)
        {
            if (d.Locked) return;
            d.open = !d.open;
            d.target = d.open ? 1f : 0f;
            d.shape.enabled = !d.open;
            if (sound != null) sound.Play3D(d.open ? "door_open" : "door_close", d.pos, byTrader ? -12f : -9f);
            if (!byTrader) EmitNoise(d.pos, 6f);
        }

        public void Unlock(Door d)
        {
            d.lockId = null;
            foreach (int c in d.cells) lockedCell[c] = false;
            if (sound != null) sound.Play3D("unlock", d.pos, 0f);
            EmitNoise(d.pos, 6f);
        }

        public void OpenMain()
        {
            Door d;
            if (!doors.TryGetValue("door_main", out d)) return;
            d.lockId = null;
            d.open = true;
            d.target = 1f;
            d.shape.enabled = false;
            if (sound != null) sound.Play3D("door_open", d.pos, -3f);
        }

        public void SetKeypadSolved()
        {
            codeSolved = true;
            if (keypadMat != null) keypadMat.SetColor("_Color", new Color(0.1f, 1f, 0.35f));
        }

        public void OpenSafe()
        {
            safeOpen = true;
            if (sound != null) sound.Play3D("safe_open", safePos, 0f);
        }

        public void SetDrawer(bool open)
        {
            drawerOpen = open;
            drawerTarget = open ? 1f : 0f;
            if (sound != null) sound.Play3D("drawer", drawerPos, -2f);
        }

        public void InsertFuse()
        {
            fuseIn = true;
            if (sound != null) sound.Play3D("switch", fuseboxPos, 0f);
        }

        public bool AllBarriersGone()
        {
            if (planksLeft > 0 || !codeSolved) return false;
            foreach (Padlock p in padlocks) if (!p.gone) return false;
            return true;
        }

        public string DoorStatus()
        {
            int pads = 0;
            foreach (Padlock p in padlocks) if (!p.gone) pads++;
            string ok = "<color=#22F07F>", bad = "<color=#FA2E3C>", end = "</color>";
            return "MAIN DOOR\n"
                   + (planksLeft > 0 ? bad : ok) + "PLANKS   " + planksLeft + "/3" + end + "\n"
                   + (pads > 0 ? bad : ok) + "PADLOCKS " + pads + "/2" + end + "\n"
                   + (codeSolved ? ok + "CODE     OK" : bad + "CODE     LOCKED") + end;
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
                    lf.node.localRotation = lf.rest * Quaternion.Euler(0f, lf.deg * e, 0f);
            }
            if (safeDoor != null && safeOpen && safeT < 1f)
            {
                safeT = Mathf.MoveTowards(safeT, 1f, dt * 1.2f);
                safeDoor.localRotation = safeRest * Quaternion.Euler(0f, 105f * Mathf.SmoothStep(0f, 1f, safeT), 0f);
            }
            if (drawerTop != null && drawerT != drawerTarget)
            {
                drawerT = Mathf.MoveTowards(drawerT, drawerTarget, dt * 2.5f);
                drawerTop.localPosition = drawerRest + drawerDir * (0.34f * Mathf.SmoothStep(0f, 1f, drawerT));
            }
            if (fuseboxDoor != null && fuseIn && fuseT < 1f)
            {
                fuseT = Mathf.MoveTowards(fuseT, 1f, dt * 1.5f);
                fuseboxDoor.localRotation = fuseRest * Quaternion.Euler(0f, 100f * Mathf.SmoothStep(0f, 1f, fuseT), 0f);
            }
            if (power && glowMats.Count > 0)
                foreach (Material m in glowMats) m.SetFloat("_Bright", 1.5f + 0.25f * Mathf.Sin(Time.time * 1.7f));
        }

        // ---------------------------------------------------------------------------------------- the walk grid (3 layers)
        bool[] solid, lockedCell;
        int gnx, gny, gn;
        float gcell = 0.4f;
        float[] stairH;
        float stairX0, stairX1, stairZ0, stairZ1;
        readonly Dictionary<int, List<int>> links = new Dictionary<int, List<int>>();

        int Cx(float x) { return Mathf.Clamp(Mathf.FloorToInt(x / gcell), 0, gnx - 1); }
        int Cz(float z) { return Mathf.Clamp(Mathf.FloorToInt(z / gcell), 0, gny - 1); }
        int Idx(int layer, int i, int j) { return layer * gn + j * gnx + i; }

        void BuildGrid()
        {
            object g = Json.Get(meta, "grid");
            gcell = Json.F(g, "cell", 0.4f);
            gnx = Json.I(g, "nx");
            gny = Json.I(g, "ny");
            gn = gnx * gny;
            solid = new bool[3 * gn];
            lockedCell = new bool[3 * gn];
            var rows = Json.O(g, "rows");
            for (int layer = 0; layer < 3; layer++)
            {
                for (int k = 0; k < gn; k++) solid[layer * gn + k] = true;
                if (rows == null || !rows.ContainsKey(layer.ToString())) continue;
                var rl = rows[layer.ToString()] as List<object>;
                for (int j = 0; j < rl.Count && j < gny; j++)
                {
                    string row = (string)rl[j];
                    for (int i = 0; i < row.Length && i < gnx; i++)
                        solid[Idx(layer, i, j)] = row[i] == '#';
                }
            }
            List<object> sh = Json.A(g, "stair_h");
            stairH = new float[gny];
            for (int j = 0; j < gny; j++) stairH[j] = sh != null && j < sh.Count ? Json.F(sh[j]) : 0f;
            List<object> lk = Json.A(g, "links");
            if (lk != null)
                foreach (object l in lk)
                {
                    object s = Json.Get(l, "stair"), c = Json.Get(l, "cell");
                    int a = Idx(2, (int)Json.At(s, 0), (int)Json.At(s, 1));
                    int b = Idx(Json.I(l, "floor"), (int)Json.At(c, 0), (int)Json.At(c, 1));
                    Link(a, b);
                    Link(b, a);
                }
            object st = Json.Get(meta, "stair");
            stairX0 = Json.F(st, "x0");
            stairX1 = Json.F(st, "x1");
            stairZ0 = Json.F(st, "z0");
            stairZ1 = Json.F(st, "z1");
        }

        void Link(int a, int b)
        {
            List<int> l;
            if (!links.TryGetValue(a, out l)) { l = new List<int>(); links[a] = l; }
            if (!l.Contains(b)) l.Add(b);
        }

        bool Blocked(int idx) { return solid[idx] || lockedCell[idx]; }

        public int CellOf(Vector3 p)
        {
            int i = Cx(p.x), j = Cz(p.z);
            bool overStair = p.x >= stairX0 - 0.05f && p.x <= stairX1 + 0.05f && p.z >= stairZ0 - 0.3f && p.z <= stairZ1 + 0.3f;
            int layer = p.y > h1 * 0.5f ? 1 : 0;
            if (overStair && p.y > 0.2f && p.y < h1 - 0.2f && !solid[Idx(2, i, j)]) layer = 2;
            return Idx(layer, i, j);
        }

        public Vector3 CellPos(int idx)
        {
            int layer = idx / gn, r = idx % gn;
            int j = r / gnx, i = r % gnx;
            float y = layer == 0 ? 0f : layer == 1 ? h1 : stairH[j];
            return new Vector3((i + 0.5f) * gcell, y, (j + 0.5f) * gcell);
        }

        public float FloorHeightAt(Vector3 p)
        {
            int c = CellOf(p);
            return CellPos(c).y;
        }

        int NearestFree(int idx)
        {
            if (!Blocked(idx)) return idx;
            int layer = idx / gn, r = idx % gn;
            int cj = r / gnx, ci = r % gnx;
            for (int rad = 1; rad < 8; rad++)
                for (int dx = -rad; dx <= rad; dx++)
                    for (int dy = -rad; dy <= rad; dy++)
                    {
                        int x = ci + dx, y = cj + dy;
                        if (x < 0 || y < 0 || x >= gnx || y >= gny) continue;
                        int k = Idx(layer, x, y);
                        if (!Blocked(k)) return k;
                    }
            if (layer == 2)
                return NearestFree(Idx(0, ci, cj));
            return idx;
        }

        float[] gScore, fScore;
        int[] cameFrom, heap, heapPos;
        int heapCount;
        static readonly int[] DX = { 1, -1, 0, 0, 1, 1, -1, -1 };
        static readonly int[] DY = { 0, 0, 1, -1, 1, -1, 1, -1 };

        public bool Reachable(Vector3 from, Vector3 to)
        {
            return FindPath(from, to).Count > 0;
        }

        public List<Vector3> FindPath(Vector3 from, Vector3 to)
        {
            var path = new List<Vector3>();
            if (solid == null) return path;
            int start = NearestFree(CellOf(from)), goal = NearestFree(CellOf(to));
            if (Blocked(start) || Blocked(goal)) return path;
            int n = 3 * gn;
            if (gScore == null || gScore.Length != n)
            {
                gScore = new float[n];
                fScore = new float[n];
                cameFrom = new int[n];
                heap = new int[n];
                heapPos = new int[n];
            }
            for (int i = 0; i < n; i++) { gScore[i] = float.MaxValue; cameFrom[i] = -1; heapPos[i] = -1; }
            Vector3 gp = CellPos(goal);
            heapCount = 0;
            gScore[start] = 0f;
            fScore[start] = Hc(start, gp);
            Push(start);
            bool found = false;
            while (heapCount > 0)
            {
                int cur = Pop();
                if (cur == goal) { found = true; break; }
                int layer = cur / gn, rr = cur % gn;
                int cy = rr / gnx, cx = rr % gnx;
                for (int k = 0; k < 8; k++)
                {
                    int x = cx + DX[k], y = cy + DY[k];
                    if (x < 0 || y < 0 || x >= gnx || y >= gny) continue;
                    int nb = Idx(layer, x, y);
                    if (Blocked(nb)) continue;
                    if (k >= 4 && (Blocked(Idx(layer, cx + DX[k], cy)) || Blocked(Idx(layer, cx, cy + DY[k])))) continue;
                    Relax(cur, nb, k >= 4 ? 1.41421356f : 1f, gp);
                }
                List<int> lk;
                if (links.TryGetValue(cur, out lk))
                    foreach (int nb in lk)
                        if (!Blocked(nb)) Relax(cur, nb, 1f, gp);
            }
            if (!found) return path;
            var cells = new List<int>();
            for (int c = goal; c != -1; c = cameFrom[c]) cells.Add(c);
            cells.Reverse();
            foreach (int c in cells) path.Add(CellPos(c));
            return path;
        }

        void Relax(int cur, int nb, float cost, Vector3 gp)
        {
            float ng = gScore[cur] + cost;
            if (ng < gScore[nb])
            {
                gScore[nb] = ng;
                cameFrom[nb] = cur;
                fScore[nb] = ng + Hc(nb, gp);
                if (heapPos[nb] < 0) Push(nb); else Up(heapPos[nb]);
            }
        }

        float Hc(int idx, Vector3 gp)
        {
            Vector3 p = CellPos(idx);
            float dx = (p.x - gp.x) / gcell, dz = (p.z - gp.z) / gcell, dy = Mathf.Abs(p.y - gp.y) / gcell;
            return Mathf.Sqrt(dx * dx + dz * dz) + dy * 0.5f;
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
            if (dot < (kind == "door" || kind == "hide" || kind == "maindoor" ? 0.8f : 0.88f)) return;
            float score = dot - dist * 0.03f + (kind == "item" ? 0.04f : 0f) + (kind == "plank" || kind == "padlock" || kind == "keypad" ? 0.03f : 0f);
            if (score <= bestScore) return;
            // nothing solid in between (a wall, the closed safe); the PC is seen past the chair
            RaycastHit hit;
            if (kind != "pc" && Physics.Linecast(camPos, pos, out hit, WallMask, QueryTriggerInteraction.Ignore)
                && Vector3.Distance(hit.point, pos) > (kind == "item" ? 0.35f : 0.6f)) return;
            bestScore = score;
            found.kind = kind;
            found.pos = pos;
            found.label = label;
            found.obj = obj;
            found.r = r;
        }

        public Target FindTarget(Vector3 camPos, Vector3 fwd)
        {
            bestScore = 0f;
            found.kind = null;
            foreach (Item it in items.Values)
            {
                if (it.held || it.gone || !it.found || !it.node.gameObject.activeInHierarchy) continue;
                if (it.id == "gold_key" && !safeOpen) continue;
                if (it.id == "silver_key" && drawerT < 0.6f) continue;
                Consider("item", it.node.position + new Vector3(0f, 0.03f, 0f), it.label, it, 2.3f, camPos, fwd);
            }
            foreach (Door d in doors.Values)
                if (d.lockId != "main") Consider("door", d.pos, DoorLabel(d), d, 2.4f, camPos, fwd);
            foreach (Hide h in hides)
                Consider("hide", h.pos + new Vector3(0f, 1.1f, 0f) + h.front * (h.depth * 0.5f), "Hide", h, 2.2f, camPos, fwd);
            Door main;
            if (doors.TryGetValue("door_main", out main) && main.lockId == "main")
            {
                foreach (Plank p in planks)
                    if (!p.gone) Consider("plank", p.pos, "Wooden Plank", p, 2.3f, camPos, fwd);
                foreach (Padlock p in padlocks)
                    if (!p.gone) Consider("padlock", p.pos, p.label, p, 2.3f, camPos, fwd);
                if (!codeSolved) Consider("keypad", keypadPos, "Door Keypad", null, 2.2f, camPos, fwd);
                Consider("maindoor", main.pos, "Main Door", null, 2.0f, camPos, fwd);
            }
            foreach (Plant p in plants)
                if (!p.searched) Consider("plant", p.pos, "Plant Pot", p, 2.2f, camPos, fwd);
            Consider("trophy", trophyPos, "Trophy", null, 2.0f, camPos, fwd);
            if (!safeOpen) Consider("safe", safePos, "Safe", null, 2.0f, camPos, fwd);
            Consider("drawer", drawerPos, drawerUnlocked ? (drawerOpen ? "Close Drawer" : "Open Drawer") : "Locked Drawer", null, 2.0f, camPos, fwd);
            if (!fuseIn) Consider("fusebox", fuseboxPos, "Fuse Box", null, 2.0f, camPos, fwd);
            Consider("pc", pcPos, "Trading PC", null, 2.4f, camPos, fwd);
            return found.kind != null ? found : null;
        }
    }
}
