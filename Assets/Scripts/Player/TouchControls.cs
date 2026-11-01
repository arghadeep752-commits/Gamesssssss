using UnityEngine;

namespace RealFPS
{
    public enum HudAction { Jump, Crouch, Run, Pause, Interact }

    /// <summary>
    /// Multi-touch controls: a fixed joystick at the bottom-left, the right half of the screen as a
    /// look pad, and on-screen buttons (drawn by <see cref="Hud"/>). Pushing the stick all the way
    /// forward runs.
    /// Keyboard and mouse work too (for testing in the editor).
    /// </summary>
    public class TouchControls : MonoBehaviour
    {
        public static TouchControls I { get; private set; }

        public Hud hud;

        public Vector2 Move { get; private set; }
        /// <summary>Used by the automated test tour to walk without touches.</summary>
        public Vector2 SimulatedMove;
        public bool Sprint { get; private set; }
        public bool RunLocked { get; private set; }

        Vector2 lookAccum;
        bool jumpQueued, crouchQueued, interactQueued;

        int joyFinger = -1, lookFinger = -1;
        Vector2 joyCenter, lastLook;
        float rimTime;
        readonly int[] buttonFinger = new int[8];

        const float LookZone = 0.5f;      // the right half of the screen looks around

        void Awake()
        {
            I = this;
            for (int i = 0; i < buttonFinger.Length; i++) buttonFinger[i] = -1;
        }

        public Vector2 ConsumeLook()
        {
            Vector2 v = lookAccum;
            lookAccum = Vector2.zero;
            return v;
        }

        public bool ConsumeJump() { bool v = jumpQueued; jumpQueued = false; return v; }
        public bool ConsumeCrouch() { bool v = crouchQueued; crouchQueued = false; return v; }
        public bool ConsumeInteract() { bool v = interactQueued; interactQueued = false; return v; }

        public void ResetAll()
        {
            Move = Vector2.zero;
            lookAccum = Vector2.zero;
            jumpQueued = crouchQueued = interactQueued = false;
            joyFinger = lookFinger = -1;
            for (int i = 0; i < buttonFinger.Length; i++) buttonFinger[i] = -1;
            rimTime = 0f;
            Sprint = RunLocked;
            if (hud != null)
            {
                hud.SetJoystick(false, Vector2.zero, Vector2.zero);
                hud.ReleaseAllButtons();
            }
        }

        float DegreesPerPixel()
        {
            return 150f / Mathf.Max(1, Screen.height) * GameSettings.LookSensitivity;
        }

