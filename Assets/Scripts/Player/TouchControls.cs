using UnityEngine;

namespace NightClass
{
    public enum HudAction { Interact, Drop, Crouch, Jump, Hide, Fire, Pause }

    /// <summary>
    /// Multi-touch input: fixed joystick bottom-left, the right half of the screen looks around,
    /// and the Granny-style buttons drawn by <see cref="Hud"/>. Keyboard + mouse work in the editor.
    /// </summary>
    public class TouchControls : MonoBehaviour
    {
        public static TouchControls I { get; private set; }
        public Hud hud;
        public Vector2 Move { get; private set; }
        public Vector2 SimulatedMove;

        Vector2 lookAccum;
        int joyFinger = -1, lookFinger = -1;
        Vector2 joyCenter, lastLook;
        readonly int[] buttonFinger = new int[12];
        bool jumpQueued;

        void Awake()
        {
            I = this;
            for (int i = 0; i < buttonFinger.Length; i++) buttonFinger[i] = -1;
        }

        public Vector2 ConsumeLook() { Vector2 v = lookAccum; lookAccum = Vector2.zero; return v; }
        public bool ConsumeJump() { bool v = jumpQueued; jumpQueued = false; return v; }
        public void AddLook(Vector2 degrees) { lookAccum += degrees; }

        public void ResetAll()
        {
            Move = Vector2.zero;
            lookAccum = Vector2.zero;
            jumpQueued = false;
            joyFinger = lookFinger = -1;
            for (int i = 0; i < buttonFinger.Length; i++) buttonFinger[i] = -1;
            if (hud != null)
            {
                hud.SetJoystick(false, Vector2.zero, Vector2.zero);
                hud.ReleaseAllButtons();
            }
        }

        float DegreesPerPixel()
        {
            return 140f / Mathf.Max(1, Screen.height) * GameSettings.LookSensitivity;
        }

        void Update()
        {
            if (NCGame.I == null || NCGame.I.State != GameState.Playing || hud == null)
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
                        if (b >= 0) { PressButton(b, id); break; }
                        Vector2 jc = hud.JoyCenterScreen();
                        if (joyFinger < 0 && t.position.x < Screen.width * 0.5f && Vector2.Distance(t.position, jc) < hud.JoyRadiusScreen() * 1.6f)
                        {
                            joyFinger = id;
                            joyCenter = jc;
                            joyActive = true;
                            Vector2 knob0;
                            move = StickVector(t.position - joyCenter, hud.JoyTravelScreen(), out knob0);
                            hud.SetJoystick(true, joyCenter, joyCenter + knob0);
                        }
                        else if (lookFinger < 0 && t.position.x > Screen.width * 0.42f)
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
                            Vector2 knob;
                            move = StickVector(t.position - joyCenter, hud.JoyTravelScreen(), out knob);
                            joyActive = true;
                            hud.SetJoystick(true, joyCenter, joyCenter + knob);
                        }
                        else if (id == lookFinger)
                        {
                            Vector2 delta = t.position - lastLook;
                            lastLook = t.position;
                            if (delta.magnitude < Screen.height * 0.35f) lookAccum += delta * DegreesPerPixel();
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
        }

        static Vector2 StickVector(Vector2 d, float travel, out Vector2 knob)
        {
            knob = Vector2.ClampMagnitude(d, travel);
            Vector2 v = d / Mathf.Max(1f, travel);
            float m = Mathf.Min(1f, v.magnitude);
            float dm = Mathf.InverseLerp(0.1f, 1f, m);
            return m > 1e-4f ? v.normalized * Mathf.Pow(dm, 1.1f) : Vector2.zero;
        }

        void PressButton(int index, int finger)
        {
            if (index < buttonFinger.Length) buttonFinger[index] = finger;
            hud.SetButtonPressed(index, true);
            Do(hud.ButtonAction(index));
        }

        public void Do(HudAction a)
        {
            FPController p = FPController.I;
            switch (a)
            {
                case HudAction.Interact:
                    if (Interactor.I != null) Interactor.I.Use();
                    break;
                case HudAction.Drop:
                    if (Inventory.I != null) Inventory.I.Drop();
                    break;
                case HudAction.Crouch:
                    if (p != null) p.ToggleCrouch();
                    break;
                case HudAction.Jump:
                    jumpQueued = true;
                    break;
                case HudAction.Hide:
                    if (p != null)
                    {
                        if (p.Hidden) p.Unhide();
                        else if (p.SpotInRange != null) p.Hide(p.SpotInRange);
                    }
                    break;
                case HudAction.Fire:
                    if (Inventory.I != null) Inventory.I.Fire();
                    break;
                case HudAction.Pause:
                    Sfx.Play2D(GameAssets.I.uiClick, 0.5f);
                    NCGame.I.Pause();
                    break;
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
            if (Input.GetKeyDown(KeyCode.C)) Do(HudAction.Crouch);
            if (Input.GetKeyDown(KeyCode.E)) Do(HudAction.Interact);
            if (Input.GetKeyDown(KeyCode.G)) Do(HudAction.Drop);
            if (Input.GetKeyDown(KeyCode.H)) Do(HudAction.Hide);
            if (Input.GetKeyDown(KeyCode.F)) Do(HudAction.Fire);
            if (Input.GetKeyDown(KeyCode.Escape)) Do(HudAction.Pause);
        }
#endif
    }
}
