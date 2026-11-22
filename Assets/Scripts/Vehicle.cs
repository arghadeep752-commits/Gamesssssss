using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Danga
{
    /// <summary>
    /// Every vehicle: cars, autos, bikes and scooters on ray-cast wheels with springs and tyre grip, the helicopter,
    /// the speedboat on the water levels. Traffic drives them kinematically along the lanes; anyone can pull the
    /// driver out and take the wheel.
    /// </summary>
    public class Vehicle : MonoBehaviour
    {
        public static readonly List<Vehicle> all = new List<Vehicle>();
        public VSpec spec;
        public Rigidbody rb;
        public Human driver;
        public bool npcDriver, traffic, wrecked, owned, siren, parked;
        public float health = 1000f, burning;
        public float steer, throttle, brake, lift;
        public bool handbrake;
        public float kinSpeed;
        GameObject body;
        Material bodyMat;
        float[] lastX;
        float rotor, flipTimer, nextCrash, engineVol;
        AudioSource engine;
        Transform rotorDisc, lightsGo, sirenGo;
        MeshRenderer sirenR;
        MaterialPropertyBlock mpb;
        public Color paint = Color.white;
        static readonly int WorldMask = 1 << City.LayerWorld;

        public float Speed => rb == null ? 0f : (rb.isKinematic ? kinSpeed : rb.linearVelocity.magnitude);
        public float ForwardSpeed => rb == null ? 0f : (rb.isKinematic ? kinSpeed : Vector3.Dot(rb.linearVelocity, transform.forward));
        public Vector3 SeatPos => spec.seat + (spec.open ? new Vector3(0f, -0.52f, 0f) : new Vector3(0f, -0.45f, 0f));
        public bool Grounded { get; private set; }

        void OnEnable() { all.Add(this); }
        void OnDisable() { all.Remove(this); }

        public static Vehicle Spawn(string model, Vector3 pos, float yaw, bool trafficMode, Color paint)
        {
            VSpec s;
            if (!Models.vehicles.TryGetValue(model, out s)) { Debug.LogWarning("[DG] no vehicle " + model); return null; }
            var go = new GameObject("veh_" + model);
            go.layer = City.LayerVehicle;
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f));
            var v = go.AddComponent<Vehicle>();
            v.spec = s;
            v.paint = paint;
            v.traffic = trafficMode;
            v.mpb = new MaterialPropertyBlock();
            v.body = Models.Spawn("Vehicles", model, go.transform, paint);
            v.body.layer = City.LayerVehicle;
            v.bodyMat = v.body.GetComponent<MeshRenderer>() != null ? v.body.GetComponent<MeshRenderer>().sharedMaterial : null;
            var box = go.AddComponent<BoxCollider>();
            float H = s.height, W = s.width, L = s.length;
            if (s.IsHeli) { box.size = new Vector3(W * 0.32f, H * 0.62f, L * 0.62f); box.center = new Vector3(0f, H * 0.33f, L * 0.1f); }
            else if (s.IsBoat) { box.size = new Vector3(W * 0.9f, H * 0.55f, L * 0.92f); box.center = new Vector3(0f, H * 0.3f, 0f); }
            else
            {
                float bottom = s.IsBike ? 0.3f : Mathf.Max(0.28f, H * 0.22f);
                float top = H * (s.IsBike ? 0.85f : 0.92f);
                box.size = new Vector3(s.IsBike ? W * 0.5f : W * 0.94f, top - bottom, L * 0.95f);
                box.center = new Vector3(0f, (top + bottom) * 0.5f, 0f);
            }
            v.rb = go.AddComponent<Rigidbody>();
            v.rb.mass = s.mass;
            v.rb.linearDamping = 0.03f;
            v.rb.angularDamping = s.IsHeli ? 2.5f : 0.6f;
            v.rb.interpolation = RigidbodyInterpolation.Interpolate;
            v.rb.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            v.rb.centerOfMass = new Vector3(0f, s.IsBike ? 0.42f : s.IsHeli ? H * 0.35f : s.IsBoat ? H * 0.15f : H * 0.28f, 0f);
            v.rb.isKinematic = trafficMode;
            v.lastX = new float[Mathf.Max(1, s.wheels.Count)];
            if (!trafficMode) { v.brake = 1f; v.handbrake = true; v.parked = true; }
            if (s.IsHeli && s.rotorR > 0f) v.MakeRotor();
            v.MakeLights();
            return v;
        }

        // ------------------------------------------------------------------ drivers
        public void TakeDriver(Human h)
        {
            driver = h;
            npcDriver = false;
            parked = false;
            var tc = GetComponent<TrafficCar>();
            if (tc != null) tc.Detach();
            if (rb.isKinematic)
            {
                rb.isKinematic = false;
                rb.linearVelocity = transform.forward * kinSpeed;
            }
            traffic = false;
            handbrake = false;
        }

        public void ReleaseDriver()
        {
            driver = null;
            steer = throttle = lift = 0f;
            brake = 1f;
            handbrake = true;
        }

        /// <summary>Puts the driver out on the street (car-jacking, crashes, death).</summary>
        public void Eject()
        {
            Vector3 exit = transform.TransformPoint(spec.exit);
            exit.y = City.I != null ? City.I.Ground(exit, transform.position.y) : transform.position.y;
            Human d = driver;
            if (d is Ped)
            {
                d.transform.SetParent(null, true);
                d.transform.position = exit;
                d.ShowBody(true);
                d.vehicle = null;
                var p = (Ped)d;
                p.st = Ped.St.Idle;
                if (!d.dead) p.Flee(transform.position, 10f);
            }
            else if (npcDriver)
            {
                var names = new[] { "npc_man", "npc_student", "npc_oldman" };
                var p = Ped.Create(names[Random.Range(0, names.Length)], exit, transform.eulerAngles.y + 90f, false);
                p.path = -1;
                Traffic.Adopt(p);
                p.Flee(transform.position, 10f);
            }
            if (!(d is Player)) driver = null;
            npcDriver = false;
            ReleaseDriver();
            var tc = GetComponent<TrafficCar>();
            if (tc != null) tc.Detach();
            if (rb.isKinematic) { rb.isKinematic = false; rb.linearVelocity = transform.forward * kinSpeed; }
            traffic = false;
        }

        // ------------------------------------------------------------------ physics
        void FixedUpdate()
        {
            if (rb == null || rb.isKinematic) return;
            float dt = Time.fixedDeltaTime;
            if (wrecked) { throttle = 0f; steer = 0f; lift = 0f; }
            if (spec.IsHeli) Heli(dt);
            else if (spec.IsBoat) Boat(dt);
            else Wheels(dt);
        }

        float Accel()
        {
            switch (spec.name)
            {
                case "sports_car": return 8.5f;
                case "bus": case "truck": return 2.4f;
                case "auto_rickshaw": return 2.8f;
                case "e_rickshaw": return 2.0f;
                case "motorbike": return 6.5f;
                case "scooter": return 4.2f;
                default: return 4.8f;
            }
        }

        void Wheels(float dt)
        {
            int n = spec.wheels.Count;
            if (n == 0) return;
            Vector3 up = transform.up;
            const float travel = 0.26f;
            float share = spec.mass / n;
            float k = share * 9.81f / (travel * 0.45f);
            float c = 2f * Mathf.Sqrt(k * share) * 0.5f;
            float fwd = Vector3.Dot(rb.linearVelocity, transform.forward);
            float top = spec.top / 3.6f;
            float steerAng = steer * Mathf.Lerp(34f, 7f, Mathf.Clamp01(Mathf.Abs(fwd) / (top * 0.6f)));
            int nDrive = 0;
            foreach (var w in spec.wheels) if (w.drive) nDrive++;
            nDrive = Mathf.Max(1, nDrive);
            float acc = Accel() * (1f - Mathf.Clamp01(fwd / top) * Mathf.Clamp01(fwd / top));
            float driveF = 0f, brakeF = brake;
            if (throttle > 0.01f) driveF = throttle * acc * spec.mass / nDrive;
            else if (throttle < -0.01f)
            {
                if (fwd > 1f) brakeF = Mathf.Max(brakeF, -throttle);
                else if (fwd > -7f) driveF = throttle * acc * 0.6f * spec.mass / nDrive;
            }
            int grounded = 0;
            Vector3 com = rb.worldCenterOfMass;
            for (int i = 0; i < n; i++)
            {
                WheelSpec w = spec.wheels[i];
                float len = travel + w.r;
                Vector3 origin = transform.TransformPoint(new Vector3(w.pos.x, w.r + travel * 0.55f, w.pos.z));
                RaycastHit hit;
                if (!Physics.Raycast(origin, -up, out hit, len, WorldMask, QueryTriggerInteraction.Ignore)) { lastX[i] = 0f; continue; }
                grounded++;
                float x = len - hit.distance;
                float fs = Mathf.Max(0f, k * x + c * (x - lastX[i]) / dt);
                lastX[i] = x;
                Vector3 dirF = w.steer ? Quaternion.AngleAxis(steerAng, up) * transform.forward : transform.forward;
                dirF = Vector3.ProjectOnPlane(dirF, hit.normal).normalized;
                Vector3 dirR = Vector3.Cross(hit.normal, dirF);
                Vector3 vp = rb.GetPointVelocity(hit.point);
                float vLong = Vector3.Dot(vp, dirF), vLat = Vector3.Dot(vp, dirR);
                float grip = handbrake && !w.steer ? 0.32f : 1f;
                float maxF = fs * 1.3f * grip + 200f;
                float fLat = Mathf.Clamp(-vLat * share / dt * 0.55f * grip, -maxF, maxF);
                float fLong = w.drive ? driveF : 0f;
                float bf = (brakeF * 9f + (handbrake && !w.steer ? 6f : 0f) + 0.25f) * share;
                fLong += Mathf.Clamp(-vLong * share / dt, -bf, bf);
                fLong = Mathf.Clamp(fLong, -maxF * 1.2f, maxF * 1.2f);
                Vector3 at = hit.point + up * Vector3.Dot(com - hit.point, up) * 0.75f;
                rb.AddForceAtPosition(hit.normal * fs, hit.point);
                rb.AddForceAtPosition(dirR * fLat + dirF * fLong, at);
            }
            Grounded = grounded > 0;
            // keep bikes and autos upright (bikes lean into turns), stop cars rolling over too easily
            bool bike = spec.IsBike, trike = spec.cls == "trike";
            float lean = bike ? -steer * Mathf.Clamp01(fwd / 10f) * 26f : 0f;
            Vector3 targetUp = Quaternion.AngleAxis(lean, transform.forward) * Vector3.up;
            Vector3 axis = Vector3.Cross(up, targetUp);
            float stiff = bike ? 70f : trike ? 22f : 9f, damp = bike ? 9f : 4f;
            float roll = Vector3.Dot(rb.angularVelocity, transform.forward);
            rb.AddTorque(transform.forward * (Vector3.Dot(axis, transform.forward) * stiff - roll * damp), ForceMode.Acceleration);
            if (!Grounded)
            {
                Vector3 pitchAxis = transform.right;
                float pr = Vector3.Dot(rb.angularVelocity, pitchAxis);
                rb.AddTorque(pitchAxis * (Vector3.Dot(axis, pitchAxis) * 6f - pr * 1.5f), ForceMode.Acceleration);
            }
            if (Grounded) rb.AddForce(-up * fwd * fwd * 0.6f * spec.mass / 1000f, ForceMode.Force);
            // upside down and stopped: put it back on its wheels
            if (Vector3.Dot(up, Vector3.up) < 0.35f && rb.linearVelocity.magnitude < 2f) flipTimer += dt; else flipTimer = 0f;
            if (flipTimer > 2.5f && !wrecked)
            {
                flipTimer = 0f;
                rb.MovePosition(transform.position + Vector3.up * 1.2f);
                rb.MoveRotation(Quaternion.Euler(0f, transform.eulerAngles.y, 0f));
                rb.angularVelocity = Vector3.zero;
            }
        }

        void Heli(float dt)
        {
            bool on = driver != null && !wrecked;
            rotor = Mathf.MoveTowards(rotor, on ? 1f : 0f, dt * (on ? 0.5f : 0.15f));
            if (rotor < 0.55f) return;
            float f = Mathf.InverseLerp(0.55f, 1f, rotor);
            Vector3 v = rb.linearVelocity;
            float vy = lift * 9f;
            rb.AddForce(Vector3.up * ((vy - v.y) * 2.2f + 9.81f * f), ForceMode.Acceleration);
            Vector3 flat = transform.forward;
            flat.y = 0f;
            flat.Normalize();
            Vector3 targetH = flat * (throttle * 52f);
            Vector3 hv = new Vector3(v.x, 0f, v.z);
            rb.AddForce((targetH - hv) * 0.8f * f, ForceMode.Acceleration);
            float yaw = transform.eulerAngles.y + steer * 75f * dt;
            Quaternion want = Quaternion.Euler(throttle * 13f, yaw, -steer * 16f);
            rb.MoveRotation(Quaternion.Slerp(rb.rotation, want, dt * 2.5f));
            rb.angularVelocity = Vector3.zero;
            Grounded = Physics.Raycast(transform.position + Vector3.up * 0.5f, Vector3.down, 1.0f, WorldMask, QueryTriggerInteraction.Ignore);
        }

        void Boat(float dt)
        {
            if (City.I == null) return;
            float W = spec.width * 0.36f, L = spec.length * 0.36f;
            float share = spec.mass / 4f;
            float k = share * 9.81f / Mathf.Max(0.15f, spec.waterline);
            int wet = 0;
            float t = Time.time;
            for (int i = 0; i < 4; i++)
            {
                Vector3 local = new Vector3((i & 1) == 0 ? -W : W, 0.05f, (i & 2) == 0 ? -L : L);
                Vector3 p = transform.TransformPoint(local);
                float wl = City.I.WaterLevel(p.x, p.z);
                if (float.IsNaN(wl)) continue;
                wl += Mathf.Sin(p.x * 0.05f + t * 0.9f) * 0.18f + Mathf.Sin(p.z * 0.07f + t * 1.3f) * 0.12f;
                float depth = wl - p.y;
                if (depth <= 0f) continue;
                wet++;
                Vector3 vp = rb.GetPointVelocity(p);
                rb.AddForceAtPosition(Vector3.up * (Mathf.Min(depth, 1.2f) * k - vp.y * share * 1.6f), p);
            }
            Grounded = wet > 0;
            Vector3 v = rb.linearVelocity;
            if (wet > 0)
            {
                Vector3 f = transform.forward, r = transform.right;
                float vl = Vector3.Dot(v, f), vs = Vector3.Dot(v, r);
                float top = spec.top / 3.6f;
                float thrust = (throttle > 0f ? throttle * 6.5f * (1f - Mathf.Clamp01(vl / top)) : throttle * 3f) * (driver != null ? 1f : 0f);
                rb.AddForce(f * (thrust - vl * 0.12f) + r * (-vs * 1.8f), ForceMode.Acceleration);
                rb.AddTorque(Vector3.up * steer * Mathf.Clamp(vl / 4f, -1f, 1f) * 1.6f, ForceMode.Acceleration);
                rb.angularDamping = 2.5f;
                rb.linearDamping = 0.15f;
            }
            else { rb.linearDamping = 1.5f; rb.angularDamping = 2f; }
        }

        void OnCollisionEnter(Collision col)
        {
            float rv = col.relativeVelocity.magnitude;
            if (rv < 5f) return;
            var other = col.collider.GetComponentInParent<Vehicle>();
            if (other != null && other.rb.isKinematic && rv > 4f)
            {
                var tc = other.GetComponent<TrafficCar>();
                if (tc != null) tc.Crash(rb.linearVelocity);
            }
            if (Time.time > nextCrash)
            {
                nextCrash = Time.time + 0.4f;
                GameAudio.At(rv > 14f ? "crash" : "glass_break", col.GetContact(0).point, Mathf.Clamp01(rv / 20f), 1f, 6f);
                if (driver != null && driver.isPlayer) Cam.Shake(Mathf.Clamp01(rv / 25f));
            }
            Damage((rv - 5f) * (spec.IsBike ? 6f : 12f), null);
            if (spec.IsBike && rv > 14f && driver != null && driver.isPlayer)
            {
                // thrown off the bike
                var p = (Player)driver;
                p.ExitVehicle(true);
                p.Hurt(rv * 1.5f, col.GetContact(0).point, null, false);
                p.knocked = 1.5f;
            }
        }

        void OnTriggerEnter(Collider other)
        {
            var h = other.GetComponentInParent<Human>();
            if (h == null || h == driver || h.vehicle == this) return;
            float sp = Speed;
            h.HitByVehicle(this, sp);
            if (sp > 3f && driver != null && driver.isPlayer && !h.isPlayer) Wanted.Crime(h.police ? 1.2f : 0.3f, h.transform.position, h.police);
        }

        public void Damage(float d, Human by)
        {
            if (wrecked || d <= 0f) return;
            health -= d;
            if (by != null && by.isPlayer && spec.police) Wanted.Crime(0.4f, transform.position, true);
            if (health <= 0f) Wreck(by);
        }

        void Wreck(Human by)
        {
            wrecked = true;
            health = 0f;
            burning = 0.01f;
            if (body != null) { mpb.SetColor("_Color", new Color(0.12f, 0.1f, 0.09f)); body.GetComponent<MeshRenderer>().SetPropertyBlock(mpb); }
            if (by != null && by.isPlayer) Wanted.Crime(spec.police ? 1.5f : 0.4f, transform.position, spec.police);
        }

        // ------------------------------------------------------------------ visuals and sound
        void MakeRotor()
        {
            var go = new GameObject("rotor");
            go.transform.SetParent(transform, false);
            go.transform.localPosition = spec.rotor + Vector3.up * 0.05f;
            var mf = go.AddComponent<MeshFilter>();
            var m = new Mesh();
            int seg = 24;
            var P = new Vector3[seg + 1];
            var C = new Color[seg + 1];
            var I = new int[seg * 3];
            P[0] = Vector3.zero;
            C[0] = new Color(0.1f, 0.1f, 0.1f, 0.25f);
            for (int i = 0; i < seg; i++)
            {
                float a = i * Mathf.PI * 2f / seg;
                P[i + 1] = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)) * spec.rotorR;
                C[i + 1] = new Color(0.1f, 0.1f, 0.1f, 0.05f);
                I[i * 3] = 0; I[i * 3 + 1] = 1 + (i + 1) % seg; I[i * 3 + 2] = 1 + i;
            }
            m.vertices = P;
            m.colors = C;
            m.triangles = I;
            mf.sharedMesh = m;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = new Material(Shader.Find("Sprites/Default"));
            r.shadowCastingMode = ShadowCastingMode.Off;
            rotorDisc = go.transform;
            rotorDisc.gameObject.SetActive(false);
        }

        void MakeLights()
        {
            Shader s = Shader.Find("Danga/GlowBillboard");
            var tex = Resources.Load<Texture2D>("UI/glow");
            if (s == null || spec.lights.Count == 0) return;
            var pts = new List<Vector3>();
            var cols = new List<Color32>();
            var sizes = new List<float>();
            foreach (var l in spec.lights) { pts.Add(l); cols.Add(new Color32(255, 240, 210, 255)); sizes.Add(0.55f); }
            foreach (var l in spec.lights) { pts.Add(new Vector3(l.x, l.y, -l.z)); cols.Add(new Color32(255, 30, 20, 200)); sizes.Add(0.3f); }
            lightsGo = GlowMesh("lights", pts, cols, sizes, s, tex, true).transform;
            if (spec.police)
            {
                var sp = new List<Vector3> { new Vector3(-0.35f, spec.height + 0.05f, 0f), new Vector3(0.35f, spec.height + 0.05f, 0f) };
                var go = GlowMesh("siren", sp, new List<Color32> { new Color32(255, 30, 30, 255), new Color32(40, 80, 255, 255) }, new List<float> { 0.7f, 0.7f }, s, tex, false);
                sirenGo = go.transform;
                sirenR = go.GetComponent<MeshRenderer>();
                go.SetActive(false);
            }
        }

        GameObject GlowMesh(string name, List<Vector3> pts, List<Color32> cols, List<float> sizes, Shader s, Texture2D tex, bool nightOnly)
        {
            int n = pts.Count;
            var P = new Vector3[n * 4];
            var U = new Vector2[n * 4];
            var U2 = new Vector2[n * 4];
            var C = new Color32[n * 4];
            var I = new int[n * 6];
            Vector2[] cr = { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            for (int i = 0; i < n; i++)
            {
                for (int k = 0; k < 4; k++) { P[i * 4 + k] = pts[i]; U[i * 4 + k] = cr[k]; U2[i * 4 + k] = new Vector2(sizes[i], 0f); C[i * 4 + k] = cols[i]; }
                I[i * 6] = i * 4; I[i * 6 + 1] = i * 4 + 2; I[i * 6 + 2] = i * 4 + 1; I[i * 6 + 3] = i * 4; I[i * 6 + 4] = i * 4 + 3; I[i * 6 + 5] = i * 4 + 2;
            }
            var m = new Mesh { name = name, vertices = P, uv = U, uv2 = U2, colors32 = C, triangles = I };
            m.bounds = new Bounds(Vector3.zero, Vector3.one * (spec.length + 2f));
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var r = go.AddComponent<MeshRenderer>();
            var mat = new Material(s);
            if (tex != null) mat.SetTexture("_MainTex", tex);
            mat.SetFloat("_NightOnly", nightOnly ? 1f : 0f);
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.Off;
            return go;
        }

        bool frozen;

        void Update()
        {
            // no ground collision loaded here yet: hold still instead of falling through the map
            if (City.I != null && !traffic && rb != null)
            {
                bool ready = City.I.CollisionReady(transform.position);
                if (!ready && !rb.isKinematic) { rb.isKinematic = true; frozen = true; }
                else if (ready && frozen) { rb.isKinematic = false; frozen = false; }
            }
            if (rotorDisc != null)
            {
                bool spin = spec.IsHeli && (rotor > 0.05f);
                rotorDisc.gameObject.SetActive(spin);
            }
            if (lightsGo != null) lightsGo.gameObject.SetActive(!wrecked && (driver != null || npcDriver || traffic) && Env.night > 0.3f);
            if (sirenGo != null)
            {
                bool on = siren && !wrecked;
                sirenGo.gameObject.SetActive(on);
                if (on) sirenGo.localScale = new Vector3(Mathf.Sin(Time.time * 14f) > 0 ? 1f : -1f, 1f, 1f);
            }
            if (wrecked)
            {
                burning += Time.deltaTime;
                if (burning < 5f && Random.value < 0.3f) Fx.Flash(transform.TransformPoint(new Vector3(0f, spec.height * 0.7f, spec.length * 0.3f)), 1.2f, new Color(1f, 0.45f, 0.1f), 0.15f);
                if (burning > 5f && burning - Time.deltaTime <= 5f)
                {
                    Combat.Explode(transform.position, 8f, 120f, null);
                    if (rb != null && !rb.isKinematic) rb.AddForce(Vector3.up * spec.mass * 6f, ForceMode.Impulse);
                }
            }
            Sound();
        }

        void Sound()
        {
            Transform lis = Cam.I != null ? Cam.I.transform : null;
            bool want = !wrecked && (driver != null || npcDriver || (spec.IsHeli && rotor > 0.05f)) && lis != null && (lis.position - transform.position).sqrMagnitude < 45f * 45f;
            if (want && engine == null)
            {
                string clip = spec.IsHeli ? "engine_heli" : spec.IsBoat ? "engine_boat" : spec.IsBike ? "engine_bike" : spec.cls == "trike" ? "engine_auto"
                            : (spec.name == "bus" || spec.name == "truck") ? "engine_diesel" : "engine_car";
                engine = GameAudio.Loop(clip, transform);
                if (engine != null) engine.time = Random.value * Mathf.Max(0.1f, engine.clip.length - 0.1f);
            }
            if (!want && engine != null) { Destroy(engine.gameObject); engine = null; }
            if (engine == null) return;
            float top = spec.top / 3.6f;
            float x = Mathf.Clamp01(Speed / Mathf.Max(5f, top));
            bool mine = driver != null && driver.isPlayer;
            if (spec.IsHeli) { engine.pitch = 0.7f + 0.35f * rotor; engine.volume = 0.8f * rotor; return; }
            engineVol = Mathf.Lerp(engineVol, (mine ? 0.55f : 0.3f) + 0.35f * Mathf.Abs(throttle), Time.deltaTime * 4f);
            engine.volume = engineVol;
            engine.pitch = 0.75f + x * 0.9f + (mine ? Mathf.Abs(throttle) * 0.1f : 0f);
        }

        public void Horn()
        {
            string h = spec.IsBike || spec.cls == "trike" ? "horn_bike" : (spec.name == "bus" || spec.name == "truck") ? "horn_truck" : "horn_car";
            GameAudio.At(h, transform.position, 0.9f, 1f, 10f);
            Traffic.Panic(transform.position + transform.forward * 6f, 6f, false);
        }

        public void SetKinematicPose(Vector3 p, Quaternion r, float spd)
        {
            kinSpeed = spd;
            rb.MovePosition(p);
            rb.MoveRotation(r);
        }
    }
}
