using UnityEngine;

namespace RealFPS
{
    /// <summary>
    /// First-person movement on a CharacterController: walk / sprint / crouch / jump,
    /// smooth acceleration, slope sliding, head bob, footsteps by surface, landing
    /// dip, sprint FOV kick, and soft limits at deep water and the valley edge.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public class FPController : MonoBehaviour
    {
        [Header("Scene (set by the build script)")]
        public Transform head;
        public Terrain terrain;
        public float waterLevel = 21f;
        public Vector3 worldCenter = Vector3.zero;
        public float worldRadius = 175f;

        [Header("Movement")]
        public float walkSpeed = 3.1f;
        public float runSpeed = 6.2f;
        public float crouchSpeed = 1.6f;
        public float acceleration = 20f;
        public float deceleration = 26f;
        public float airControl = 3f;
        public float gravity = 19f;
        public float jumpHeight = 1.05f;
        public float standHeight = 1.8f;
        public float crouchHeight = 1.05f;
        public float slopeSlide = 5f;

        CharacterController cc;
        Camera cam;
        Vector3 velocity;
        float yaw, pitch;
        bool grounded, crouching, active;
        float height;
        float stepDistance, lastStepIndex;
        float bobBlend, landDip, landVel;
        float idleTime;
        Vector3 groundNormal = Vector3.up;
        float groundNormalTime;
        float fovCurrent;
        float airTime;
        bool running;

        public bool IsActive { get { return active; } }
        public bool Running { get { return running; } }

        void Awake()
        {
            cc = GetComponent<CharacterController>();
            height = standHeight;
        }

        public void ApplySettings()
        {
            if (cam != null) fovCurrent = cam.fieldOfView = GameSettings.FieldOfView;
        }

        public void Spawn(Vector3 pos, float yawDeg)
        {
            cc.enabled = false;
            if (terrain != null)
            {
                float ground = terrain.SampleHeight(pos) + terrain.transform.position.y;
                pos.y = Mathf.Max(pos.y, ground + 0.05f);
            }
            transform.position = pos;
            yaw = yawDeg;
            pitch = 0f;
            velocity = Vector3.zero;
            crouching = false;
            height = standHeight;
            ApplyHeight();
            cc.enabled = true;
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            head.localRotation = Quaternion.identity;
        }

        public void AttachCamera(Transform camT)
        {
            camT.SetParent(head, false);
            camT.localPosition = Vector3.zero;
            camT.localRotation = Quaternion.identity;
            cam = camT.GetComponent<Camera>();
            if (cam != null) cam.nearClipPlane = 0.15f;
            ApplySettings();
        }

        public void SetActive(bool on)
        {
            active = on;
            cc.enabled = on;
            if (!on) velocity = Vector3.zero;
        }

        public float Yaw { get { return yaw; } set { yaw = value; } }
        public float Pitch { get { return pitch; } set { pitch = Mathf.Clamp(value, -84f, 84f); } }

        void ApplyHeight()
        {
            cc.height = height;
            cc.center = new Vector3(0f, height * 0.5f, 0f);
        }

        float TerrainHeight(Vector3 p)
        {
            if (terrain == null) return -1000f;
            return terrain.SampleHeight(p) + terrain.transform.position.y;
        }

        float WaterDepth(Vector3 p)
        {
            return waterLevel - TerrainHeight(p);
        }

        void Update()
        {
            if (!active || Game.I == null || Game.I.State != GameState.Playing) return;
            float dt = Time.deltaTime;
            if (dt <= 0f) return;
            TouchControls input = TouchControls.I;

            // ---------------------------------------------------------- look
            Vector2 look = input != null ? input.ConsumeLook() : Vector2.zero;
            yaw += look.x;
            pitch = Mathf.Clamp(pitch - look.y * (GameSettings.InvertY ? -1f : 1f), -84f, 84f);

            // ---------------------------------------------------------- crouch
            if (input != null && input.ConsumeCrouch())
            {
                if (crouching)
                {
                    if (!Physics.SphereCast(transform.position + Vector3.up * (height - cc.radius), cc.radius * 0.9f, Vector3.up, out _, standHeight - height + 0.05f, ~0, QueryTriggerInteraction.Ignore))
                        crouching = false;
                }
                else if (grounded) crouching = true;
            }
            float targetH = crouching ? crouchHeight : standHeight;
            if (!Mathf.Approximately(height, targetH))
            {
                height = Mathf.MoveTowards(height, targetH, 5f * dt);
                ApplyHeight();
            }

            // ---------------------------------------------------------- move
            Vector2 mv = input != null ? input.Move : Vector2.zero;
            running = input != null && input.Sprint && mv.y > 0.35f && !crouching;
            float depthHere = WaterDepth(transform.position);
            float maxSpeed = crouching ? crouchSpeed : (running ? runSpeed : walkSpeed);
            if (depthHere > 0.25f) maxSpeed *= Mathf.Lerp(0.85f, 0.55f, Mathf.InverseLerp(0.25f, 0.9f, depthHere));

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
            else
            {
                hv = Vector3.MoveTowards(hv, target, airControl * dt);
            }

            // soft limits: deep water and the edge of the valley
            hv = LimitTowardsDeepWater(hv, dt);
            Vector3 fromCenter = transform.position - worldCenter;
            fromCenter.y = 0f;
            if (fromCenter.magnitude > worldRadius)
            {
                Vector3 outDir = fromCenter.normalized;
                float outward = Vector3.Dot(hv, outDir);
                if (outward > 0f) hv -= outDir * outward;
                hv -= outDir * Mathf.Min(3f, fromCenter.magnitude - worldRadius);
            }

            // ---------------------------------------------------------- jump & gravity
            if (input != null && input.ConsumeJump() && grounded)
            {
                if (crouching)
                {
                    crouching = false;
                }
                else
                {
                    velocity.y = Mathf.Sqrt(2f * gravity * jumpHeight);
                    grounded = false;
                    Sfx.Play2D(GameAssets.I.jump, 0.35f, Random.Range(0.95f, 1.05f));
                }
            }
            if (grounded && velocity.y < 0f) velocity.y = -2f;
            else velocity.y -= gravity * dt;

            // slide down slopes that are too steep to stand on
            if (grounded && Time.time - groundNormalTime < 0.2f)
            {
                float angle = Vector3.Angle(groundNormal, Vector3.up);
                if (angle > cc.slopeLimit + 2f)
                {
                    Vector3 slide = new Vector3(groundNormal.x, 0f, groundNormal.z).normalized;
                    hv += slide * slopeSlide * Mathf.InverseLerp(cc.slopeLimit, 70f, angle) * 2f;
                }
            }

            velocity = new Vector3(hv.x, velocity.y, hv.z);
            float fallSpeed = velocity.y;
            CollisionFlags flags = cc.Move(velocity * dt);
            bool wasGrounded = grounded;
            grounded = cc.isGrounded;
            if ((flags & CollisionFlags.Above) != 0 && velocity.y > 0f) velocity.y = 0f;
            if (!grounded) airTime += dt; else airTime = 0f;
            if (!wasGrounded && grounded) Land(fallSpeed);

            // fell through the world somehow -> back to the spawn point
            if (transform.position.y < TerrainHeight(transform.position) - 3f && Game.I.spawnPoint != null)
                Spawn(Game.I.spawnPoint.position, yaw);

            UpdateHead(hv, dt);
        }

        Vector3 LimitTowardsDeepWater(Vector3 hv, float dt)
        {
            if (terrain == null || hv.sqrMagnitude < 0.0001f) return hv;
            Vector3 p = transform.position;
            Vector3 ahead = p + hv.normalized * 0.6f;
            float dAhead = WaterDepth(ahead);
            if (dAhead < 1.0f) return hv;
            float e = 0.6f;
            Vector3 grad = new Vector3(WaterDepth(p + Vector3.right * e) - WaterDepth(p - Vector3.right * e), 0f,
                                       WaterDepth(p + Vector3.forward * e) - WaterDepth(p - Vector3.forward * e));
            if (grad.sqrMagnitude < 1e-6f) return Vector3.zero;
            Vector3 deeper = grad.normalized;
            float into = Vector3.Dot(hv, deeper);
            if (into > 0f) hv -= deeper * into;
            if (WaterDepth(p) > 1.15f) hv -= deeper * 1.5f; // gently push back to the shallows
            return hv;
        }

        void Land(float fallSpeed)
        {
            float impact = Mathf.Clamp01((-fallSpeed - 3f) / 9f);
            if (airTime > 0.12f || impact > 0f)
            {
                landVel = -(0.6f + impact * 1.8f);
                Surface s = SurfaceBelow();
                Sfx.Play2D(Sfx.Pick(GameAssets.I.StepsFor(s)), 0.5f + impact * 0.4f, 0.85f);
                if (impact > 0.2f) Sfx.Play2D(GameAssets.I.land, 0.25f + impact * 0.5f);
            }
        }

        void UpdateHead(Vector3 hv, float dt)
        {
            float speed = hv.magnitude;
            float eye = height - 0.12f;

            // footsteps every stride; stride grows with speed
            float stride = Mathf.Lerp(0.78f, 1.45f, Mathf.InverseLerp(walkSpeed, runSpeed, speed));
            if (crouching) stride = 0.6f;
            bool moving = grounded && speed > 0.35f;
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
            else
            {
                idleTime += dt;
            }
            bobBlend = Mathf.MoveTowards(bobBlend, moving ? 1f : 0f, dt * 4f);

            float phase = stepDistance / stride * Mathf.PI;
            float run01 = Mathf.InverseLerp(walkSpeed, runSpeed, speed);
            float amp = GameSettings.HeadBob ? Mathf.Lerp(0.03f, 0.055f, run01) * bobBlend : 0f;
            float bobY = -Mathf.Abs(Mathf.Sin(phase)) * amp + amp * 0.5f;
            float bobX = Mathf.Cos(phase) * amp * 0.6f;
            float roll = GameSettings.HeadBob ? Mathf.Cos(phase) * 0.6f * bobBlend * (0.5f + run01) : 0f;

            // breathing when standing still
            float breathe = Mathf.Sin(Time.time * 1.4f) * 0.006f * Mathf.Clamp01(idleTime);

            // landing dip spring
            landVel += (-landDip * 90f - landVel * 13f) * dt;
            landDip += landVel * dt;

            head.localPosition = new Vector3(bobX, eye + bobY + breathe + landDip * 0.1f, 0f);
            head.localRotation = Quaternion.Euler(pitch, 0f, roll);
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);

            if (cam != null)
            {
                float targetFov = GameSettings.FieldOfView + (running && speed > walkSpeed + 0.5f ? 6f : 0f);
                fovCurrent = Mathf.Lerp(fovCurrent <= 0f ? targetFov : fovCurrent, targetFov, dt * 5f);
                cam.fieldOfView = fovCurrent;
            }
        }

