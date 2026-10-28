using UnityEngine;

namespace ZombieStrike
{
    /// <summary>First-person player: movement, looking, flashlight, health and death.</summary>
    public class PlayerController : MonoBehaviour
    {
        public static PlayerController I { get; private set; }

        public const float EyeHeight = 1.62f;
        public const float MaxHealth = 100f;
        const float WalkSpeed = 4.4f;
        const float SprintSpeed = 6.6f;

        public float Health { get; private set; }
        public bool Alive { get; private set; }
        public bool Sprinting { get; private set; }
        public float MoveAmount { get; private set; }
        public Camera Cam { get; private set; }
        public Weapon Gun { get; private set; }

        CharacterController cc;
        Transform head;
        float yaw, pitch, kick, vy, stepDistance, shake, deathTime, hurtSoundAt;
        int stepIndex;

        public static PlayerController Create(Vector3 position, float startYaw)
        {
            var go = new GameObject("Player");
            go.layer = Layers.Player;
            go.transform.position = position;
            var cc = go.AddComponent<CharacterController>();
            cc.height = 1.8f;
            cc.radius = 0.35f;
            cc.center = new Vector3(0f, 0.9f, 0f);
            cc.stepOffset = 0.35f;
            cc.slopeLimit = 45f;
            cc.skinWidth = 0.04f;
            var p = go.AddComponent<PlayerController>();
            p.Setup(cc, startYaw);
            return p;
        }

        void Awake()
        {
            I = this;
            Health = MaxHealth;
            Alive = true;
        }

        void Setup(CharacterController controller, float startYaw)
        {
            cc = controller;
            yaw = startYaw;
            pitch = 0f;

            head = new GameObject("Head").transform;
            head.SetParent(transform, false);
            head.localPosition = new Vector3(0f, EyeHeight, 0f);

            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            camGo.transform.SetParent(head, false);
            Cam = camGo.AddComponent<Camera>();
            Cam.fieldOfView = 70f;
            Cam.nearClipPlane = 0.08f;
            Cam.farClipPlane = 80f;
            Cam.clearFlags = CameraClearFlags.SolidColor;
            Cam.backgroundColor = RenderSettings.fogColor;
            Cam.cullingMask = ~(1 << Layers.Weapon);
            Cam.depth = 0f;
            camGo.AddComponent<AudioListener>();

            var weaponCamGo = new GameObject("Weapon Camera");
            weaponCamGo.transform.SetParent(camGo.transform, false);
            var weaponCam = weaponCamGo.AddComponent<Camera>();
            weaponCam.clearFlags = CameraClearFlags.Depth;
            weaponCam.cullingMask = 1 << Layers.Weapon;
            weaponCam.fieldOfView = 64f;
            weaponCam.nearClipPlane = 0.01f;
            weaponCam.farClipPlane = 5f;
            weaponCam.depth = 1f;

            var flGo = new GameObject("Flashlight");
            flGo.transform.SetParent(camGo.transform, false);
            flGo.transform.localPosition = new Vector3(0.18f, -0.12f, 0.05f);
            flGo.transform.localRotation = Quaternion.Euler(1.5f, -1.5f, 0f);
            var fl = flGo.AddComponent<Light>();
            fl.type = LightType.Spot;
            fl.range = 30f;
            fl.spotAngle = 62f;
            fl.intensity = 2.6f;
            fl.color = new Color(1f, 0.95f, 0.85f);
            fl.shadows = LightShadows.None;
            fl.renderMode = LightRenderMode.ForcePixel;

            Gun = camGo.AddComponent<Weapon>();
            Gun.Build(this, Cam);
            Apply();
        }

