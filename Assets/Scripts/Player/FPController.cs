using UnityEngine;

namespace NightClass
{
    /// <summary>
    /// First-person movement: smooth acceleration, crouch (crawl spaces), jump, head bob tied to the
    /// stride, surface footsteps, landing dip, and hiding inside lockers / wardrobes.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public class FPController : MonoBehaviour
    {
        public static FPController I { get; private set; }

        public float walkSpeed = 3.3f;
        public float crouchSpeed = 1.5f;
        public float acceleration = 16f;
        public float deceleration = 22f;
        public float airControl = 2.5f;
        public float gravity = 19f;
        public float jumpHeight = 0.85f;
        public float standHeight = 1.75f;
        public float crouchHeight = 0.9f;
        public Transform head;

        CharacterController cc;
        Camera cam;
        float yaw, pitch, height;
        Vector3 velocity;
        bool grounded, crouching, active;
        float stepDistance, lastStepIndex, bobBlend, idleTime, airTime, landDip, landVel, fovCurrent;
        int noStandZones;
        HidingSpot spot;
        float hideYaw0;

        public bool Crouching { get { return crouching; } }
        public bool Hidden { get; private set; }
        public HidingSpot Spot { get { return spot; } }
        public HidingSpot SpotInRange;
        public float Speed { get; private set; }
        public Vector3 HeadPosition { get { return head != null ? head.position : transform.position + Vector3.up * 1.6f; } }
        public Camera Cam { get { return cam; } }
        public float Yaw { get { return yaw; } }

        void Awake()
        {
            I = this;
            cc = GetComponent<CharacterController>();
            height = standHeight;
            ApplyHeight();
        }

        void ApplyHeight()
        {
            cc.height = height;
            cc.center = new Vector3(0f, height * 0.5f, 0f);
        }

        public void Spawn(Vector3 pos, float yawDeg)
        {
            Hidden = false;
            spot = null;
            cc.enabled = false;
            transform.position = pos;
            yaw = yawDeg;
            pitch = 0f;
            velocity = Vector3.zero;
            crouching = false;
            noStandZones = 0;
            height = standHeight;
            ApplyHeight();
            cc.enabled = true;
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            if (head != null)
            {
                head.localPosition = new Vector3(0f, height - 0.12f, 0f);
                head.localRotation = Quaternion.identity;
            }
        }

        public void AttachCamera(Transform camT)
        {
            camT.SetParent(head, false);
            camT.localPosition = Vector3.zero;
            camT.localRotation = Quaternion.identity;
            cam = camT.GetComponent<Camera>();
            if (cam != null) { cam.fieldOfView = GameSettings.FieldOfView; fovCurrent = cam.fieldOfView; }
        }

        public void SetActive(bool on)
        {
            active = on;
            if (!on) velocity = Vector3.zero;
            if (TouchControls.I != null) TouchControls.I.ResetAll();
        }

        float shakeAmount;
        public void Shake(float amount) { shakeAmount = Mathf.Max(shakeAmount, amount); }

        public void EnterNoStand() { noStandZones++; }
        public void ExitNoStand() { noStandZones = Mathf.Max(0, noStandZones - 1); }
        public bool CanStand { get { return noStandZones == 0; } }

        public void ToggleCrouch()
        {
            if (Hidden) return;
            if (crouching)
            {
                if (!CanStand)
                {
                    NCGame.I.Message("Not enough room to stand up here.", 2f);
                    return;
                }
                float r = cc.radius * 0.9f;
                if (Physics.SphereCast(transform.position + Vector3.up * (height - r), r, Vector3.up, out _, standHeight - height + 0.05f, ~((1 << 11) | (1 << 12) | (1 << 13)), QueryTriggerInteraction.Ignore))
                {
                    NCGame.I.Message("Not enough room to stand up here.", 2f);
                    return;
                }
                crouching = false;
            }
            else crouching = true;
            Sfx.Play2D(GameAssets.I.land, 0.25f, crouching ? 1.25f : 1.1f);
        }

        // ------------------------------------------------------------------ hiding
        public void Hide(HidingSpot s)
        {
            if (Hidden || s == null) return;
            spot = s;
            Hidden = true;
            cc.enabled = false;
            transform.position = s.hidePoint.position - Vector3.up * (standHeight - 0.12f);
            yaw = s.hidePoint.eulerAngles.y;
            hideYaw0 = yaw;
            pitch = 0f;
            crouching = false;
            height = standHeight;
            ApplyHeight();
            velocity = Vector3.zero;
            s.OnHide();
            if (NCGame.I.teacher != null) NCGame.I.teacher.OnPlayerHid(s);
        }

        public void Unhide()
        {
            if (!Hidden || spot == null) return;
            HidingSpot s = spot;
            transform.position = s.exitPoint.position;
            yaw = s.exitPoint.eulerAngles.y;
            pitch = 0f;
            cc.enabled = true;
            Hidden = false;
            spot = null;
            s.OnUnhide();
        }

        public void ForceUnhide()
        {
            if (!Hidden) return;
            Unhide();
        }

        // ------------------------------------------------------------------ update
        void Update()
        {
            if (!active || NCGame.I == null || NCGame.I.State != GameState.Playing) return;
            float dt = Time.deltaTime;
            if (dt <= 0f) return;
            TouchControls input = TouchControls.I;

            Vector2 look = input != null ? input.ConsumeLook() : Vector2.zero;
            yaw += look.x;
            pitch = Mathf.Clamp(pitch - look.y, -82f, 82f);

            if (Hidden)
            {
                yaw = hideYaw0 + Mathf.Clamp(Mathf.DeltaAngle(hideYaw0, yaw), -55f, 55f);
                pitch = Mathf.Clamp(pitch, -35f, 35f);
                Speed = 0f;
                transform.rotation = Quaternion.Euler(0f, yaw, 0f);
                head.localPosition = new Vector3(0f, standHeight - 0.12f + Mathf.Sin(Time.time * 1.2f) * 0.004f, 0f);
                head.localRotation = Quaternion.Euler(pitch, 0f, 0f);
                return;
            }

            // auto-crouch inside crawl spaces
            if (!CanStand && !crouching) crouching = true;
            float targetH = crouching ? crouchHeight : standHeight;
            if (!Mathf.Approximately(height, targetH))
            {
                height = Mathf.MoveTowards(height, targetH, 4f * dt);
                ApplyHeight();
            }

            Vector2 mv = input != null ? input.Move : Vector2.zero;
            float maxSpeed = crouching ? crouchSpeed : walkSpeed;
            Vector3 wish = transform.right * mv.x + transform.forward * mv.y;
            float mag = Mathf.Clamp01(wish.magnitude);
            if (mag > 0.001f) wish /= wish.magnitude;
            Vector3 target = wish * maxSpeed * mag;
            Vector3 hv = new Vector3(velocity.x, 0f, velocity.z);
            if (grounded)
            {
                float rate = target.sqrMagnitude > hv.sqrMagnitude ? acceleration : deceleration;
                hv = Vector3.MoveTowards(hv, target, rate * dt);
            }
            else hv = Vector3.MoveTowards(hv, target, airControl * dt);

            if (input != null && input.ConsumeJump() && grounded)
            {
                if (crouching) ToggleCrouch();
                else
                {
                    velocity.y = Mathf.Sqrt(2f * gravity * jumpHeight);
                    grounded = false;
                    Sfx.Play2D(GameAssets.I.jump, 0.3f, Random.Range(0.95f, 1.05f));
                }
            }
            if (grounded && velocity.y < 0f) velocity.y = -2f;
            else velocity.y -= gravity * dt;

            velocity = new Vector3(hv.x, velocity.y, hv.z);
            float fallSpeed = velocity.y;
            CollisionFlags flags = cc.Move(velocity * dt);
            bool wasGrounded = grounded;
            grounded = cc.isGrounded;
            if ((flags & CollisionFlags.Above) != 0 && velocity.y > 0f) velocity.y = 0f;
            if (!grounded) airTime += dt; else airTime = 0f;
            if (!wasGrounded && grounded) Land(fallSpeed);
            Speed = hv.magnitude;

            if (transform.position.y < -12f && NCGame.I.playerSpawn != null)
                Spawn(NCGame.I.playerSpawn.position, yaw);

            UpdateHead(hv, dt);
        }

        void Land(float fallSpeed)
        {
            float impact = Mathf.Clamp01((-fallSpeed - 3f) / 9f);
            if (airTime > 0.12f || impact > 0f)
            {
                landVel = -(0.6f + impact * 1.8f);
                Sfx.Play2D(Sfx.Pick(GameAssets.I.StepsFor(SurfaceBelow())), 0.5f + impact * 0.4f, 0.85f);
                if (impact > 0.2f) Sfx.Play2D(GameAssets.I.land, 0.25f + impact * 0.5f);
            }
        }

        void UpdateHead(Vector3 hv, float dt)
        {
            float speed = hv.magnitude;
            float eye = height - 0.12f;
            float stride = crouching ? 0.55f : 0.8f;
            bool moving = grounded && speed > 0.3f;
            if (moving)
            {
                stepDistance += speed * dt;
                float idx = Mathf.Floor(stepDistance / stride);
                if (idx > lastStepIndex)
                {
                    lastStepIndex = idx;
                    Footstep(speed);
                }
                idleTime = 0f;
            }
            else idleTime += dt;
            bobBlend = Mathf.MoveTowards(bobBlend, moving ? Mathf.Clamp01(speed / walkSpeed) : 0f, dt * 4f);

            float phase = stepDistance / stride * Mathf.PI;
            float amp = GameSettings.HeadBob ? (crouching ? 0.018f : 0.034f) * bobBlend : 0f;
            float bobY = -Mathf.Abs(Mathf.Sin(phase)) * amp + amp * 0.5f;
            float bobX = Mathf.Cos(phase) * amp * 0.6f;
            float roll = GameSettings.HeadBob ? Mathf.Cos(phase) * 0.5f * bobBlend : 0f;
            float breathe = Mathf.Sin(Time.time * 1.4f) * 0.006f * Mathf.Clamp01(idleTime);

            float springTime = Mathf.Min(dt, 0.1f);
            int steps = Mathf.Max(1, Mathf.CeilToInt(springTime / 0.008f));
            float h = springTime / steps;
            for (int i = 0; i < steps; i++)
            {
                landVel += (-landDip * 90f - landVel * 13f) * h;
                landDip += landVel * h;
            }
            landDip = Mathf.Clamp(landDip, -2f, 2f);
            landVel = Mathf.Clamp(landVel, -20f, 20f);

            Vector3 shake = Vector3.zero;
            if (shakeAmount > 0.001f)
            {
                shake = Random.insideUnitSphere * shakeAmount * 0.12f;
                shakeAmount = Mathf.MoveTowards(shakeAmount, 0f, dt * 0.6f);
            }
            head.localPosition = new Vector3(bobX, eye + bobY + breathe + landDip * 0.1f, 0f) + shake;
            head.localRotation = Quaternion.Euler(pitch + shake.y * 30f, 0f, roll + shake.x * 30f);
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);

            if (cam != null && cam.transform.parent == head)
            {
                float targetFov = GameSettings.FieldOfView;
                fovCurrent = Mathf.Lerp(fovCurrent <= 0f ? targetFov : fovCurrent, targetFov, dt * 5f);
                cam.fieldOfView = fovCurrent;
            }
        }

        void Footstep(float speed)
        {
            float vol = Mathf.Lerp(0.25f, 0.55f, Mathf.InverseLerp(1f, walkSpeed, speed));
            if (crouching) vol *= 0.45f;
            Sfx.Play2D(Sfx.Pick(GameAssets.I.StepsFor(SurfaceBelow())), vol, Random.Range(0.9f, 1.1f));
        }

        public Surface SurfaceBelow()
        {
            RaycastHit hit;
            if (Physics.Raycast(transform.position + Vector3.up * 0.4f, Vector3.down, out hit, 1.2f, ~((1 << 11) | (1 << 12)), QueryTriggerInteraction.Ignore))
            {
                var tag = hit.collider.GetComponentInParent<SurfaceTag>();
                if (tag != null) return tag.surface;
            }
            return Surface.Concrete;
        }
    }
}
