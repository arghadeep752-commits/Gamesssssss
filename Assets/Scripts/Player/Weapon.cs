using UnityEngine;

namespace ZombieStrike
{
    /// <summary>The assault rifle: first-person model, hitscan shooting, recoil, reload and effects.</summary>
    public class Weapon : MonoBehaviour
    {
        public const int MagSize = 30;
        public const int MaxReserve = 300;
        const float FireRate = 9.5f;
        const float ReloadTime = 1.7f;
        const float BodyDamage = 28f;
        const float HeadMultiplier = 2.6f;
        const float Range = 90f;

        public int Mag { get; private set; }
        public int Reserve { get; private set; }
        public bool Reloading { get; private set; }
        public float ReloadProgress { get { return Reloading ? Mathf.Clamp01(reloadT / ReloadTime) : 0f; } }
        public bool OnTarget { get; private set; }
        public float Spread { get; private set; }
        public int ShotsFired { get; private set; }
        public int ShotsHit { get; private set; }

        PlayerController owner;
        Camera cam;
        Transform rig, model, muzzle, magazine, flash;
        Light flashLight;
        readonly Vector3 rigBase = new Vector3(0.21f, -0.235f, 0.44f);
        Vector3 magBase;
        float nextFire, reloadT, bloom, kickBack, kickUp, flashT, swayX, swayY, bobT, sprintBlend, emptyClickAt;
        float autoReloadAt = -1f;
        int shotIndex;

        public void Build(PlayerController p, Camera c)
        {
            owner = p;
            cam = c;
            Mag = MagSize;
            Reserve = 150;

            int L = Layers.Weapon;
            rig = new GameObject("WeaponRig").transform;
            rig.SetParent(cam.transform, false);
            rig.localPosition = rigBase;
            rig.gameObject.layer = L;
            model = new GameObject("Rifle").transform;
            model.SetParent(rig, false);
            model.gameObject.layer = L;
            model.localScale = Vector3.one * 0.85f;

            Material metal = Art.Lit(new Color(0.24f, 0.25f, 0.27f), "metal");
            Material dark = Art.Lit(new Color(0.1f, 0.1f, 0.11f));
            Material polymer = Art.Lit(new Color(0.17f, 0.18f, 0.16f), "grime");
            Material tan = Art.Lit(new Color(0.55f, 0.47f, 0.33f), "grime");
            Material glove = Art.Lit(new Color(0.13f, 0.13f, 0.13f), "grime");
            Material sleeve = Art.Lit(new Color(0.27f, 0.3f, 0.21f), "grime");

            Part(metal, new Vector3(0f, 0f, 0.02f), new Vector3(0.065f, 0.095f, 0.34f), Vector3.zero);
            Part(dark, new Vector3(0f, 0.058f, 0.02f), new Vector3(0.04f, 0.022f, 0.3f), Vector3.zero);
            Part(tan, new Vector3(0f, 0f, 0.21f), new Vector3(0.072f, 0.078f, 0.2f), Vector3.zero);
            Part(dark, new Vector3(0f, 0.012f, 0.32f), new Vector3(0.028f, 0.028f, 0.28f), Vector3.zero);
            Part(dark, new Vector3(0f, 0.012f, 0.46f), new Vector3(0.042f, 0.042f, 0.05f), Vector3.zero);
            Part(dark, new Vector3(0f, 0.062f, 0.3f), new Vector3(0.012f, 0.04f, 0.012f), Vector3.zero);
            magazine = Part(metal, new Vector3(0f, -0.105f, 0.07f), new Vector3(0.048f, 0.14f, 0.075f), new Vector3(12f, 0f, 0f)).transform;
            magBase = magazine.localPosition;
            Part(polymer, new Vector3(0f, -0.085f, -0.075f), new Vector3(0.045f, 0.1f, 0.055f), new Vector3(-18f, 0f, 0f));
            Part(tan, new Vector3(0f, -0.015f, -0.24f), new Vector3(0.055f, 0.085f, 0.17f), Vector3.zero);
            Part(dark, new Vector3(0f, -0.02f, -0.33f), new Vector3(0.06f, 0.1f, 0.02f), Vector3.zero);
            Part(dark, new Vector3(0f, 0.088f, 0.03f), new Vector3(0.036f, 0.036f, 0.075f), Vector3.zero);
            // hands and sleeves
            Part(glove, new Vector3(0.02f, -0.1f, -0.07f), new Vector3(0.075f, 0.075f, 0.1f), new Vector3(-10f, 0f, 0f));
            Part(sleeve, new Vector3(0.075f, -0.165f, -0.25f), new Vector3(0.088f, 0.088f, 0.27f), new Vector3(-16f, -12f, 0f));
            Part(glove, new Vector3(-0.015f, -0.055f, 0.22f), new Vector3(0.075f, 0.06f, 0.11f), Vector3.zero);
            Part(sleeve, new Vector3(-0.125f, -0.13f, 0.08f), new Vector3(0.088f, 0.088f, 0.3f), new Vector3(-10f, 38f, 0f));

            muzzle = new GameObject("Muzzle").transform;
            muzzle.SetParent(model, false);
            muzzle.localPosition = new Vector3(0f, 0.012f, 0.5f);

            var flashGo = Art.MeshObject(model, Art.Quad(new Color(1f, 0.85f, 0.55f, 1f)), Art.Additive("flare"),
                new Vector3(0f, 0.012f, 0.53f), Vector3.zero, Vector3.one * 0.28f, L);
            flash = flashGo.transform;
            flashGo.SetActive(false);

            var lightGo = new GameObject("MuzzleLight");
            lightGo.transform.SetParent(cam.transform, false);
            lightGo.transform.localPosition = new Vector3(0.15f, -0.1f, 0.9f);
            flashLight = lightGo.AddComponent<Light>();
            flashLight.type = LightType.Point;
            flashLight.range = 8f;
            flashLight.intensity = 2.4f;
            flashLight.color = new Color(1f, 0.72f, 0.38f);
            flashLight.shadows = LightShadows.None;
            flashLight.enabled = false;
        }