        void Footstep(float speed)
        {
            Surface s = SurfaceBelow();
            float vol = Mathf.Lerp(0.28f, 0.6f, Mathf.InverseLerp(1f, runSpeed, speed));
            if (crouching) vol *= 0.5f;
            Sfx.Play2D(Sfx.Pick(GameAssets.I.StepsFor(s)), vol, Random.Range(0.9f, 1.1f));
        }

        public Surface SurfaceBelow()
        {
            Vector3 p = transform.position;
            if (WaterDepth(p) > 0.05f) return Surface.Water;
            RaycastHit hit;
            if (Physics.Raycast(p + Vector3.up * 0.4f, Vector3.down, out hit, 1.2f, ~0, QueryTriggerInteraction.Ignore))
            {
                var tag = hit.collider.GetComponentInParent<SurfaceTag>();
                if (tag != null) return tag.surface;
                if (hit.collider is TerrainCollider) return TerrainSurface(hit.point);
                return Surface.Rock;
            }
            return TerrainSurface(p);
        }

        Surface TerrainSurface(Vector3 p)
        {
            if (terrain == null) return Surface.Grass;
            TerrainData td = terrain.terrainData;
            Vector3 local = p - terrain.transform.position;
            int x = Mathf.Clamp((int)(local.x / td.size.x * td.alphamapWidth), 0, td.alphamapWidth - 1);
            int z = Mathf.Clamp((int)(local.z / td.size.z * td.alphamapHeight), 0, td.alphamapHeight - 1);
            float[,,] a = td.GetAlphamaps(x, z, 1, 1);
            int best = 0;
            float bw = -1f;
            for (int i = 0; i < a.GetLength(2); i++)
            {
                if (a[0, 0, i] > bw) { bw = a[0, 0, i]; best = i; }
            }
            switch (best)
            {
                case 1: return Surface.Dirt;
                case 2: return Surface.Rock;
                case 3: return Surface.Dirt;
                default: return Surface.Grass;
            }
        }

        void OnControllerColliderHit(ControllerColliderHit hit)
        {
            if (hit.point.y < transform.position.y + cc.radius)
            {
                groundNormal = hit.normal;
                groundNormalTime = Time.time;
            }
        }
    }
}
