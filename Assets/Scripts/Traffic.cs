using System.Collections.Generic;
using UnityEngine;

namespace Danga
{
    /// <summary>A polyline: a traffic lane (India drives on the left) or a footpath.</summary>
    public class Path
    {
        public Vector3[] p;
        public float[] d;
        public float len, speed = 12f;
        public int[] next = new int[0];
        public bool junction;
        public string cls = "B";
        public readonly List<TrafficCar> cars = new List<TrafficCar>();

        public static Path From(object pts)
        {
            var l = pts as List<object>;
            var path = new Path();
            int n = l != null ? l.Count : 0;
            path.p = new Vector3[Mathf.Max(2, n)];
            for (int i = 0; i < n; i++) path.p[i] = Json.V3(l[i]);
            if (n < 2) path.p[1] = path.p[0] + Vector3.forward;
            path.d = new float[path.p.Length];
            for (int i = 1; i < path.p.Length; i++) path.d[i] = path.d[i - 1] + Vector3.Distance(path.p[i - 1], path.p[i]);
            path.len = Mathf.Max(0.1f, path.d[path.p.Length - 1]);
            return path;
        }

        public Vector3 At(float s, out Vector3 dir)
        {
            s = Mathf.Clamp(s, 0f, len);
            int lo = 0, hi = d.Length - 1;
            while (hi - lo > 1)
            {
                int m = (lo + hi) >> 1;
                if (d[m] <= s) lo = m; else hi = m;
            }
            float seg = d[hi] - d[lo];
            float t = seg > 1e-4f ? (s - d[lo]) / seg : 0f;
            dir = p[hi] - p[lo];
            dir = dir.sqrMagnitude > 1e-6f ? dir.normalized : Vector3.forward;
            return Vector3.Lerp(p[lo], p[hi], t);
        }

        public float Nearest(Vector3 q, out float dist)
        {
            float best = 1e9f, bs = 0f;
            for (int i = 0; i < p.Length - 1; i++)
            {
                Vector3 a = p[i], b = p[i + 1], ab = b - a;
                float t = Mathf.Clamp01(Vector3.Dot(q - a, ab) / Mathf.Max(1e-4f, ab.sqrMagnitude));
                float dd = (a + ab * t - q).sqrMagnitude;
                if (dd < best) { best = dd; bs = d[i] + (d[i + 1] - d[i]) * t; }
            }
            dist = Mathf.Sqrt(best);
            return bs;
        }
    }

    /// <summary>Drives one traffic vehicle along the lanes, keeping its distance and stopping for people.</summary>
    public class TrafficCar : MonoBehaviour
    {
        public Vehicle v;
        public int lane;
        public float s, speed, mood = 1f;
        float honk;
        public Ped rider;

        public void Init(Vehicle veh, int laneIndex, float at)
        {
            v = veh;
            lane = laneIndex;
            s = at;
            mood = Random.Range(0.8f, 1.15f);
            Traffic.I.lanes[lane].cars.Add(this);
            speed = Traffic.I.lanes[lane].speed * 0.6f;
            Place(Traffic.I.lanes[lane]);
        }

        public void Detach()
        {
            if (Traffic.I != null && lane >= 0 && lane < Traffic.I.lanes.Length) Traffic.I.lanes[lane].cars.Remove(this);
            Traffic.I.cars.Remove(this);
            if (v != null) v.traffic = false;
            Destroy(this);
        }

        public void Crash(Vector3 hit)
        {
            if (v == null) return;
            v.rb.isKinematic = false;
            v.rb.linearVelocity = transform.forward * speed * 0.5f + hit * 0.3f;
            v.traffic = false;
            v.ReleaseDriver();
            if (rider != null) { v.driver = rider; v.Eject(); }
            Detach();
        }

        void Place(Path L)
        {
            Vector3 dir;
            Vector3 pos = L.At(s, out dir);
            Vector3 d2;
            Vector3 ahead = L.At(Mathf.Min(L.len, s + 2.5f), out d2);
            Vector3 fwd = ahead - pos;
            if (fwd.sqrMagnitude < 0.01f) fwd = dir;
            v.SetKinematicPose(pos + Vector3.up * 0.03f, Quaternion.LookRotation(fwd, Vector3.up), speed);
        }

