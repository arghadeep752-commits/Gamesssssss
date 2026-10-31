using UnityEngine;

namespace RealFPS
{
    public enum HudAction { Jump, Crouch, Run, Pause, Interact }

    /// <summary>
    /// Multi-touch controls: a floating joystick on the left part of the screen,
    /// drag-to-look anywhere else, and on-screen buttons (drawn by <see cref="Hud"/>).
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

        const float JoyZone = 0.42f;      // left part of the screen
        const float JoyRadiusRef = 125f;  // in canvas units

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

            float scale = hud.CanvasScale;
            float joyRadius = JoyRadiusRef * scale;
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
                        if (t.position.x < Screen.width * JoyZone && joyFinger < 0)
                        {
                            joyFinger = id;
                            joyCenter = t.position;
                            move = Vector2.zero;
                            joyActive = true;
                            hud.SetJoystick(true, joyCenter, joyCenter);
                        }
                        else if (lookFinger < 0)
                        {
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
                            Vector2 d = t.position - joyCenter;
                            float len = d.magnitude;
                            if (len > joyRadius * 1.35f)
                            {
                                // let the base follow the thumb
                                joyCenter = t.position - d / len * joyRadius * 1.35f;
                                d = t.position - joyCenter;
                                len = d.magnitude;
                            }
                            Vector2 v = d / joyRadius;
                            if (v.magnitude > 1f) v = v.normalized;
                            // small dead zone, then a slightly eased response
                            float m = v.magnitude;
                            float dm = Mathf.InverseLerp(0.08f, 1f, m);
                            move = m > 1e-4f ? v / m * Mathf.Pow(dm, 1.15f) : Vector2.zero;
                            joyActive = true;
                            Vector2 knob = joyCenter + Vector2.ClampMagnitude(d, joyRadius);
                            hud.SetJoystick(true, joyCenter, knob);
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