        void Update()
        {
            if (Game.I == null || Game.I.State != GameState.Playing || hud == null)
            {
                if (joyFinger >= 0 || lookFinger >= 0 || Move != Vector2.zero) ResetAll();
                return;
            }

            Vector2 move = Move;
            bool joyActive = false;

            for (int i = 0; i < Input.touchCount; i++)
            {
                Touch t = Input.GetTouch(i);
                int id = t.fingerId;
                switch (t.phase)
                {
                    case TouchPhase.Began:
                    {
                        int b = hud.HitButton(t.position);
                        if (b >= 0)
                        {
                            PressButton(b, id);
                            break;
                        }
                        // fixed joystick: grab it anywhere on (or just around) its ring
                        Vector2 jc = hud.JoyCenterScreen();
                        if (joyFinger < 0 && Vector2.Distance(t.position, jc) < hud.JoyRadiusScreen() * 1.45f)
                        {
                            joyFinger = id;
                            joyCenter = jc;
                            joyActive = true;
                            move = StickVector(t.position - joyCenter, hud.JoyTravelScreen(), out Vector2 knob0);
                            hud.SetJoystick(true, joyCenter, joyCenter + knob0);
                        }
                        else if (lookFinger < 0 && t.position.x > Screen.width * LookZone)
                        {
                            // the right half of the screen is the look pad
                            lookFinger = id;
                            lastLook = t.position;
                        }
                        break;
                    }
                    case TouchPhase.Moved:
                    case TouchPhase.Stationary:
                    {
                        if (id == joyFinger)
                        {
                            move = StickVector(t.position - joyCenter, hud.JoyTravelScreen(), out Vector2 knob);
                            joyActive = true;
                            hud.SetJoystick(true, joyCenter, joyCenter + knob);
                        }
                        else if (id == lookFinger)
                        {
                            Vector2 delta = t.position - lastLook;
                            lastLook = t.position;
                            if (delta.magnitude < Screen.height * 0.35f)
                                lookAccum += delta * DegreesPerPixel();
                        }
                        break;
                    }
                    case TouchPhase.Ended:
                    case TouchPhase.Canceled:
                    {
                        if (id == joyFinger)
                        {
                            joyFinger = -1;
                            move = Vector2.zero;
                            hud.SetJoystick(false, Vector2.zero, Vector2.zero);
                        }
                        if (id == lookFinger) lookFinger = -1;
                        for (int k = 0; k < buttonFinger.Length; k++)
                        {
                            if (buttonFinger[k] == id)
                            {
                                buttonFinger[k] = -1;
                                hud.SetButtonPressed(k, false);
                            }
                        }
                        break;
                    }
                }
            }
            if (joyFinger < 0 && !joyActive) move = Vector2.zero;

#if UNITY_EDITOR || UNITY_STANDALONE
            KeyboardMouse(ref move);
#endif
            if (SimulatedMove != Vector2.zero) move = SimulatedMove;
            Move = move;

            // sprint: lock button, or push the stick all the way forward
            if (move.magnitude > 0.92f && move.y > 0.7f) rimTime += Time.deltaTime;
            else rimTime = 0f;
            Sprint = RunLocked || rimTime > 0.18f;
            hud.SetSprinting(Sprint && move.y > 0.35f);
        }

        /// <summary>Thumb offset -> movement (dead zone, eased response) and the clamped knob offset.</summary>
        static Vector2 StickVector(Vector2 d, float travel, out Vector2 knob)
        {
            knob = Vector2.ClampMagnitude(d, travel);
            Vector2 v = d / Mathf.Max(1f, travel);
            float m = Mathf.Min(1f, v.magnitude);
            float dm = Mathf.InverseLerp(0.1f, 1f, m);
            return m > 1e-4f ? v.normalized * Mathf.Pow(dm, 1.15f) : Vector2.zero;
        }

        void PressButton(int index, int finger)
        {
            if (index < buttonFinger.Length) buttonFinger[index] = finger;
            hud.SetButtonPressed(index, true);
            switch (hud.ButtonAction(index))
            {
                case HudAction.Jump: jumpQueued = true; break;
                case HudAction.Crouch: crouchQueued = true; break;
                case HudAction.Run:
                    RunLocked = !RunLocked;
                    hud.SetRunLocked(RunLocked);
                    break;
                case HudAction.Pause:
                    Sfx.Play2D(GameAssets.I.uiClick, 0.5f);
                    Game.I.Pause();
                    break;
                case HudAction.Interact: interactQueued = true; break;
            }
        }

#if UNITY_EDITOR || UNITY_STANDALONE
        void KeyboardMouse(ref Vector2 move)
        {
            Vector2 k = new Vector2((Input.GetKey(KeyCode.D) ? 1 : 0) - (Input.GetKey(KeyCode.A) ? 1 : 0),
                                    (Input.GetKey(KeyCode.W) ? 1 : 0) - (Input.GetKey(KeyCode.S) ? 1 : 0));
            if (k != Vector2.zero) move = k.normalized;
            if (Input.GetMouseButton(1))
                lookAccum += new Vector2(Input.GetAxis("Mouse X"), Input.GetAxis("Mouse Y")) * 3f * GameSettings.LookSensitivity;
            if (Input.GetKeyDown(KeyCode.Space)) jumpQueued = true;
            if (Input.GetKeyDown(KeyCode.C)) crouchQueued = true;
            if (Input.GetKeyDown(KeyCode.E)) interactQueued = true;
            if (Input.GetKey(KeyCode.LeftShift) && move.y > 0f) move = move.normalized;
        }
#endif
    }
}