        void FixedUpdate()
        {
            if (v == null || !v.traffic || Traffic.I == null) return;
            float dt = Time.fixedDeltaTime;
            Path L = Traffic.I.lanes[lane];
            float want = L.speed * mood * Mathf.Min(1f, v.spec.top / 110f) * (L.junction ? 0.6f : 1f);
            float gap = 1e9f;
            foreach (var o in L.cars) if (o != this && o.s > s) gap = Mathf.Min(gap, o.s - s - (o.v.spec.length + v.spec.length) * 0.5f);
            if (gap > 40f && L.next.Length > 0)
                foreach (int nx in L.next)
                    foreach (var o in Traffic.I.lanes[nx].cars) gap = Mathf.Min(gap, L.len - s + o.s - (o.v.spec.length + v.spec.length) * 0.5f);
            float obst = Obstacle();
            float g = Mathf.Min(gap, obst);
            float safe = 4f + speed * 1.3f;
            if (g < safe) want = Mathf.Min(want, Mathf.Max(0f, (g - 2.5f) * 0.9f));
            speed = Mathf.MoveTowards(speed, want, (want < speed ? 8f : 2.6f) * dt);
            if (obst < 9f && speed < 1f && Time.time > honk && Random.value < 0.02f) { honk = Time.time + 4f; v.Horn(); }
            s += speed * dt;
            int guard = 0;
            while (s > L.len && guard++ < 4)
            {
                if (L.next.Length == 0) { Traffic.I.Despawn(this); return; }
                int nl = L.next[Random.Range(0, L.next.Length)];
                L.cars.Remove(this);
                s -= L.len;
                lane = nl;
                L = Traffic.I.lanes[lane];
                L.cars.Add(this);
            }
            Place(L);
        }

        float Obstacle()
        {
            float best = 1e9f;
            Vector3 f = transform.forward, me = transform.position;
            float half = v.spec.length * 0.5f;
            Player p = Player.I;
            if (p != null && !p.dead)
            {
                Vector3 at = p.vehicle != null ? p.vehicle.transform.position : p.transform.position;
                float w = p.vehicle != null ? p.vehicle.spec.width * 0.5f + 1.2f : 1.6f;
                Check(at - me, f, half, w, ref best);
            }
            foreach (var o in Vehicle.all)
            {
                if (o == v || o.traffic || (o.transform.position - me).sqrMagnitude > 400f) continue;
                Check(o.transform.position - me, f, half, o.spec.width * 0.5f + 1.1f, ref best);
            }
            foreach (var h in Traffic.I.peds)
            {
                if (h == null || h.dead || h.st == Ped.St.Walk || h.st == Ped.St.Ride) continue;
                Vector3 r = h.transform.position - me;
                if (r.sqrMagnitude > 400f) continue;
                Check(r, f, half, 1.4f, ref best);
            }
            return best;
        }

        static void Check(Vector3 rel, Vector3 f, float half, float width, ref float best)
        {
            float along = Vector3.Dot(rel, f);
            if (along < 0f || along > 22f) return;
            Vector3 lat = rel - f * along;
            lat.y = 0f;
            if (lat.magnitude > width) return;
            best = Mathf.Min(best, along - half);
        }
    }

    /// <summary>Steers a police car towards the player.</summary>
    public class AIDriver : MonoBehaviour
    {
        public Vehicle v;
        float stuck, reverseUntil;
        bool dismounted;

