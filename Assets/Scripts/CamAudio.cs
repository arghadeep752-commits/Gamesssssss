using System.Collections.Generic;
using UnityEngine;

namespace Danga
{
    /// <summary>Third-person camera: orbit by dragging, follows behind vehicles, slow orbit in the menu.</summary>
    public class Cam : MonoBehaviour
    {
        public static Cam I;
        public Camera cam;
        public float yaw, pitch = 12f, dist = 4.4f;
        public Vector2 look;               // drag input (pixels this frame)
        public float sensitivity = 1f;
        float idle, shake, curDist = 4.4f;
        Vector3 focus;
        public bool menuOrbit;
        public Vector3 orbitCentre;
        Plane[] planes = new Plane[6];
        int planesFrame = -1;

        public Vector3 Flat
        {
            get
            {
                Vector3 f = transform.forward;
                f.y = 0f;
                return f.sqrMagnitude > 1e-4f ? f.normalized : Vector3.forward;
            }
        }

        public static Cam Create()
        {
            var go = new GameObject("Camera");
            go.tag = "MainCamera";
            var c = go.AddComponent<Camera>();
            c.nearClipPlane = 0.15f;
            c.farClipPlane = 1500f;
            c.fieldOfView = 60f;
            c.clearFlags = CameraClearFlags.Skybox;
            c.allowHDR = false;
            c.allowMSAA = true;
            go.AddComponent<AudioListener>();
            I = go.AddComponent<Cam>();
            I.cam = c;
            return I;
        }

        public static void Shake(float s) { if (I != null) I.shake = Mathf.Max(I.shake, s); }

        public bool Visible(Vector3 p)
        {
            if (planesFrame != Time.frameCount) { GeometryUtility.CalculateFrustumPlanes(cam, planes); planesFrame = Time.frameCount; }
            return GeometryUtility.TestPlanesAABB(planes, new Bounds(p + Vector3.up, Vector3.one * 3f));
        }

        void LateUpdate()
        {
            float dt = Time.unscaledDeltaTime;
            if (menuOrbit)
            {
                yaw += dt * 4f;
                Quaternion q = Quaternion.Euler(14f, yaw, 0f);
                transform.position = orbitCentre + q * new Vector3(0f, 0f, -150f) + Vector3.up * 45f;
                transform.rotation = Quaternion.LookRotation(orbitCentre + Vector3.up * 10f - transform.position);
                return;
            }
            Player p = Player.I;
            if (p == null) return;
            Vehicle v = p.vehicle;
            Vector3 target;
            float wantDist;
            if (v != null)
            {
                target = v.transform.position + Vector3.up * (v.spec.height * 0.75f + 0.6f);
                wantDist = v.spec.length * 0.85f + 3.4f + (v.spec.IsHeli ? 6f : 0f);
            }
            else
            {
                target = p.transform.position + Vector3.up * 1.55f;
                wantDist = dist * (p.fire && !p.Def.melee ? 0.8f : 1f);
            }
            if (look.sqrMagnitude > 0.01f)
            {
                yaw += look.x * 0.18f * sensitivity;
                pitch = Mathf.Clamp(pitch - look.y * 0.14f * sensitivity, -25f, 70f);
                idle = 0f;
            }
            else idle += dt;
            look = Vector2.zero;
            if (v != null && idle > 1.2f && v.Speed > 3f)
            {
                // swing back behind the vehicle
                float vy = Quaternion.LookRotation(v.ForwardSpeed >= 0f ? v.transform.forward : -v.transform.forward).eulerAngles.y;
                yaw = Mathf.LerpAngle(yaw, vy, dt * 2.2f);
                pitch = Mathf.Lerp(pitch, v.spec.IsHeli ? 18f : 9f, dt * 1.5f);
            }
            focus = Vector3.Lerp(focus, target, 1f - Mathf.Exp(-dt * (v != null ? 14f : 20f)));
            if ((focus - target).sqrMagnitude > 100f) focus = target;
            Quaternion rot = Quaternion.Euler(pitch, yaw, 0f);
            Vector3 back = rot * Vector3.back;
            RaycastHit hit;
            float d = wantDist;
            if (Physics.SphereCast(focus, 0.25f, back, out hit, wantDist, 1 << City.LayerWorld, QueryTriggerInteraction.Ignore)) d = Mathf.Max(0.8f, hit.distance - 0.1f);
            curDist = d < curDist ? d : Mathf.Lerp(curDist, d, dt * 3f);
            Vector3 pos = focus + back * curDist;
            if (shake > 0f)
            {
                pos += Random.insideUnitSphere * shake * 0.25f;
                shake = Mathf.Max(0f, shake - dt * 2.5f);
            }
            transform.SetPositionAndRotation(pos, rot);
            float fov = 60f + (v != null ? Mathf.Clamp01(v.Speed / 40f) * 10f : 0f);
            cam.fieldOfView = Mathf.Lerp(cam.fieldOfView, fov, dt * 3f);
        }
    }

