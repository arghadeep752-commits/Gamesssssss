using UnityEngine;

namespace GridProto
{
    /// <summary>
    /// First-person body: smooth walking/running with momentum, jump, crouch, head bob,
    /// footsteps, landing dip and pushing physics cubes.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public class PlayerController : MonoBehaviour
    {
        [Header("References")]
        public Transform cameraPivot;      // eye position; head bob moves this
        public Camera playerCamera;        // child of the pivot; pitch and roll
        public AudioSource footstepSource;

        [Header("Movement")]
        public float walkSpeed = 3.2f;
        public float runSpeed = 5.6f;
        public float crouchSpeed = 1.7f;
        public float groundAcceleration = 11f;
        public float airAcceleration = 2.5f;
        public float gravity = 17f;
        public float jumpHeight = 1.05f;
        public float pushAcceleration = 18f;

        [Header("Body")]
        public float standHeight = 1.8f;
        public float crouchHeight = 1.1f;
        public float eyeBelowTop = 0.13f;

        [Header("Camera")]
        [Tooltip("Degrees turned when dragging across the full screen height")]
        public float lookDegreesPerScreen = 170f;
        public float pitchLimit = 85f;
        public float baseFov = 62f;
        public float runFovBoost = 6f;

        CharacterController controller;
        Vector3 velocity;
        float yaw, pitch;
        bool crouching;
        float height;
        bool wasGrounded = true;
        float lastGroundedTime = -10f, jumpBufferedUntil = -10f;
        float fallSpeed;
        float bobPhase, bobWeight, roll, fov;
        float dip, dipVelocity;
        int stepIndex;

        public bool IsCrouching { get { return crouching; } }
        public bool IsRunning { get; private set; }

        void Awake()
        {
            controller = GetComponent<CharacterController>();
            yaw = transform.eulerAngles.y;
            height = standHeight;
            fov = baseFov;
            ApplyHeight(height);
        }

        public void Teleport(Vector3 position, float newYaw, float newPitch)
        {
            controller.enabled = false;
            transform.position = position;
            controller.enabled = true;
            yaw = newYaw;
            pitch = newPitch;
            velocity = Vector3.zero;
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);
        }

        void Update()
        {
            // always consume the input, so nothing piles up while the game is paused
            Vector2 move = TouchState.Move;
            Vector2 look = TouchState.LookDelta;
            TouchState.LookDelta = Vector2.zero;
            bool jump = TouchState.JumpPressed;
            TouchState.JumpPressed = false;
            bool crouchToggle = TouchState.CrouchPressed;
            TouchState.CrouchPressed = false;
#if UNITY_EDITOR || UNITY_STANDALONE
            ReadKeyboardAndMouse(ref move, ref look, ref jump, ref crouchToggle);
#endif
            float dt = Time.deltaTime;
            if (dt <= 0f) return;

            // look
            float degreesPerPixel = lookDegreesPerScreen * GameSettings.Sensitivity / Mathf.Max(1f, Screen.height);
            yaw += look.x * degreesPerPixel;
            pitch = Mathf.Clamp(pitch - look.y * degreesPerPixel, -pitchLimit, pitchLimit);
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);

            // crouch
            if (crouchToggle)
            {
                if (crouching) { if (CanStand()) crouching = false; }
                else crouching = true;
            }
            float targetHeight = crouching ? crouchHeight : standHeight;
            if (!Mathf.Approximately(height, targetHeight))
            {
                height = Mathf.MoveTowards(height, targetHeight, dt * 4.5f);
                ApplyHeight(height);
            }

            // horizontal movement with momentum
            bool grounded = controller.isGrounded;
            if (grounded) lastGroundedTime = Time.time;
            if (jump) jumpBufferedUntil = Time.time + 0.15f;

            float amount = Mathf.Clamp01(move.magnitude);
            IsRunning = !crouching && amount > 0.92f && move.y > 0.55f;
            float speed = crouching ? crouchSpeed : (IsRunning ? runSpeed : walkSpeed);
            Vector3 wish = transform.right * move.x + transform.forward * move.y;
            if (wish.sqrMagnitude > 1f) wish.Normalize();
            Vector3 targetVelocity = wish * speed;
            Vector3 horizontal = new Vector3(velocity.x, 0f, velocity.z);
            float accel = grounded ? groundAcceleration : airAcceleration;
            horizontal = Vector3.Lerp(horizontal, targetVelocity, 1f - Mathf.Exp(-accel * dt));

            // vertical movement (with a short jump buffer and coyote time)
            bool canJump = Time.time - lastGroundedTime < 0.12f;
            if (Time.time < jumpBufferedUntil && canJump && velocity.y <= 0.1f)
            {
                jumpBufferedUntil = -10f;
                if (crouching)
                {
                    if (CanStand()) crouching = false;
                }
                else
                {
                    velocity.y = Mathf.Sqrt(2f * gravity * jumpHeight);
                    lastGroundedTime = -10f;
                    PlayFoot(ProtoAudio.Thump, 0.3f);
                }
            }
            else if (grounded && velocity.y < 0f)
            {
                velocity.y = -2f;   // keeps the controller glued to the ground and slopes
            }
            else
            {
                velocity.y -= gravity * dt;
            }

            velocity.x = horizontal.x;
            velocity.z = horizontal.z;
            if (!grounded) fallSpeed = Mathf.Max(fallSpeed, -velocity.y);

            CollisionFlags flags = controller.Move(velocity * dt);
            if ((flags & CollisionFlags.Above) != 0 && velocity.y > 0f) velocity.y = 0f;