        void FixedUpdate()
        {
            Player p = Player.I;
            if (v == null || v.wrecked || p == null) return;
            if (Wanted.stars == 0 || p.dead) { v.siren = false; v.throttle = 0f; v.brake = 1f; return; }
            v.siren = true;
            v.handbrake = false;
            Vector3 target = p.vehicle != null ? p.vehicle.transform.position : p.transform.position;
            Vector3 local = transform.InverseTransformPoint(target);
            float ang = Mathf.Atan2(local.x, local.z) * Mathf.Rad2Deg;
            float dist = local.magnitude;
            v.steer = Mathf.Clamp(ang / 28f, -1f, 1f);
            if (Time.time < reverseUntil) { v.throttle = -0.8f; v.steer = -v.steer; v.brake = 0f; return; }
            if (dist < 14f && p.vehicle == null)
            {
                v.throttle = 0f;
                v.brake = 1f;
                if (!dismounted && v.Speed < 2f)
                {
                    dismounted = true;
                    v.npcDriver = false;
                    for (int i = 0; i < 2; i++)
                    {
                        Vector3 e = transform.TransformPoint(new Vector3(i == 0 ? v.spec.width * 0.5f + 0.8f : -v.spec.width * 0.5f - 0.8f, 0f, 0f));
                        e.y = City.I.Ground(e, transform.position.y);
                        var cop = Ped.Create("police", e, transform.eulerAngles.y, true);
                        Traffic.Adopt(cop);
                        cop.Chase();
                    }
                }
                return;
            }
            if (dismounted) { v.throttle = 0f; v.brake = 1f; return; }
            v.brake = 0f;
            v.throttle = Mathf.Abs(ang) > 110f ? -0.7f : dist > 35f ? 1f : 0.75f;
            if (Mathf.Abs(ang) > 110f) v.steer = -v.steer;
            if (v.Speed < 1.2f && v.throttle > 0.5f) stuck += Time.fixedDeltaTime; else stuck = 0f;
            if (stuck > 1.8f) { stuck = 0f; reverseUntil = Time.time + 1.4f; }
        }
    }

    /// <summary>Stars, heat and the police response.</summary>
    public static class Wanted
    {
        public static int stars;
        static float heat, lastSeen;
        public static bool never;
        static readonly float[] Levels = { 0f, 0.8f, 3f, 6f, 10f, 15f };

        public static void Crime(float h, Vector3 at, bool cop = false)
        {
            if (never || Game.I == null || Game.I.state != Game.S.Play) return;
            heat += h * (cop ? 1.5f : 1f);
            int s = 0;
            for (int i = 1; i < Levels.Length; i++) if (heat >= Levels[i]) s = i;
            if (s > stars) { stars = s; Hud.Stars(); }
            lastSeen = Time.time;
        }

        public static void Noise(Vector3 at, Human shooter)
        {
            Traffic.Panic(at, 32f);
            if (shooter != null && shooter.isPlayer) Crime(0.15f, at, CopsNear(at, 40f));
        }

        public static void Seen() { lastSeen = Time.time; }

        public static bool CopsNear(Vector3 p, float r)
        {
            float r2 = r * r;
            foreach (var h in Human.all) if (h.police && !h.dead && (h.transform.position - p).sqrMagnitude < r2) return true;
            foreach (var v in Vehicle.all) if (v.spec.police && v.npcDriver && (v.transform.position - p).sqrMagnitude < r2) return true;
            return false;
        }

        public static void Tick()
        {
            if (stars == 0) { heat = Mathf.Max(0f, heat - Time.deltaTime * 0.05f); return; }
            if (CopsNear(Player.I.transform.position, 25f)) lastSeen = Time.time;
            if (Time.time - lastSeen > 18f + stars * 6f)
            {
                stars--;
                heat = Levels[stars];
                lastSeen = Time.time;
                Hud.Stars();
            }
        }

        public static float Escape => stars == 0 ? 0f : Mathf.Clamp01((Time.time - lastSeen) / (18f + stars * 6f));

        public static void Set(int s)
        {
            stars = Mathf.Clamp(s, 0, 5);
            heat = Levels[stars];
            lastSeen = Time.time;
            Hud.Stars();
        }
    }