    /// <summary>Recorded sound effects (3D one-shots and loops), ambience by place and time, the radio.</summary>
    public class GameAudio : MonoBehaviour
    {
        static GameAudio I;
        static readonly Dictionary<string, AudioClip> clips = new Dictionary<string, AudioClip>();
        readonly List<AudioSource> pool = new List<AudioSource>();
        AudioSource ui, ambA, ambB, radio;
        string ambName = "";
        public static float sfx = 1f, music = 0.7f;
        public static int station = 0;
        public static readonly string[] Stations = { "radio_desi", "radio_hiphop", "radio_sitar", "music_chase" };
        public static readonly string[] StationNames = { "Agartala FM - Desi", "Tripura Beats - Hip Hop", "Raag Radio - Sitar", "Chase FM" };
        float nextAmb;

        public static void Init(Transform parent)
        {
            var go = new GameObject("audio");
            go.transform.SetParent(parent, false);
            I = go.AddComponent<GameAudio>();
            I.ui = go.AddComponent<AudioSource>();
            I.ui.spatialBlend = 0f;
            I.ambA = go.AddComponent<AudioSource>();
            I.ambB = go.AddComponent<AudioSource>();
            foreach (var a in new[] { I.ambA, I.ambB }) { a.loop = true; a.spatialBlend = 0f; a.volume = 0f; }
            I.radio = go.AddComponent<AudioSource>();
            I.radio.loop = true;
            I.radio.spatialBlend = 0f;
        }

        public static AudioClip Clip(string name)
        {
            AudioClip c;
            if (clips.TryGetValue(name, out c)) return c;
            c = Resources.Load<AudioClip>("Sounds/" + name);
            if (c == null) c = Resources.Load<AudioClip>("Music/" + name);
            clips[name] = c;
            return c;
        }

        public static void Ui(string name, float vol = 1f)
        {
            if (I == null) return;
            var c = Clip(name);
            if (c != null) I.ui.PlayOneShot(c, vol * sfx);
        }

        public static void At(string name, Vector3 p, float vol = 1f, float pitch = 1f, float minDist = 5f)
        {
            if (I == null) return;
            var c = Clip(name);
            if (c == null) return;
            if (Cam.I != null && (Cam.I.transform.position - p).sqrMagnitude > 160f * 160f) return;
            AudioSource s = null;
            foreach (var a in I.pool) if (!a.isPlaying) { s = a; break; }
            if (s == null)
            {
                if (I.pool.Count >= 20) return;
                var go = new GameObject("sfx");
                go.transform.SetParent(I.transform, false);
                s = go.AddComponent<AudioSource>();
                s.spatialBlend = 1f;
                s.rolloffMode = AudioRolloffMode.Logarithmic;
                s.dopplerLevel = 0f;
                I.pool.Add(s);
            }
            s.transform.position = p;
            s.clip = c;
            s.minDistance = minDist;
            s.maxDistance = 200f;
            s.pitch = pitch;
            s.volume = vol * sfx;
            // long recordings (crash, explosion) are cut to a few seconds
            s.Play();
            if (c.length > 6f) s.SetScheduledEndTime(AudioSettings.dspTime + 4.0);
        }