        void Apply()
        {
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            float t = Time.time;
            float sx = shake > 0f ? (Mathf.PerlinNoise(t * 25f, 1f) - 0.5f) * shake * 6f : 0f;
            float sy = shake > 0f ? (Mathf.PerlinNoise(1f, t * 25f) - 0.5f) * shake * 6f : 0f;
            float roll = Alive ? 0f : Mathf.Lerp(0f, 72f, Ease.OutCubic(deathTime / 1.2f));
            head.localRotation = Quaternion.Euler(pitch - kick + sy, sx, roll);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            GameManager gm = GameManager.I;
            TouchControls tc = TouchControls.I;
            bool playing = gm != null && gm.State == GameState.Playing && Alive;

            if (!Alive)
            {
                deathTime += Time.unscaledDeltaTime;
                float a = Ease.OutCubic(deathTime / 1.2f);
                head.localPosition = Vector3.Lerp(new Vector3(0f, EyeHeight, 0f), new Vector3(0f, 0.35f, 0f), a);
                Apply();
                return;
            }

            if (gm != null && gm.State == GameState.Menu)
            {
                yaw += 5f * dt;
                pitch = Mathf.Lerp(pitch, -4f, dt);
            }

            Vector2 move = playing && tc != null ? tc.Move : Vector2.zero;
            Vector2 look = playing && tc != null ? tc.LookDelta : Vector2.zero;

            // look: a full-screen-height swipe turns about 180 degrees at speed 1
            float k = 180f / Mathf.Max(Screen.height, 1) * Settings.LookSpeed;
            if (Gun != null && Gun.OnTarget) k *= 0.62f; // gentle aim assist
            yaw += look.x * k;
            pitch = Mathf.Clamp(pitch - look.y * k, -80f, 80f);
            kick = Mathf.MoveTowards(kick, 0f, (3f + kick * 7f) * dt);
            shake = Mathf.MoveTowards(shake, 0f, 2.5f * dt);
            Apply();

            // movement
            Sprinting = move.magnitude > 0.9f && move.y > 0.55f;
            float speed = Sprinting ? SprintSpeed : WalkSpeed;
            Vector3 wish = (transform.right * move.x + transform.forward * move.y) * speed;
            if (cc.isGrounded && vy < 0f) vy = -2f;
            vy += Physics.gravity.y * dt;
            cc.Move((wish + Vector3.up * vy) * dt);

            Vector3 v = cc.velocity;
            v.y = 0f;
            float horizontal = v.magnitude;
            MoveAmount = Mathf.Clamp01(horizontal / WalkSpeed);

            // head bob and footsteps
            float bob = playing ? Mathf.Sin(stepDistance / 2.2f * Mathf.PI * 2f) : 0f;
            head.localPosition = new Vector3(0f, EyeHeight + bob * 0.035f * MoveAmount, 0f);
            if (playing && cc.isGrounded && horizontal > 0.5f)
            {
                stepDistance += horizontal * dt;
                if (stepDistance >= 2.2f)
                {
                    stepDistance -= 2.2f;
                    stepIndex++;
                    if (Sfx.I != null) Sfx.I.Play2D(stepIndex % 2 == 0 ? "footstep1" : "footstep2", 0.35f, Random.Range(0.9f, 1.1f));
                }
            }

            if (Sfx.I != null) Sfx.I.SetHeartbeat(Health < 35f ? 0.25f + (35f - Health) / 35f * 0.75f : 0f);
        }

        public void AddRecoil(float up, float side)
        {
            pitch = Mathf.Clamp(pitch - up * 0.4f, -80f, 80f);
            kick += up * 0.6f;
            yaw += side;
        }

        public void AddShake(float amount)
        {
            shake = Mathf.Max(shake, amount);
        }

        public void TakeDamage(float amount, Vector3 from)
        {
            if (!Alive || GameManager.I == null || GameManager.I.State != GameState.Playing) return;
            Health = Mathf.Max(0f, Health - amount);
            AddShake(0.35f);
            if (HUD.I != null) HUD.I.OnDamaged(amount / MaxHealth, from);
            if (Time.time >= hurtSoundAt && Sfx.I != null)
            {
                hurtSoundAt = Time.time + 0.35f;
                Sfx.I.Play2D("player_hurt", 0.9f, Random.Range(0.92f, 1.08f));
            }
            if (Health <= 0f) Die();
        }

        public bool Heal(float amount)
        {
            if (!Alive || Health >= MaxHealth) return false;
            Health = Mathf.Min(MaxHealth, Health + amount);
            return true;
        }

        void Die()
        {
            Alive = false;
            deathTime = 0f;
            if (Sfx.I != null) Sfx.I.SetHeartbeat(0f);
            if (GameManager.I != null) GameManager.I.OnPlayerDied();
        }
    }
}