    /// <summary>Spawns and removes traffic, pedestrians and police around the player.</summary>
    public class Traffic : MonoBehaviour
    {
        public static Traffic I;
        public Path[] lanes = new Path[0], walks = new Path[0];
        List<int>[] links;
        public readonly List<TrafficCar> cars = new List<TrafficCar>();
        public readonly List<Ped> peds = new List<Ped>();
        readonly List<Vehicle> copCars = new List<Vehicle>();
        public int maxCars = 12, maxPeds = 16;
        float next;
        static readonly string[] CarModels = { "auto_rickshaw", "e_rickshaw", "motorbike", "scooter", "car_hatch", "car_sedan", "car_suv", "van", "bus", "truck", "sports_car", "police_jeep" };
        static readonly float[] CarWeights = { 20, 9, 15, 12, 13, 8, 6, 5, 3, 5, 2, 2 };
        static readonly string[] PedModels = { "npc_man", "npc_student", "npc_oldman", "npc_saree", "npc_tripuri" };
        static readonly float[] PedWeights = { 30, 20, 14, 20, 16 };
        static readonly Color[] Paints = { Color.white, new Color(0.95f, 0.95f, 0.95f), new Color(0.75f, 0.78f, 0.82f), new Color(0.6f, 0.62f, 0.66f),
                                           new Color(1f, 0.85f, 0.8f), new Color(0.85f, 0.9f, 1f), new Color(1f, 0.95f, 0.8f) };

        public void Init()
        {
            I = this;
            object m = City.I.meta;
            var ls = Json.A(m, "lanes");
            if (ls != null)
            {
                lanes = new Path[ls.Count];
                for (int i = 0; i < ls.Count; i++)
                {
                    object o = ls[i];
                    var p = Path.From(Json.Get(o, "pts"));
                    p.speed = Json.F(o, "speed", 12f);
                    p.cls = Json.S(o, "cls", "B");
                    p.junction = Json.Has(o, "junction");
                    var nx = Json.A(o, "next");
                    if (nx != null)
                    {
                        var list = new List<int>();
                        foreach (object k in nx) { int idx = (int)Json.F(k); if (idx >= 0 && idx < ls.Count) list.Add(idx); }
                        p.next = list.ToArray();
                    }
                    lanes[i] = p;
                }
            }
            var ws = Json.A(m, "walks");
            if (ws != null)
            {
                walks = new Path[ws.Count];
                for (int i = 0; i < ws.Count; i++) walks[i] = Path.From(Json.Get(ws[i], "pts"));
            }
            links = new List<int>[walks.Length * 2];
            for (int i = 0; i < links.Length; i++) links[i] = new List<int>();
            var wl = Json.A(m, "walk_links");
            if (wl != null)
                foreach (object o in wl)
                {
                    var pair = o as List<object>;
                    if (pair == null || pair.Count < 2) continue;
                    int a = End(pair[0]), b = End(pair[1]);
                    if (a < 0 || b < 0 || a >= links.Length || b >= links.Length) continue;
                    links[a].Add(b);
                    links[b].Add(a);
                }
            Debug.Log("[DG] traffic: " + lanes.Length + " lanes, " + walks.Length + " footpaths");
        }

        static int End(object o)
        {
            var e = o as List<object>;
            if (e == null || e.Count < 2) return -1;
            return (int)Json.F(e[0]) * 2 + (Json.F(e[1]) < 0f ? 1 : 0);
        }

        static string Pick(string[] names, float[] w)
        {
            float t = 0f;
            foreach (float x in w) t += x;
            float r = Random.value * t;
            for (int i = 0; i < names.Length; i++) { r -= w[i]; if (r <= 0f) return names[i]; }
            return names[0];
        }

        public void NextWalk(Ped p, Path w)
        {
            int end = p.path * 2 + (p.s > w.len ? 1 : 0);
            var opts = links != null && end < links.Length ? links[end] : null;
            if (opts == null || opts.Count == 0)
            {
                p.dir = -p.dir;
                p.s = Mathf.Clamp(p.s, 0f, w.len);
                return;
            }
            int to = opts[Random.Range(0, opts.Count)];
            p.path = to / 2;
            bool atEnd = (to & 1) == 1;
            p.s = atEnd ? walks[p.path].len : 0f;
            p.dir = atEnd ? -1f : 1f;
        }