            bool nowGrounded = controller.isGrounded;
            if (nowGrounded && !wasGrounded)
            {
                if (fallSpeed > 3f)
                {
                    dipVelocity -= Mathf.Min(fallSpeed * 0.08f, 1f);
                    PlayFoot(ProtoAudio.Thump, Mathf.Clamp01(fallSpeed / 9f) * 0.8f);
                }
                fallSpeed = 0f;
            }
            wasGrounded = nowGrounded;

            UpdateCamera(dt, horizontal, nowGrounded, move);
        }

        void UpdateCamera(float dt, Vector3 horizontal, bool grounded, Vector2 move)
        {
            float speed = horizontal.magnitude;
            float targetWeight = grounded ? Mathf.Clamp01(speed / walkSpeed) : 0f;
            bobWeight = Mathf.Lerp(bobWeight, targetWeight, 1f - Mathf.Exp(-9f * dt));

            // one footstep every half bob cycle; stride length sets the rhythm
            float stride = crouching ? 0.75f : (IsRunning ? 1.75f : 1.25f);   // ~2.5 steps/s walking, ~3.2 running
            if (grounded && speed > 0.15f)
            {
                float before = bobPhase;
                bobPhase += speed * dt / stride * Mathf.PI;
                if (Mathf.Floor(bobPhase / Mathf.PI) != Mathf.Floor(before / Mathf.PI))
                {
                    stepIndex++;
                    float volume = crouching ? 0.2f : (IsRunning ? 0.6f : 0.42f);
                    PlayFoot(ProtoAudio.Footstep(stepIndex + Random.Range(0, 3)), volume);
                }
            }
            float ampY = crouching ? 0.018f : (IsRunning ? 0.05f : 0.032f);
            float ampX = crouching ? 0.012f : (IsRunning ? 0.028f : 0.018f);
            float bobY = (Mathf.Abs(Mathf.Sin(bobPhase)) - 0.5f) * ampY * bobWeight;   // lowest when a foot lands
            float bobX = Mathf.Cos(bobPhase) * ampX * bobWeight;                          // sway over the planted foot

            // landing dip: a damped spring (time step clamped so it stays stable on hitches)
            float sdt = Mathf.Min(dt, 0.05f);
            dipVelocity += (-dip * 60f - dipVelocity * 11f) * sdt;
            dip += dipVelocity * sdt;

            roll = Mathf.Lerp(roll, -move.x * 1.6f, 1f - Mathf.Exp(-6f * dt));
            float targetFov = baseFov + (IsRunning && speed > walkSpeed * 1.1f ? runFovBoost : 0f);
            fov = Mathf.Lerp(fov, targetFov, 1f - Mathf.Exp(-5f * dt));

            float eye = height - eyeBelowTop;
            cameraPivot.localPosition = new Vector3(bobX, eye + bobY + dip, 0f);
            playerCamera.transform.localRotation = Quaternion.Euler(pitch, 0f, roll);
            playerCamera.fieldOfView = fov;
        }

        void ApplyHeight(float h)
        {
            controller.height = h;
            controller.center = new Vector3(0f, h * 0.5f, 0f);
        }

        bool CanStand()
        {
            float r = controller.radius * 0.9f;
            Vector3 p = transform.position;
            Vector3 bottom = p + Vector3.up * (r + 0.1f);
            Vector3 top = p + Vector3.up * (standHeight - r);
            int mask = ~(1 << gameObject.layer);
            return !Physics.CheckCapsule(bottom, top, r, mask, QueryTriggerInteraction.Ignore);
        }

        void PlayFoot(AudioClip clip, float volume)
        {
            if (footstepSource == null || clip == null) return;
            footstepSource.pitch = Random.Range(0.92f, 1.08f);
            footstepSource.PlayOneShot(clip, volume);
        }

        // push physics cubes the player walks into
        void OnControllerColliderHit(ControllerColliderHit hit)
        {
            Rigidbody body = hit.collider.attachedRigidbody;
            if (body == null || body.isKinematic) return;
            if (hit.moveDirection.y < -0.3f) return;   // standing on top of it
            Vector3 push = new Vector3(hit.moveDirection.x, 0f, hit.moveDirection.z);
            if (push.sqrMagnitude < 0.0001f) return;
            Vector3 at = new Vector3(hit.point.x, Mathf.Lerp(hit.point.y, body.worldCenterOfMass.y, 0.6f), hit.point.z);
            body.AddForceAtPosition(push.normalized * pushAcceleration, at, ForceMode.Acceleration);
        }

#if UNITY_EDITOR || UNITY_STANDALONE
        Vector3 lastMouse;
        bool mouseLooking;

        // keyboard + mouse for testing in the Unity editor: WASD, Shift run, Space jump, C crouch, E interact, right mouse look
        void ReadKeyboardAndMouse(ref Vector2 move, ref Vector2 look, ref bool jump, ref bool crouch)
        {
            Vector2 k = Vector2.zero;
            if (Input.GetKey(KeyCode.W)) k.y += 1f;
            if (Input.GetKey(KeyCode.S)) k.y -= 1f;
            if (Input.GetKey(KeyCode.D)) k.x += 1f;
            if (Input.GetKey(KeyCode.A)) k.x -= 1f;
            if (k != Vector2.zero)
            {
                k = k.normalized;
                if (!Input.GetKey(KeyCode.LeftShift)) k *= 0.85f;
                move = k;
            }
            if (Input.GetKeyDown(KeyCode.Space)) jump = true;
            if (Input.GetKeyDown(KeyCode.C)) crouch = true;
            if (Input.GetKeyDown(KeyCode.E)) TouchState.InteractPressed = true;
            if (Input.GetMouseButton(1))
            {
                if (mouseLooking) look += (Vector2)(Input.mousePosition - lastMouse);
                mouseLooking = true;
                lastMouse = Input.mousePosition;
            }
            else
            {
                mouseLooking = false;
            }
        }
#endif
    }
}
