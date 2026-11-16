using UnityEngine;

namespace Moulika
{
    /// <summary>
    /// The first-person player, made for a touch screen (port of game/scripts/player.gd).
    /// - Turning and walking are updated every rendered frame, so they stay smooth whatever the frame rate.
    /// - Walking speeds up and stops within a fraction of a second, without sliding.
    /// - The view follows the thumb, smoothed over a few hundredths of a second so touch jitter disappears;
    ///   the turn per finger movement is the same on every screen size.
    /// - The view bobs gently while walking, with a footstep at the bottom of every bob.
    /// - Standing up is refused where there is no room above you.
    /// </summary>
    public class Player : MonoBehaviour
    {
        public Camera cam;
        public Transform hold;
        public Hud hud;
        public GameAudio sound;
        public float yaw;               // degrees, Unity convention (turning right increases it)
        public float pitch;             // degrees, looking up is positive
        public float sensitivity = 1f;
        public bool crouched, hidden, frozen;
        public float eye = 1.6f;

        CharacterController cc;
        Vector3 velocity;
        float bob, bobAmp;
        bool bobLow;
        Vector2 lookLeft;               // drag (pixels, y up) not yet turned into rotation

        const float Walk = 3.3f;
        const float CrouchSpeed = 1.7f;
        const float Accel = 15f;
        const float Decel = 24f;
        const float Look = 0.0042f;     // radians per pixel of drag on a 720-pixel-high screen
        const float StandH = 1.7f;
        const float CrouchH = 1.0f;
        const float Radius = 0.28f;

        public static Player Create(Transform parent)
        {
            var go = new GameObject("Player");
            go.layer = 2;   // Ignore Raycast: Moulika's sight and the item checks look past the player's own body
            go.transform.SetParent(parent, false);
            var p = go.AddComponent<Player>();
            p.cc = go.AddComponent<CharacterController>();
            p.cc.radius = Radius;
            p.cc.height = StandH;
            p.cc.center = new Vector3(0f, StandH / 2f, 0f);
            p.cc.stepOffset = 0.25f;
            p.cc.slopeLimit = 46f;
            p.cc.skinWidth = 0.02f;
            p.cc.minMoveDistance = 0f;
            var camGo = new GameObject("Camera");
            camGo.transform.SetParent(go.transform, false);
            camGo.transform.localPosition = new Vector3(0f, p.eye, 0f);
            p.cam = camGo.AddComponent<Camera>();
            p.cam.fieldOfView = 68f;
            p.cam.nearClipPlane = 0.05f;
            p.cam.farClipPlane = 120f;
            p.cam.clearFlags = CameraClearFlags.SolidColor;
            p.cam.backgroundColor = Game.SkyColor;
            p.cam.allowMSAA = true;
            p.cam.allowHDR = false;
            var holdGo = new GameObject("Hold");
            holdGo.transform.SetParent(camGo.transform, false);
            holdGo.transform.localPosition = new Vector3(0.3f, -0.24f, 0.55f);
            p.hold = holdGo.transform;
            return p;
        }

        public Vector3 Head { get { return cam.transform.position; } }
        public Vector3 Forward { get { return cam.transform.forward; } }

        public void Teleport(Vector3 p)
        {
            cc.enabled = false;
            transform.position = p;
            cc.enabled = true;
            velocity = Vector3.zero;
        }

        public void SetCrouch(bool c)
        {
            if (crouched && !c)
            {
                // room to stand? (the stand-up capsule must not touch walls or furniture)
                Vector3 b = transform.position + Vector3.up * (Radius + 0.05f);
                Vector3 t = transform.position + Vector3.up * (StandH - Radius + 0.05f);
                if (Physics.CheckCapsule(b, t, Radius - 0.03f, Level.WallMask, QueryTriggerInteraction.Ignore))
                {
                    if (hud != null) hud.ShowMessage("No room to stand up", 1.5f);
                    return;
                }
            }
            crouched = c;
            float h = c ? CrouchH : StandH;
            cc.height = h;
            cc.center = new Vector3(0f, h / 2f, 0f);
        }

        /// <summary>Turn to look at a point (level view).</summary>
        public void Face(Vector3 target)
        {
            Vector3 d = target - transform.position;
            yaw = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
            pitch = 0f;
            lookLeft = Vector2.zero;
            Apply();
        }

        public void Apply()
        {
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            cam.transform.localRotation = Quaternion.Euler(-pitch, 0f, 0f);
        }

        void Update()
        {
            float dt = Mathf.Min(Time.deltaTime, 0.1f);   // a long hitch must not throw the player through a wall
            if (dt <= 0f) return;
            Turn(dt);
            eye = Mathf.Lerp(eye, crouched ? 0.85f : 1.6f, 1f - Mathf.Exp(-dt * 10f));
            if (frozen || hidden || hud == null)
            {
                velocity = Vector3.zero;
                bobAmp = 0f;
                cam.transform.localPosition = new Vector3(0f, eye, 0f);
                return;
            }
            WalkStep(dt);
            Bob(dt);
        }

        void Turn(float dt)
        {
            if (hud != null)
            {
                if (!frozen) lookLeft += hud.look;
                hud.look = Vector2.zero;
            }
            if (frozen) lookLeft = Vector2.zero;
            Vector2 take = lookLeft * (1f - Mathf.Exp(-dt * 26f));
            lookLeft -= take;
            float k = Look * sensitivity * 720f / Mathf.Max(Screen.height, 1) * Mathf.Rad2Deg;
            yaw += take.x * k;
            pitch = Mathf.Clamp(pitch + take.y * k, -77.3f, 77.3f);
            Apply();
        }

        void WalkStep(float dt)
        {
            Vector2 m = hud.move;      // screen convention: y down = backwards
            if (m.magnitude > 1f) m = m.normalized;
            Vector3 want = transform.rotation * new Vector3(m.x, 0f, -m.y) * (crouched ? CrouchSpeed : Walk);
            want.y = 0f;
            var cur = new Vector3(velocity.x, 0f, velocity.z);
            bool speedingUp = want.magnitude > cur.magnitude && (cur.magnitude < 0.2f || Vector3.Dot(want.normalized, cur.normalized) > 0.8f);
            cur = Vector3.MoveTowards(cur, want, (speedingUp ? Accel : Decel) * dt);
            velocity.x = cur.x;
            velocity.z = cur.z;
            velocity.y = cc.isGrounded ? -0.5f : Mathf.Max(velocity.y - 20f * dt, -25f);
            cc.Move(velocity * dt);
            Vector3 v = cc.velocity;
            velocity.x = v.x;
            velocity.z = v.z;
        }

        void Bob(float dt)
        {
            float hv = new Vector2(velocity.x, velocity.z).magnitude;
            bobAmp = Mathf.Lerp(bobAmp, Mathf.Clamp01(hv / Walk), 1f - Mathf.Exp(-dt * 8f));
            if (hv > 0.3f) bob += dt * (5f + hv * 2.4f) * (crouched ? 0.8f : 1f);
            float s = Mathf.Sin(bob);
            // a footstep every time the head reaches the bottom of the bob
            if (s < -0.9f && !bobLow && hv > 0.6f)
            {
                bobLow = true;
                if (sound != null) sound.Play("footstep_" + Random.Range(1, 7), crouched ? -16f : -9f, Random.Range(0.92f, 1.08f));
            }
            else if (s > 0f) bobLow = false;
            cam.transform.localPosition = new Vector3(Mathf.Cos(bob * 0.5f) * 0.012f * bobAmp, eye + s * 0.026f * bobAmp, 0f);
        }
    }
}