        GameObject Part(Material m, Vector3 pos, Vector3 size, Vector3 euler)
        {
            return Art.Box(model, pos, size, m, euler, Layers.Weapon);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            GameManager gm = GameManager.I;
            TouchControls tc = TouchControls.I;
            bool playing = gm != null && gm.State == GameState.Playing && owner.Alive;

            bloom = Mathf.MoveTowards(bloom, 0f, 4.5f * dt);
            Spread = 0.35f + bloom + owner.MoveAmount * 1.4f + (owner.Sprinting ? 1.6f : 0f);

            OnTarget = false;
            if (playing)
            {
                RaycastHit h;
                Transform ct = cam.transform;
                if (Physics.Raycast(ct.position, ct.forward, out h, 60f, Layers.ShootMask, QueryTriggerInteraction.Ignore))
                {
                    var hb = h.collider.GetComponent<ZombieHitbox>();
                    OnTarget = hb != null && hb.Owner != null && hb.Owner.Alive;
                }
            }

            if (Reloading)
            {
                reloadT += dt;
                if (reloadT >= ReloadTime) FinishReload();
            }
            else if (playing && tc != null)
            {
                if (tc.ReloadPressed)
                {
                    StartReload();
                }
                else if (autoReloadAt > 0f && Time.time >= autoReloadAt)
                {
                    autoReloadAt = -1f;
                    StartReload();
                }
                else if (tc.FireHeld && Time.time >= nextFire)
                {
                    if (Mag > 0)
                    {
                        Fire();
                    }
                    else if (Reserve > 0)
                    {
                        StartReload();
                    }
                    else if (Time.time >= emptyClickAt)
                    {
                        emptyClickAt = Time.time + 0.4f;
                        if (Sfx.I != null) Sfx.I.Play2D("dry_fire", 0.8f);
                    }
                }
            }

            Animate(dt, playing && tc != null ? tc.LookDelta : Vector2.zero);
        }

