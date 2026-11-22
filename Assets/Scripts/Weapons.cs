using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Danga
{
    public enum Wpn { Fist, Bat, Knife, Revolver, Pistol, Smg, Shotgun, Ak47, Sniper }

    public class WpnDef
    {
        public Wpn id;
        public string name, model, icon, sound;
        public bool melee, rifle;
        public float damage, range, rate, spread;
        public int pellets = 1, mag, price, ammoPrice, ammoPack;
    }

    /// <summary>The weapons, shooting, melee hits, explosions and their flashes.</summary>
    public static class Combat
    {
        public static readonly WpnDef[] Defs =
        {
            new WpnDef { id = Wpn.Fist, name = "Fists", icon = "fist", sound = "punch", melee = true, damage = 9, range = 1.5f, rate = 2.2f },
            new WpnDef { id = Wpn.Bat, name = "Baseball Bat", model = "bat", icon = "bat", sound = "bat_hit", melee = true, damage = 28, range = 1.9f, rate = 1.4f, price = 1500 },
            new WpnDef { id = Wpn.Knife, name = "Knife", model = "knife", icon = "knife", sound = "knife_slash", melee = true, damage = 38, range = 1.6f, rate = 1.8f, price = 900 },
            new WpnDef { id = Wpn.Revolver, name = "Revolver", model = "revolver", icon = "revolver", sound = "shot_revolver", damage = 55, range = 70, rate = 1.5f, spread = 1.2f, mag = 6, price = 8000, ammoPrice = 300, ammoPack = 18 },
            new WpnDef { id = Wpn.Pistol, name = "Pistol", model = "pistol", icon = "pistol", sound = "shot_pistol", damage = 30, range = 60, rate = 3.5f, spread = 2f, mag = 15, price = 15000, ammoPrice = 450, ammoPack = 30 },
            new WpnDef { id = Wpn.Smg, name = "Carbine", model = "smg", icon = "smg", sound = "shot_smg", rifle = true, damage = 22, range = 75, rate = 10f, spread = 3.2f, mag = 30, price = 45000, ammoPrice = 900, ammoPack = 90 },
            new WpnDef { id = Wpn.Shotgun, name = "Shotgun", model = "shotgun", icon = "shotgun", sound = "shot_shotgun", rifle = true, damage = 15, range = 32, rate = 1.1f, spread = 6.5f, pellets = 8, mag = 6, price = 60000, ammoPrice = 700, ammoPack = 18 },
            new WpnDef { id = Wpn.Ak47, name = "AK-47", model = "ak47", icon = "ak47", sound = "shot_smg", rifle = true, damage = 32, range = 90, rate = 8f, spread = 2.4f, mag = 30, price = 85000, ammoPrice = 1200, ammoPack = 90 },
            new WpnDef { id = Wpn.Sniper, name = "Sniper Rifle", model = "sniper", icon = "sniper", sound = "shot_revolver", rifle = true, damage = 120, range = 160, rate = 0.8f, spread = 0.3f, mag = 5, price = 120000, ammoPrice = 1500, ammoPack = 15 },
        };

        public static WpnDef Def(Wpn w) { return Defs[(int)w]; }

        static readonly RaycastHit[] hits = new RaycastHit[24];
        public const int ShotMask = (1 << City.LayerWorld) | (1 << City.LayerVehicle) | (1 << City.LayerPed) | (1 << City.LayerPlayer);

        /// <summary>One shot (or one shotgun blast) from 'origin' towards 'aim'.</summary>
        public static void Fire(Human shooter, WpnDef w, Vector3 origin, Vector3 aim, float extraSpread = 0f)
        {
            Fx.Flash(origin, 0.35f, new Color(1f, 0.75f, 0.35f), 0.06f);
            GameAudio.At(w.sound, origin, 1f, 0.95f + Random.value * 0.1f, 8f);
            for (int p = 0; p < w.pellets; p++)
            {
                Vector3 dir = (aim - origin).normalized;
                float sp = w.spread + extraSpread;
                dir = Quaternion.Euler(Random.Range(-sp, sp), Random.Range(-sp, sp), 0f) * dir;
                int n = Physics.RaycastNonAlloc(origin, dir, hits, w.range, ShotMask, QueryTriggerInteraction.Collide);
                float best = 1e9f;
                int bi = -1;
                for (int i = 0; i < n; i++)
                {
                    if (hits[i].distance >= best) continue;
                    var h = hits[i].collider.GetComponentInParent<Human>();
                    if (h != null && (h == shooter || h.dead)) continue;
                    var v = hits[i].collider.GetComponentInParent<Vehicle>();
                    if (v != null && shooter != null && v == shooter.vehicle) continue;
                    if (hits[i].collider.isTrigger && h == null) continue;
                    best = hits[i].distance;
                    bi = i;
                }
                if (bi < 0) continue;
                RaycastHit hit = hits[bi];
                var hh = hit.collider.GetComponentInParent<Human>();
                var vv = hit.collider.GetComponentInParent<Vehicle>();
                if (hh != null) hh.Hurt(w.damage, origin, shooter, false);
                else if (vv != null) { vv.Damage(w.damage * 0.6f, shooter); Fx.Flash(hit.point, 0.25f, new Color(1f, 0.85f, 0.5f), 0.08f); }
                else
                {
                    Fx.Flash(hit.point + hit.normal * 0.05f, 0.18f, new Color(1f, 0.9f, 0.7f), 0.07f);
                    if (p == 0) GameAudio.At("bullet_impact", hit.point, 0.5f, 1f, 4f);
                }
            }
            Wanted.Noise(origin, shooter);
        }

        /// <summary>A punch, bat swing or knife slash: hits the first person or vehicle in front.</summary>
        public static bool Melee(Human attacker, WpnDef w)
        {
            Vector3 c = attacker.transform.position + attacker.transform.forward * (w.range * 0.6f) + Vector3.up * 1.0f;
            var cols = Physics.OverlapSphere(c, 0.85f, ShotMask, QueryTriggerInteraction.Collide);
            Human target = null;
            Vehicle vt = null;
            float bd = 1e9f;
            foreach (var col in cols)
            {
                var h = col.GetComponentInParent<Human>();
                if (h != null && h != attacker && !h.dead)
                {
                    float d = Vector3.Distance(h.transform.position, attacker.transform.position);
                    if (d < bd) { bd = d; target = h; }
                }
                else if (h == null && vt == null) vt = col.GetComponentInParent<Vehicle>();
            }
            if (target != null)
            {
                target.Hurt(w.damage * Random.Range(0.85f, 1.15f), attacker.transform.position, attacker, true);
                GameAudio.At(w.sound, c, 1f, 0.9f + Random.value * 0.2f, 5f);
                return true;
            }
            if (vt != null && w.id == Wpn.Bat) { vt.Damage(8f, attacker); GameAudio.At("bat_hit", c, 0.8f, 0.8f, 5f); return true; }
            GameAudio.At("swing", c, 0.6f, 1f, 4f);
            return false;
        }

        public static void Explode(Vector3 p, float radius, float damage, Human by)
        {
            Fx.Flash(p + Vector3.up, 6f, new Color(1f, 0.55f, 0.2f), 0.5f);
            Fx.Flash(p + Vector3.up * 2f, 9f, new Color(1f, 0.35f, 0.1f), 0.9f);
            GameAudio.At("explosion", p, 1f, 1f, 25f);
            var cols = Physics.OverlapSphere(p, radius, (1 << City.LayerVehicle) | (1 << City.LayerPed) | (1 << City.LayerPlayer), QueryTriggerInteraction.Collide);
            var done = new HashSet<Object>();
            foreach (var c in cols)
            {
                var h = c.GetComponentInParent<Human>();
                if (h != null && done.Add(h))
                {
                    float k = 1f - Vector3.Distance(h.transform.position, p) / radius;
                    h.Hurt(damage * Mathf.Clamp01(k + 0.2f), p, by, false);
                }
                var v = c.GetComponentInParent<Vehicle>();
                if (v != null && done.Add(v))
                {
                    if (v.rb != null && !v.rb.isKinematic) v.rb.AddExplosionForce(v.spec.mass * 12f, p, radius, 1.5f, ForceMode.Impulse);
                    v.Damage(damage * 6f, by);
                }
            }
            Cam.Shake(0.6f);
        }
    }

    /// <summary>Short-lived camera-facing glows: muzzle flashes, sparks, explosions.</summary>
    public class Fx : MonoBehaviour
    {
        static Fx inst;
        static Material mat;
        static Mesh quad;
        readonly List<GameObject> pool = new List<GameObject>();
        readonly List<float> until = new List<float>();
        readonly List<float> life = new List<float>();
        readonly List<float> size0 = new List<float>();
        readonly List<Color> cols = new List<Color>();
        MaterialPropertyBlock mpb;

        public static void Init(Transform parent)
        {
            var go = new GameObject("fx");
            go.transform.SetParent(parent, false);
            inst = go.AddComponent<Fx>();
            inst.mpb = new MaterialPropertyBlock();
            Shader s = Shader.Find("Danga/GlowBillboard");
            mat = new Material(s);
            mat.SetFloat("_NightOnly", 0f);
            var t = Resources.Load<Texture2D>("UI/glow");
            if (t != null) mat.SetTexture("_MainTex", t);
            quad = new Mesh { name = "glow" };
            quad.vertices = new Vector3[4];
            quad.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            quad.uv2 = new[] { Vector2.right, Vector2.right, Vector2.right, Vector2.right };
            quad.colors32 = new[] { new Color32(255, 255, 255, 255), new Color32(255, 255, 255, 255), new Color32(255, 255, 255, 255), new Color32(255, 255, 255, 255) };
            quad.triangles = new[] { 0, 2, 1, 0, 3, 2 };
            quad.bounds = new Bounds(Vector3.zero, Vector3.one * 20f);
        }

        public static void Flash(Vector3 p, float size, Color c, float time)
        {
            if (inst == null) return;
            inst.Add(p, size, c, time);
        }

        void Add(Vector3 p, float size, Color c, float time)
        {
            int i = until.FindIndex(u => u < Time.time);
            if (i < 0)
            {
                if (pool.Count >= 40) return;
                var go = new GameObject("flash");
                go.transform.SetParent(transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = quad;
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterial = mat;
                r.shadowCastingMode = ShadowCastingMode.Off;
                pool.Add(go);
                until.Add(0);
                life.Add(0);
                size0.Add(0);
                cols.Add(Color.white);
                i = pool.Count - 1;
            }
            var g = pool[i];
            g.SetActive(true);
            g.transform.position = p;
            until[i] = Time.time + time;
            life[i] = time;
            size0[i] = size;
            cols[i] = c;
            mpb.SetColor("_Color", c);
            mpb.SetFloat("_Scale", size);
            g.GetComponent<MeshRenderer>().SetPropertyBlock(mpb);
        }

        void Update()
        {
            for (int i = 0; i < pool.Count; i++)
            {
                if (!pool[i].activeSelf) continue;
                float left = until[i] - Time.time;
                if (left <= 0f) { pool[i].SetActive(false); continue; }
                mpb.SetColor("_Color", cols[i]);
                mpb.SetFloat("_Scale", size0[i] * (0.6f + 0.4f * left / life[i]));
                pool[i].GetComponent<MeshRenderer>().SetPropertyBlock(mpb);
            }
        }
    }
}
