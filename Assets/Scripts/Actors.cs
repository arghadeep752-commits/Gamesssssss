using System.Collections.Generic;
using UnityEngine;

namespace Danga
{
    /// <summary>Anyone with a body: the player, people on the street, the police.</summary>
    public class Human : MonoBehaviour
    {
        public static readonly List<Human> all = new List<Human>();
        public Rig rig;
        public string model;
        public Color tint = Color.white;
        public float health = 100f, maxHealth = 100f, armor;
        public bool dead, police, isPlayer;
        public Vehicle vehicle;
        public Wpn weapon = Wpn.Fist;
        protected GameObject weaponGo;
        protected Transform muzzle;
        public float knocked, deadTime;
        protected CapsuleCollider hitBox;
        public bool looted;

        protected virtual void OnEnable() { all.Add(this); }
        protected virtual void OnDisable() { all.Remove(this); }

        public Vector3 Chest => transform.position + Vector3.up * 1.3f;
        public Vector3 Muzzle => muzzle != null ? muzzle.position : transform.position + Vector3.up * 1.35f + transform.forward * 0.45f;
        public WpnDef Def => Combat.Def(weapon);

        GameObject blob;

        public void SetModel(string m)
        {
            model = m;
            if (rig != null) Destroy(rig.gameObject);
            rig = Rig.Create(m, transform, tint);
            if (blob == null) blob = Models.Blob(transform, 1.1f, 1.1f, 0.6f);
            weaponGo = null;
            Equip(weapon, true);
        }

        protected void MakeHitBox(int layer)
        {
            var hb = new GameObject("hitbox");
            hb.layer = layer;
            hb.transform.SetParent(transform, false);
            hitBox = hb.AddComponent<CapsuleCollider>();
            hitBox.isTrigger = true;
            hitBox.radius = 0.32f;
            hitBox.height = 1.75f;
            hitBox.center = new Vector3(0f, 0.9f, 0f);
            var rb = hb.AddComponent<Rigidbody>();
            rb.isKinematic = true;
            rb.useGravity = false;
        }

        public void Equip(Wpn w, bool force = false)
        {
            if (w == weapon && !force && (weaponGo != null || Combat.Def(w).model == null)) return;
            weapon = w;
            if (weaponGo != null) Destroy(weaponGo);
            weaponGo = null;
            muzzle = null;
            var def = Combat.Def(w);
            if (def.model == null || rig == null || rig.data == null) return;
            Transform hand = rig.Bone("Hand.R");
            weaponGo = Models.Spawn("Weapons", def.model, hand, Color.white);
            Vector3 d = rig.data.handTip - rig.data.hand;
            if (d.sqrMagnitude < 1e-4f) d = Vector3.down;
            weaponGo.transform.localPosition = d * 0.45f;
            weaponGo.transform.localRotation = Quaternion.LookRotation(d.normalized, Vector3.forward);
            WSpec ws;
            if (Models.weapons.TryGetValue(def.model, out ws) && !def.melee)
            {
                muzzle = new GameObject("muzzle").transform;
                muzzle.SetParent(weaponGo.transform, false);
                muzzle.localPosition = ws.muzzle;
            }
        }

        public void ShowBody(bool on)
        {
            if (rig != null && rig.smr != null) rig.smr.enabled = on;
            if (blob != null) blob.SetActive(on && vehicle == null);
            if (weaponGo != null) weaponGo.SetActive(on);
        }

        public virtual void Hurt(float dmg, Vector3 from, Human by, bool melee)
        {
            if (dead) return;
            if (armor > 0f)
            {
                float a = Mathf.Min(armor, dmg * 0.7f);
                armor -= a;
                dmg -= a;
            }
            health -= dmg;
            if (rig != null && !(vehicle != null)) rig.Play("hit", 0.05f, 1f, true);
            if (health <= 0f) Die(by);
        }

        public virtual void Die(Human by)
        {
            if (dead) return;
            dead = true;
            health = 0f;
            deadTime = Time.time;
            if (rig != null) rig.Play("death", 0.1f);
            GameAudio.At(Random.value < 0.5f ? "grunt" : "body_fall", Chest, 0.9f, 1f, 5f);
            if (hitBox != null) hitBox.enabled = false;
        }