        public static void Panic(Vector3 at, float r, bool scream = true)
        {
            if (I == null) return;
            float r2 = r * r;
            foreach (var p in I.peds)
            {
                if (p == null || p.dead || p.police || p.st == Ped.St.Ride || p.st == Ped.St.Fight) continue;
                if ((p.transform.position - at).sqrMagnitude < r2)
                {
                    if (scream) p.Flee(at, 8f);
                    else if (p.st == Ped.St.Walk) { p.st = Ped.St.Idle; p.until = Time.time + 1.5f; }
                }
            }
        }

        public static void Adopt(Ped p)
        {
            if (I != null && !I.peds.Contains(p)) I.peds.Add(p);
        }

        public static void ReattachPed(Ped p)
        {
            if (I == null) return;
            float best = 25f;
            int bp = -1;
            float bs = 0f;
            for (int i = 0; i < I.walks.Length; i++)
            {
                Path w = I.walks[i];
                Vector3 a = w.p[0], b = w.p[w.p.Length - 1];
                Vector3 c = (a + b) * 0.5f;
                if ((c - p.transform.position).sqrMagnitude > (w.len * 0.5f + 30f) * (w.len * 0.5f + 30f)) continue;
                float d;
                float s = w.Nearest(p.transform.position, out d);
                if (d < best) { best = d; bp = i; bs = s; }
            }
            if (bp >= 0) { p.path = bp; p.s = bs; p.st = Ped.St.Walk; }
            else { p.path = -1; p.st = Ped.St.Idle; p.until = Time.time + 1e6f; }
        }

        void Update()
        {
            if (Game.I == null || Game.I.state == Game.S.Paused || Player.I == null) return;
            if (Time.time < next) return;
            next = Time.time + 0.25f;
            Vector3 pp = Game.I.Focus;
            // remove far ones
            for (int i = cars.Count - 1; i >= 0; i--)
            {
                var c = cars[i];
                if (c == null || c.v == null) { cars.RemoveAt(i); continue; }
                if ((c.transform.position - pp).sqrMagnitude > 270f * 270f) Despawn(c);
            }
            for (int i = peds.Count - 1; i >= 0; i--)
            {
                var p = peds[i];
                if (p == null) { peds.RemoveAt(i); continue; }
                float d2 = (p.transform.position - pp).sqrMagnitude;
                bool deadLong = p.dead && Time.time - p.deadTime > 40f;
                if (p.st == Ped.St.Ride) continue;
                if (d2 > 130f * 130f || deadLong) { peds.RemoveAt(i); Destroy(p.gameObject); }
            }
            foreach (var v in Vehicle.all.ToArray())
            {
                if (v == null || v.traffic || v.owned || v.driver != null && v.driver.isPlayer) continue;
                float d2 = (v.transform.position - pp).sqrMagnitude;
                if ((v.wrecked && d2 > 120f * 120f) || (!v.parked && d2 > 300f * 300f)) Destroy(v.gameObject);
            }
            // add new ones
            int tries = 3;
            while (cars.Count < maxCars && tries-- > 0) SpawnCar(pp);
            int livePeds = 0;
            foreach (var p in peds) if (p != null && !p.police && p.st != Ped.St.Ride) livePeds++;
            tries = 3;
            while (livePeds < maxPeds && tries-- > 0) if (SpawnPed(pp)) livePeds++;
            Police(pp);
        }

        public void Despawn(TrafficCar c)
        {
            cars.Remove(c);
            if (c.lane >= 0 && c.lane < lanes.Length) lanes[c.lane].cars.Remove(c);
            if (c.rider != null) { peds.Remove(c.rider); Destroy(c.rider.gameObject); }
            if (c.v != null) Destroy(c.v.gameObject);
        }