        void Fire()
        {
            nextFire = Time.time + 1f / FireRate;
            Mag--;
            ShotsFired++;
            shotIndex++;

            Transform ct = cam.transform;
            Vector3 origin = ct.position;
            Vector3 dir = ct.forward;
            Vector2 r = Random.insideUnitCircle * Mathf.Tan(Spread * Mathf.Deg2Rad);
            dir = (dir + ct.right * r.x + ct.up * r.y).normalized;

            Physics.SyncTransforms();
            RaycastHit hit;
            Vector3 end;
            if (Physics.Raycast(origin, dir, out hit, Range, Layers.ShootMask, QueryTriggerInteraction.Ignore))
            {
                end = hit.point;
                var hb = hit.collider.GetComponent<ZombieHitbox>();
                if (hb != null && hb.Owner != null && hb.Owner.Alive)
                {
                    float dmg = BodyDamage * (hb.IsHead ? HeadMultiplier : 1f);
                    bool killed = hb.Owner.TakeDamage(dmg, dir, hb.IsHead);
                    ShotsHit++;
                    if (Fx.I != null) Fx.I.Blood(hit.point, -dir + hit.normal * 0.5f, hb.IsHead ? 16 : 8);
                    if (HUD.I != null) HUD.I.HitMarker(killed, hb.IsHead);
                    if (Sfx.I != null)
                    {
                        Sfx.I.PlayAt("hit_flesh", hit.point, 0.8f, Random.Range(0.9f, 1.1f));
                        if (hb.IsHead) Sfx.I.Play2D("headshot", 0.45f, killed ? 1f : 1.15f);
                    }
                }
                else
                {
                    if (Fx.I != null) Fx.I.Impact(hit.point, hit.normal);
                    if (Sfx.I != null && shotIndex % 2 == 0) Sfx.I.PlayAt("hit_wall", hit.point, 0.5f, Random.Range(0.85f, 1.15f));
                }
            }
            else
            {
                end = origin + dir * Range;
            }

            if (Fx.I != null) Fx.I.Tracer(muzzle.position, end);
            bloom = Mathf.Min(bloom + 0.45f, 3.5f);
            owner.AddRecoil(Random.Range(0.55f, 0.85f), Random.Range(-0.25f, 0.25f));
            kickBack = 0.05f;
            kickUp = 4f;
            flashT = 0.045f;
            flash.gameObject.SetActive(true);
            flash.localRotation = Quaternion.Euler(0f, 0f, Random.Range(0f, 360f));
            float fs = Random.Range(0.22f, 0.32f);
            flash.localScale = new Vector3(fs, fs, fs);
            flashLight.enabled = true;
            if (Sfx.I != null) Sfx.I.Gunshot();
            if (Mag == 0 && Reserve > 0) autoReloadAt = Time.time + 0.25f;
        }

        public void StartReload()
        {
            if (Reloading || Mag >= MagSize || Reserve <= 0) return;
            Reloading = true;
            reloadT = 0f;
            autoReloadAt = -1f;
            if (Sfx.I != null) Sfx.I.Play2D("reload", 0.9f);
        }

        void FinishReload()
        {
            int take = Mathf.Min(MagSize - Mag, Reserve);
            Mag += take;
            Reserve -= take;
            Reloading = false;
        }

        public bool AddReserve(int amount)
        {
            if (Reserve >= MaxReserve) return false;
            Reserve = Mathf.Min(MaxReserve, Reserve + amount);
            return true;
        }

        void Animate(float dt, Vector2 look)
        {
            kickBack = Mathf.Lerp(kickBack, 0f, 18f * dt);
            kickUp = Mathf.Lerp(kickUp, 0f, 14f * dt);
            swayX = Mathf.Lerp(swayX, Mathf.Clamp(-look.x * 0.03f, -4f, 4f), 8f * dt);
            swayY = Mathf.Lerp(swayY, Mathf.Clamp(look.y * 0.03f, -4f, 4f), 8f * dt);

            float move = owner.MoveAmount;
            bobT += dt * (owner.Sprinting ? 11f : 7.5f) * move;
            Vector3 bob = new Vector3(Mathf.Cos(bobT) * 0.012f, Mathf.Abs(Mathf.Sin(bobT)) * 0.014f, 0f) * move;
            sprintBlend = Mathf.MoveTowards(sprintBlend, owner.Sprinting && !Reloading ? 1f : 0f, 4f * dt);

            float rp = Reloading ? reloadT / ReloadTime : 0f;
            float rc = Mathf.Sin(rp * Mathf.PI);
            float lower = owner.Alive ? 0f : 0.35f;
            rig.localPosition = rigBase + bob + new Vector3(0f, -0.08f * rc - 0.03f * sprintBlend - lower, -kickBack);
            rig.localRotation = Quaternion.Euler(-kickUp + 22f * rc + 10f * sprintBlend + swayY, swayX - 22f * sprintBlend, -25f * rc + swayX * 0.5f);

            float m = 0f;
            if (Reloading && rp > 0.2f && rp < 0.65f) m = Mathf.Sin((rp - 0.2f) / 0.45f * Mathf.PI);
            magazine.localPosition = magBase + new Vector3(0f, -0.22f * m, 0.02f * m);

            if (flashT > 0f)
            {
                flashT -= dt;
                if (flashT <= 0f)
                {
                    flash.gameObject.SetActive(false);
                    flashLight.enabled = false;
                }
            }
        }
    }
}