        public virtual void HitByVehicle(Vehicle v, float speed)
        {
            if (dead || vehicle != null || speed < 3f) return;
            Hurt(speed * 7f, v.transform.position, v.driver, false);
            knocked = 1.6f;
            Vector3 push = (transform.position - v.transform.position);
            push.y = 0f;
            transform.position += push.normalized * 0.8f;
            GameAudio.At("body_fall", Chest, 1f, 1f, 6f);
        }

        /// <summary>Turns the body smoothly to a direction.</summary>
        protected void FaceTowards(Vector3 dir, float degPerSec)
        {
            dir.y = 0f;
            if (dir.sqrMagnitude < 1e-4f) return;
            Quaternion want = Quaternion.LookRotation(dir);
            transform.rotation = Quaternion.RotateTowards(transform.rotation, want, degPerSec * Time.deltaTime);
        }
    }

    /// <summary>The player: walks, runs, jumps, swims, fights, shoots and drives.</summary>
    public class Player : Human
    {
        public static Player I;
        CharacterController cc;
        public Vector2 move;
        public bool fire, sprint, jump;
        float vy, nextShot, nextStep, aimUntil, reloadUntil, lastGround;
        public int money = 25000;
        public readonly HashSet<Wpn> owned = new HashSet<Wpn>();
        public readonly int[] ammo = new int[Combat.Defs.Length], clip = new int[Combat.Defs.Length];
        public bool swimming;
        public Human aimTarget;
        public Vehicle nearVehicle;
        string outfit = "player_casual";
        public float speedMul = 1f, gravity = -20f;

        public string Outfit => outfit;