        public static AudioSource Loop(string name, Transform t)
        {
            var c = Clip(name);
            if (c == null) return null;
            var go = new GameObject("loop_" + name);
            go.transform.SetParent(t, false);
            var s = go.AddComponent<AudioSource>();
            s.clip = c;
            s.loop = true;
            s.spatialBlend = 1f;
            s.minDistance = 6f;
            s.maxDistance = 120f;
            s.rolloffMode = AudioRolloffMode.Logarithmic;
            s.dopplerLevel = 0.3f;
            s.volume = 0f;
            s.Play();
            return s;
        }

        public static void Radio(bool on)
        {
            if (I == null) return;
            if (!on || station < 0) { I.radio.Stop(); return; }
            var c = Clip(Stations[station % Stations.Length]);
            if (c == null) return;
            if (I.radio.clip != c || !I.radio.isPlaying)
            {
                I.radio.clip = c;
                I.radio.time = Random.value * Mathf.Max(0f, c.length - 5f);
                I.radio.Play();
            }
        }

        public static void Menu(bool on)
        {
            if (I == null) return;
            if (on)
            {
                var c = Clip("music_menu");
                if (c != null && (I.radio.clip != c || !I.radio.isPlaying)) { I.radio.clip = c; I.radio.time = 0f; I.radio.Play(); }
            }
            else if (I.radio.clip != null && I.radio.clip.name == "music_menu") I.radio.Stop();
        }

        void Update()
        {
            bool menuTrack = radio.clip != null && radio.clip.name == "music_menu";
            radio.volume = music * (menuTrack ? 0.28f : 0.55f);
            if (Time.unscaledTime < nextAmb) { Fade(); return; }
            nextAmb = Time.unscaledTime + 1f;
            string want = "amb_city";
            if (Player.I != null && City.I != null)
            {
                Vector3 p = Player.I.transform.position;
                string zone = City.I.ZoneAt(p);
                float sea = Mathf.Abs(p.z - (-950f));
                if (Env.night > 0.6f) want = "amb_night";
                else if (zone.Contains("Bazar") || zone.Contains("Battala") || zone.Contains("Chowmuhani") || zone.Contains("Market")) want = "amb_market";
                else if (zone.Contains("Park") || zone.Contains("Kanan") || zone.Contains("Garden")) want = "amb_birds";
                if (!float.IsNaN(City.I.WaterLevel(p.x, p.z)) && City.I.WaterLevel(p.x, p.z) <= -0.9f && p.z < -800f) want = "amb_sea";
                if (Player.I.vehicle != null && Player.I.vehicle.spec.IsHeli && p.y > 30f) want = "amb_wind";
            }
            if (want != ambName)
            {
                ambName = want;
                var tmp = ambA; ambA = ambB; ambB = tmp;
                ambA.clip = Clip(want);
                if (ambA.clip != null) { ambA.time = Random.value * Mathf.Max(0f, ambA.clip.length - 2f); ambA.Play(); }
            }
            Fade();
        }

        void Fade()
        {
            float dt = Time.unscaledDeltaTime;
            float target = Game.I != null && Game.I.state == Game.S.Menu ? 0.15f : 0.35f;
            ambA.volume = Mathf.MoveTowards(ambA.volume, target * sfx, dt * 0.3f);
            ambB.volume = Mathf.MoveTowards(ambB.volume, 0f, dt * 0.3f);
            if (ambB.volume <= 0f && ambB.isPlaying) ambB.Stop();
        }
    }
}