        bool SpawnCar(Vector3 pp)
        {
            if (lanes.Length == 0) return false;
            int li = Random.Range(0, lanes.Length);
            Path L = lanes[li];
            if (L.junction) return false;
            float s = Random.Range(0f, L.len);
            Vector3 dir;
            Vector3 pos = L.At(s, out dir);
            float d = Vector3.Distance(pos, pp);
            if (d < 70f || d > 230f) return false;
            if (Cam.I != null && d < 140f && Cam.I.Visible(pos)) return false;
            foreach (var o in L.cars) if (Mathf.Abs(o.s - s) < 18f) return false;
            string model = Pick(CarModels, CarWeights);
            if ((model == "bus" || model == "truck") && L.cls == "C") model = "car_hatch";
            var v = Vehicle.Spawn(model, pos, Quaternion.LookRotation(dir).eulerAngles.y, true, Paints[Random.Range(0, Paints.Length)]);
            if (v == null) return false;
            var tc = v.gameObject.AddComponent<TrafficCar>();
            tc.Init(v, li, s);
            cars.Add(tc);
            if (v.spec.open)
            {
                var rider = Ped.Create(Pick(PedModels, new float[] { 40, 30, 15, 5, 10 }), v.transform.position, 0f, false);
                rider.st = Ped.St.Ride;
                rider.vehicle = v;
                rider.transform.SetParent(v.transform, false);
                rider.transform.localPosition = v.SeatPos;
                rider.transform.localRotation = Quaternion.identity;
                if (rider.rig != null) rider.rig.Play(v.spec.IsBike ? "ride" : "drive", 0f);
                var hb = rider.GetComponentInChildren<CapsuleCollider>();
                if (hb != null) hb.enabled = false;
                v.driver = rider;
                tc.rider = rider;
                peds.Add(rider);
            }
            else v.npcDriver = true;
            return true;
        }

        bool SpawnPed(Vector3 pp)
        {
            if (walks.Length == 0) return false;
            int wi = Random.Range(0, walks.Length);
            Path w = walks[wi];
            float s = Random.Range(0f, w.len);
            Vector3 dir;
            Vector3 pos = w.At(s, out dir);
            float d = Vector3.Distance(pos, pp);
            if (d < 30f || d > 110f) return false;
            if (Cam.I != null && d < 55f && Cam.I.Visible(pos)) return false;
            var p = Ped.Create(Pick(PedModels, PedWeights), pos, 0f, false);
            p.path = wi;
            p.s = s;
            p.dir = Random.value < 0.5f ? 1f : -1f;
            peds.Add(p);
            return true;
        }

        void Police(Vector3 pp)
        {
            int stars = Wanted.stars;
            int wantFoot = stars == 0 ? 0 : 1 + stars * 2, wantCars = stars == 0 ? 0 : Mathf.Min(4, stars);
            int foot = 0;
            foreach (var p in peds) if (p != null && p.police && !p.dead && p.st == Ped.St.Chase) foot++;
            copCars.RemoveAll(c => c == null || c.wrecked);
            if (stars == 0)
            {
                foreach (var c in copCars) if (c != null && (c.transform.position - pp).sqrMagnitude > 150f * 150f) Destroy(c.gameObject);
                return;
            }
            if (foot < wantFoot && walks.Length > 0)
            {
                for (int t = 0; t < 6; t++)
                {
                    int wi = Random.Range(0, walks.Length);
                    Vector3 dir;
                    Vector3 pos = walks[wi].At(Random.Range(0f, walks[wi].len), out dir);
                    float d = Vector3.Distance(pos, pp);
                    if (d < 35f || d > 75f) continue;
                    var cop = Ped.Create("police", pos, 0f, true);
                    peds.Add(cop);
                    cop.Chase();
                    break;
                }
            }
            if (copCars.Count < wantCars && lanes.Length > 0)
            {
                for (int t = 0; t < 6; t++)
                {
                    int li = Random.Range(0, lanes.Length);
                    Path L = lanes[li];
                    float s = Random.Range(0f, L.len);
                    Vector3 dir;
                    Vector3 pos = L.At(s, out dir);
                    float d = Vector3.Distance(pos, pp);
                    if (d < 80f || d > 160f || !City.I.CollisionReady(pos)) continue;
                    var v = Vehicle.Spawn("police_jeep", pos + Vector3.up * 0.3f, Quaternion.LookRotation(dir).eulerAngles.y, false, Color.white);
                    if (v == null) break;
                    v.parked = false;
                    v.handbrake = false;
                    v.brake = 0f;
                    v.npcDriver = true;
                    v.siren = true;
                    v.gameObject.AddComponent<AIDriver>().v = v;
                    copCars.Add(v);
                    break;
                }
            }
        }
    }
}