        public static Player Create(Vector3 pos, float yaw)
        {
            var go = new GameObject("Player");
            go.layer = City.LayerPlayer;
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f));
            var p = go.AddComponent<Player>();
            I = p;
            p.isPlayer = true;
            p.cc = go.AddComponent<CharacterController>();
            p.cc.radius = 0.32f;
            p.cc.height = 1.74f;
            p.cc.center = new Vector3(0f, 0.89f, 0f);
            p.cc.stepOffset = 0.45f;
            p.cc.slopeLimit = 50f;
            p.cc.skinWidth = 0.04f;
            p.MakeHitBox(City.LayerPlayer);
            foreach (Wpn w in new[] { Wpn.Fist, Wpn.Bat, Wpn.Knife, Wpn.Revolver }) p.owned.Add(w);
            p.clip[(int)Wpn.Revolver] = 6;
            p.ammo[(int)Wpn.Revolver] = 36;
            p.SetModel(p.outfit);
            return p;
        }

        public void SetOutfit(string o, Color t)
        {
            outfit = o;
            tint = t;
            SetModel(o);
            if (vehicle != null) { ShowBody(vehicle.spec.open); SitAnim(); }
        }

        public void Teleport(Vector3 p, float yaw)
        {
            if (vehicle != null) ExitVehicle(true);
            cc.enabled = false;
            transform.SetPositionAndRotation(p, Quaternion.Euler(0f, yaw, 0f));
            cc.enabled = true;
            vy = 0f;
        }

        public void Revive()
        {
            dead = false;
            health = maxHealth;
            knocked = 0f;
            if (hitBox != null) hitBox.enabled = true;
            if (rig != null) rig.Play("idle", 0f);
        }

        public int TotalAmmo(Wpn w) { return clip[(int)w] + ammo[(int)w]; }

        public void NextWeapon(int dir)
        {
            int n = Combat.Defs.Length;
            int i = (int)weapon;
            for (int k = 0; k < n; k++)
            {
                i = (i + dir + n) % n;
                var w = (Wpn)i;
                if (owned.Contains(w) && (Combat.Def(w).melee || TotalAmmo(w) > 0)) { Equip(w); GameAudio.Ui("reload", 0.4f); return; }
            }
        }

        void Update()
        {
            if (Game.I == null || Game.I.state != Game.S.Play) return;
            if (dead)
            {
                if (Time.time - deadTime > 3.5f) Game.I.Wasted();
                return;
            }
            if (vehicle != null) { InVehicle(); return; }
            Vector3 camF = Cam.I != null ? Cam.I.Flat : transform.forward;
            Vector3 camR = new Vector3(camF.z, 0f, -camF.x);
            Vector3 wish = camR * move.x + camF * move.y;
            float mag = Mathf.Clamp01(wish.magnitude);
            if (knocked > 0f) { knocked -= Time.deltaTime; wish = Vector3.zero; mag = 0f; }

            bool grounded = cc.isGrounded;
            if (grounded) lastGround = Time.time;
            float wl = City.I != null ? City.I.WaterLevel(transform.position.x, transform.position.z) : float.NaN;
            swimming = !float.IsNaN(wl) && transform.position.y < wl - 1.05f;
            bool running = sprint && mag > 0.5f && !swimming;
            float spd = swimming ? 1.6f : running ? 6.6f : mag > 0.75f ? 4.2f : 1.7f;
            spd *= speedMul;
            Vector3 vel = wish.normalized * spd * mag;
            if (swimming)
            {
                vy = Mathf.MoveTowards(vy, (wl - 1.0f - transform.position.y) * 3f, 20f * Time.deltaTime);
            }
            else if (grounded)
            {
                vy = -2f;
                if (jump && knocked <= 0f) { vy = 6.2f * (gravity > -10f ? 1.6f : 1f); jump = false; GameAudio.At("grunt", Chest, 0.25f, 1.3f, 3f); }
            }
            else vy += gravity * Time.deltaTime;
            jump = false;
            vel.y = vy;
            cc.Move(vel * Time.deltaTime);

            // aiming: guns turn the body towards the target (or where the camera looks)
            WpnDef def = Def;
            bool aiming = fire || Time.time < aimUntil;
            aimTarget = aiming && !def.melee ? FindTarget(def.range) : null;
            if (aiming && !swimming)
            {
                Vector3 look = aimTarget != null ? aimTarget.transform.position - transform.position : camF;
                FaceTowards(look, 900f);
            }
            else if (mag > 0.05f) FaceTowards(wish, swimming ? 240f : 720f);

            if (fire && !swimming && knocked <= 0f) TryAttack(def);

            // animation
            string clip;
            float aspd = 1f;
            if (knocked > 0f) clip = "hit";
            else if (swimming) clip = "swim";
            else if (!grounded && Time.time - lastGround > 0.25f) clip = vy > 0f ? "jump" : "fall";
            else if (mag < 0.05f) clip = "idle";
            else if (running) { clip = "sprint"; aspd = speedMul; }
            else if (mag > 0.75f) { clip = "run"; aspd = speedMul; }
            else { clip = "walk"; aspd = Mathf.Lerp(0.7f, 1.1f, mag); }
            if (rig != null)
            {
                if (rig.Current != "punch" && rig.Current != "swing" || rig.Finished) rig.Play(clip, 0.18f, aspd);
                if (!def.melee && aiming && !swimming) rig.Upper(def.rifle ? "aim_rifle" : "aim_pistol", 1f);
                else rig.Upper(null);
            }
            // footsteps
            if (grounded && mag > 0.1f && !swimming && Time.time > nextStep)
            {
                nextStep = Time.time + (running ? 0.28f : mag > 0.75f ? 0.34f : 0.52f) / speedMul;
                GameAudio.At("footstep_" + Random.Range(1, 7), transform.position, running ? 0.55f : 0.35f, 0.9f + Random.value * 0.2f, 2f);
            }
            // things nearby
            nearVehicle = FindVehicle(4.2f);
            LootBodies();
            if (transform.position.y < -40f) Teleport(Game.I.SpawnPoint(), 0f);
        }

        void TryAttack(WpnDef def)
        {
            if (Time.time < nextShot || Time.time < reloadUntil) return;
            nextShot = Time.time + 1f / def.rate;
            aimUntil = Time.time + 1.2f;
            if (def.melee)
            {
                if (rig != null) rig.Play(def.id == Wpn.Fist ? "punch" : "swing", 0.06f, 1.2f, true);
                StartCoroutine(MeleeHit(def, 0.18f));
                return;
            }
            int w = (int)def.id;
            if (clip[w] <= 0)
            {
                if (ammo[w] <= 0) { GameAudio.At("empty_click", Muzzle, 0.8f, 1f, 3f); NextWeapon(-1); return; }
                int take = Mathf.Min(def.mag, ammo[w]);
                ammo[w] -= take;
                clip[w] = take;
                reloadUntil = Time.time + 1.3f;
                GameAudio.At("reload", Muzzle, 0.8f, 1.2f, 3f);
                return;
            }
            clip[w]--;
            Vector3 aim = aimTarget != null ? aimTarget.Chest + Random.insideUnitSphere * 0.15f
                                            : Muzzle + (Cam.I != null ? Cam.I.transform.forward : transform.forward) * def.range;
            if (rig != null) { rig.Upper(def.rifle ? "shoot_rifle" : "shoot_pistol", 1f); rig.RestartUpper(); }
            Combat.Fire(this, def, Muzzle, aim, 0f);
            Cam.Shake(def.id == Wpn.Shotgun ? 0.35f : 0.12f);
        }

        System.Collections.IEnumerator MeleeHit(WpnDef def, float delay)
        {
            yield return new WaitForSeconds(delay);
            if (Combat.Melee(this, def)) Cam.Shake(0.1f);
        }

        Human FindTarget(float range)
        {
            Vector3 f = Cam.I != null ? Cam.I.Flat : transform.forward;
            Human best = null;
            float bs = 1e9f;
            foreach (var h in all)
            {
                if (h == this || h.dead || h.vehicle != null && !h.vehicle.spec.open) continue;
                Vector3 d = h.transform.position - transform.position;
                float dist = d.magnitude;
                if (dist > range || dist < 0.5f) continue;
                float ang = Vector3.Angle(f, new Vector3(d.x, 0f, d.z));
                if (ang > 40f) continue;
                float score = dist * (1f + ang / 20f) * (h.police && Wanted.stars > 0 ? 0.6f : 1f);
                if (score >= bs) continue;
                if (Physics.Linecast(Chest, h.Chest, 1 << City.LayerWorld, QueryTriggerInteraction.Ignore)) continue;
                bs = score;
                best = h;
            }
            return best;
        }

        Vehicle FindVehicle(float r)
        {
            Vehicle best = null;
            float bd = r;
            foreach (var v in Vehicle.all)
            {
                if (v.wrecked || v.driver == this) continue;
                Vector3 local = v.transform.InverseTransformPoint(transform.position);
                Vector3 half = new Vector3(v.spec.width * 0.5f, v.spec.height, v.spec.length * 0.5f);
                Vector3 q = new Vector3(Mathf.Max(0f, Mathf.Abs(local.x) - half.x), 0f, Mathf.Max(0f, Mathf.Abs(local.z) - half.z));
                float d = q.magnitude;
                if (d < bd) { bd = d; best = v; }
            }
            return best;
        }

        void LootBodies()
        {
            foreach (var h in all)
            {
                if (!h.dead || h.looted || h == this) continue;
                if ((h.transform.position - transform.position).sqrMagnitude > 2.2f) continue;
                h.looted = true;
                int cash = h.police ? Random.Range(300, 900) : Random.Range(40, 650);
                AddMoney(cash);
            }
        }

        public void AddMoney(int amount)
        {
            money = Mathf.Max(0, money + amount);
            if (amount > 0) { GameAudio.Ui("cash", 0.6f); Hud.Toast("+ ₹ " + Hud.Rupees(amount), new Color(0.4f, 1f, 0.45f)); }
        }

        // ------------------------------------------------------------------ vehicles
        public void EnterVehicle(Vehicle v)
        {
            if (v == null || v.wrecked) return;
            if (v.driver != null && v.driver != this)
            {
                Human d = v.driver;
                v.Eject();
                if (d is Ped) ((Ped)d).Flee(transform.position, 12f);
                if (v.spec.police || (Wanted.CopsNear(transform.position, 40f))) Wanted.Crime(1.2f, transform.position);
            }
            Debug.Log("[DG] enter " + v.spec.name);
            vehicle = v;
            v.TakeDriver(this);
            cc.enabled = false;
            hitBox.enabled = false;
            transform.SetParent(v.transform, false);
            transform.localPosition = v.SeatPos;
            transform.localRotation = Quaternion.identity;
            ShowBody(v.spec.open);
            SitAnim();
            GameAudio.At(v.spec.open ? "engine_bike" : "car_door", transform.position, 0.6f, 1f, 4f);
            Game.I.OnEnterVehicle(v);
        }

        void SitAnim()
        {
            if (rig == null || vehicle == null) return;
            rig.Upper(null);
            rig.Play(vehicle.spec.IsBike ? "ride" : "drive", 0.1f);
        }

        public void ExitVehicle(bool instant = false)
        {
            if (vehicle == null) return;
            Vehicle v = vehicle;
            Debug.Log("[DG] exit " + v.spec.name + (instant ? " (thrown or teleported)" : ""));
            Vector3 exit = v.transform.TransformPoint(v.spec.exit);
            if (!instant)
            {
                // the driver's door is on the right; use the left if something is in the way
                if (Physics.CheckCapsule(exit + Vector3.up * 0.5f, exit + Vector3.up * 1.5f, 0.3f, 1 << City.LayerWorld | 1 << City.LayerVehicle, QueryTriggerInteraction.Ignore))
                    exit = v.transform.TransformPoint(new Vector3(-v.spec.exit.x, v.spec.exit.y, v.spec.exit.z));
            }
            v.ReleaseDriver();
            vehicle = null;
            transform.SetParent(null, true);
            float gy = City.I != null ? City.I.Ground(exit, exit.y) : exit.y;
            if (!float.IsNaN(City.I.WaterLevel(exit.x, exit.z)) && gy < City.I.WaterLevel(exit.x, exit.z)) gy = Mathf.Max(gy, exit.y);
            transform.SetPositionAndRotation(new Vector3(exit.x, Mathf.Max(gy, exit.y - 3f) + 0.05f, exit.z), Quaternion.Euler(0f, v.transform.eulerAngles.y, 0f));
            cc.enabled = true;
            hitBox.enabled = true;
            ShowBody(true);
            if (rig != null) rig.Play("idle", 0.1f);
            vy = 0f;
            Game.I.OnExitVehicle(v);
        }

        void InVehicle()
        {
            transform.localPosition = vehicle.SeatPos;
            transform.localRotation = Quaternion.identity;
            if (vehicle.wrecked && vehicle.burning > 2f) { ExitVehicle(); return; }
            if (fire && vehicle.spec.open && !Def.melee && Time.time >= nextShot)
            {
                // drive-by on bikes and autos
                aimTarget = FindTarget(Def.range);
                if (aimTarget != null) TryAttack(Def);
            }
        }

        public override void Hurt(float dmg, Vector3 from, Human by, bool melee)
        {
            if (Game.I != null && Game.I.godMode) return;
            base.Hurt(dmg, from, by, melee);
            Hud.Flash();
        }

        public override void Die(Human by)
        {
            if (vehicle != null) ExitVehicle(true);
            base.Die(by);
        }

        public override void HitByVehicle(Vehicle v, float speed)
        {
            if (v.driver == this) return;
            base.HitByVehicle(v, speed);
        }
    }

    /// <summary>People of Agartala: walk the footpaths, react to danger, sometimes fight back; police officers chase and shoot.</summary>
    public class Ped : Human
    {
        public enum St { Walk, Flee, Cower, Fight, Chase, Dead, Ride, Idle }
        public St st = St.Walk;
        public int path;
        public float s, dir = 1f, side, speed = 1.3f, until, nextShot;
        Vector3 threat;
        float groundY, nextGround;
        public bool fearless;

        public static Ped Create(string model, Vector3 pos, float yaw, bool cop)
        {
            var go = new GameObject(cop ? "Police" : "Ped");
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f));
            var p = go.AddComponent<Ped>();
            p.police = cop;
            p.tint = cop ? Color.white : Color.HSVToRGB(Random.value, Random.Range(0f, 0.25f), Random.Range(0.85f, 1.05f));
            p.SetModel(model);
            p.MakeHitBox(City.LayerPed);
            p.groundY = pos.y;
            p.side = Random.Range(-0.9f, 0.9f);
            p.speed = Random.Range(1.15f, 1.5f) * (model == "npc_oldman" ? 0.75f : 1f);
            p.fearless = cop || (model == "npc_man" || model == "npc_student") && Random.value < 0.3f;
            if (cop) { p.Equip(Wpn.Pistol); p.health = p.maxHealth = 120f; }
            return p;
        }

        public void Flee(Vector3 from, float time)
        {
            if (dead || st == St.Ride || police) return;
            threat = from;
            if (st != St.Flee && Random.value < 0.25f) GameAudio.At("scream", Chest, 0.7f, Random.Range(0.9f, 1.2f), 6f);
            st = Random.value < 0.2f ? St.Cower : St.Flee;
            until = Time.time + time * Random.Range(0.8f, 1.3f);
        }

        public void Chase()
        {
            if (dead || st == St.Ride) return;
            st = St.Chase;
        }

        public override void Hurt(float dmg, Vector3 from, Human by, bool melee)
        {
            base.Hurt(dmg, from, by, melee);
            if (dead) return;
            if (by != null && by.isPlayer)
            {
                if (police) { Wanted.Crime(1.5f, transform.position, true); Chase(); }
                else if (melee && fearless) { st = St.Fight; until = Time.time + 20f; }
                else Flee(from, 10f);
                if (!police) Wanted.Crime(0.25f, transform.position);
            }
        }

        public override void Die(Human by)
        {
            base.Die(by);
            st = St.Dead;
            if (by != null && by.isPlayer) Wanted.Crime(police ? 2.2f : 0.9f, transform.position, police);
            Traffic.Panic(transform.position, 25f);
        }

        void Update()
        {
            if (Game.I == null || Game.I.state == Game.S.Paused) return;
            float dt = Time.deltaTime;
            Player pl = Player.I;
            float dp = pl != null ? Vector3.Distance(transform.position, pl.transform.position) : 0f;
            float dc = Cam.I != null ? Vector3.Distance(transform.position, Cam.I.transform.position) : dp;
            if (rig != null) rig.updateEvery = dc < 25f ? 0f : dc < 60f ? 0.066f : 0.15f;
            if (st == St.Dead || dead)
            {
                if (vehicle != null) vehicle.Eject();
                return;
            }
            if (st == St.Ride) return;
            if (knocked > 0f) { knocked -= dt; Anim("hit", 1f); return; }
            Vector3 vel = Vector3.zero;
            switch (st)
            {
                case St.Walk:
                    vel = WalkPath(dt);
                    break;
                case St.Idle:
                    Anim("idle", 1f);
                    if (Time.time > until) st = St.Walk;
                    break;
                case St.Flee:
                {
                    Vector3 away = transform.position - threat;
                    away.y = 0f;
                    if (away.sqrMagnitude < 0.01f) away = transform.forward;
                    vel = away.normalized * 5.2f;
                    if (Time.time > until) { st = St.Idle; until = Time.time + 2f; Traffic.ReattachPed(this); }
                    break;
                }
                case St.Cower:
                    Anim("cower", 1f);
                    if (Time.time > until) { st = St.Idle; until = Time.time + 1f; }
                    break;
                case St.Fight:
                case St.Chase:
                    vel = Pursue(dt, pl, dp);
                    break;
            }
            if (vel.sqrMagnitude > 0.01f)
            {
                Vector3 p = transform.position + vel * dt;
                if (st != St.Walk)
                {
                    if (Time.time > nextGround)
                    {
                        nextGround = Time.time + 0.25f;
                        groundY = City.I.Ground(p, groundY);
                    }
                    // stay out of buildings
                    if (Physics.Raycast(transform.position + Vector3.up * 0.8f, vel.normalized, 0.6f, 1 << City.LayerWorld, QueryTriggerInteraction.Ignore))
                    {
                        vel = Quaternion.Euler(0f, 90f, 0f) * vel;
                        p = transform.position + vel * dt;
                    }
                    p.y = Mathf.Lerp(transform.position.y, groundY, 10f * dt);
                }
                transform.position = p;
                FaceTowards(vel, 540f);
                float sp = new Vector3(vel.x, 0f, vel.z).magnitude;
                Anim(sp > 4.5f ? "sprint" : sp > 2.4f ? "run" : "walk", sp > 4.5f ? 1f : sp > 2.4f ? sp / 3.9f : sp / 1.45f);
            }
            else if (st == St.Walk) Anim("idle", 1f);
        }

        void Anim(string clip, float spd)
        {
            if (rig == null) return;
            if ((rig.Current == "punch" || rig.Current == "hit") && !rig.Finished) return;
            rig.Play(clip, 0.2f, spd);
        }

        Vector3 WalkPath(float dt)
        {
            Path w = Traffic.I != null && path >= 0 && path < Traffic.I.walks.Length ? Traffic.I.walks[path] : null;
            if (w == null) { st = St.Idle; until = Time.time + 999f; return Vector3.zero; }
            s += dir * speed * dt;
            if (s > w.len || s < 0f) Traffic.I.NextWalk(this, w);
            w = Traffic.I.walks[path];
            Vector3 d;
            Vector3 c = w.At(s, out d);
            Vector3 right = new Vector3(d.z, 0f, -d.x);
            Vector3 target = c + right * side * dir;
            target.y = c.y;
            Vector3 vel = (target - transform.position) / Mathf.Max(dt, 1e-3f);
            if (vel.magnitude > speed * 3f) vel = vel.normalized * speed * 3f;
            if ((target - transform.position).magnitude > 6f) { transform.position = target; return Vector3.zero; }
            transform.position = Vector3.Lerp(transform.position, target, 1f);
            FaceTowards(d * dir, 360f);
            Anim("walk", speed / 1.45f);
            return Vector3.zero;
        }

        Vector3 Pursue(float dt, Player pl, float dist)
        {
            if (pl == null || pl.dead) { st = St.Idle; until = Time.time + 3f; return Vector3.zero; }
            if (st == St.Fight && Time.time > until) { st = St.Walk; Traffic.ReattachPed(this); return Vector3.zero; }
            if (police && Wanted.stars == 0) { st = St.Idle; until = Time.time + 4f; Traffic.ReattachPed(this); return Vector3.zero; }
            Vector3 to = pl.transform.position - transform.position;
            to.y = 0f;
            FaceTowards(to, 540f);
            if (police)
            {
                bool see = dist < 32f && !Physics.Linecast(Chest, pl.Chest, 1 << City.LayerWorld, QueryTriggerInteraction.Ignore);
                if (see) Wanted.Seen();
                if (Wanted.stars <= 1 && dist < 1.7f && pl.vehicle == null) { Game.I.Busted(); return Vector3.zero; }
                if (see && dist < 24f && (Wanted.stars >= 2 || pl.weapon != Wpn.Fist))
                {
                    if (rig != null) rig.Upper("aim_pistol", 1f);
                    if (Time.time > nextShot)
                    {
                        nextShot = Time.time + Random.Range(0.7f, 1.3f);
                        Vector3 aim = pl.vehicle != null ? pl.vehicle.transform.position + Vector3.up : pl.Chest;
                        Combat.Fire(this, Combat.Def(Wpn.Pistol), Muzzle, aim, 5f - Mathf.Min(3f, Wanted.stars));
                    }
                    if (dist < 9f) return Vector3.zero;
                    return to.normalized * 2.0f;
                }
                if (rig != null) rig.Upper(null);
                return to.normalized * (dist > 6f ? 5.4f : 2.5f);
            }
            if (dist < 1.3f)
            {
                if (Time.time > nextShot)
                {
                    nextShot = Time.time + 1.1f;
                    if (rig != null) rig.Play("punch", 0.06f, 1.1f, true);
                    if (Random.value < 0.6f) pl.Hurt(6f, transform.position, this, true);
                    GameAudio.At("punch", Chest, 0.8f, 1f, 4f);
                }
                return Vector3.zero;
            }
            return to.normalized * 4.0f;
        }
    }
}
