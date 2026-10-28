using UnityEngine;

namespace ZombieStrike
{
    /// <summary>
    /// Multi-touch input: floating joystick on the left, drag-to-look on the right,
    /// hold-to-fire button (dragging it also aims) and a reload button.
    /// Screen positions of the buttons are supplied by the HUD.
    /// </summary>
    public class TouchControls : MonoBehaviour
    {
        public static TouchControls I { get; private set; }

        public bool Active;
        public Vector2 Move { get; private set; }
        public Vector2 LookDelta { get; private set; }
        public bool FireHeld { get; private set; }
        public bool ReloadPressed { get; private set; }
        public bool MoveActive { get { return moveFinger >= 0; } }
        public Vector2 MoveOrigin { get; private set; }

        // layout in screen pixels (set by the HUD)
        public Vector2 FireCenter;
        public float FireRadius = 100f;
        public Vector2 ReloadCenter;
        public float ReloadRadius = 60f;
        public Vector2 JoyDefault;
        public float JoyRadius = 110f;

        int moveFinger = -1, lookFinger = -1, fireFinger = -1;
        Vector2 moveCurrent, lookLast, fireLast;

        void Awake()
        {
            I = this;
            Input.multiTouchEnabled = true;
        }

        void Update()
        {
            LookDelta = Vector2.zero;
            ReloadPressed = false;
            if (!Active)
            {
                moveFinger = lookFinger = fireFinger = -1;
                Move = Vector2.zero;
                FireHeld = false;
                return;
            }

            int count = Input.touchCount;
            for (int i = 0; i < count; i++)
            {
                Touch t = Input.GetTouch(i);
                switch (t.phase)
                {
                    case TouchPhase.Began:
                        Begin(t.fingerId, t.position);
                        break;
                    case TouchPhase.Moved:
                    case TouchPhase.Stationary:
                        Drag(t.fingerId, t.position);
                        break;
                    case TouchPhase.Ended:
                    case TouchPhase.Canceled:
                        Drag(t.fingerId, t.position);
                        End(t.fingerId);
                        break;
                }
            }
            if (count == 0) moveFinger = lookFinger = fireFinger = -1;

            if (moveFinger >= 0)
            {
                float r = Mathf.Max(JoyRadius, 1f);
                Vector2 d = (moveCurrent - MoveOrigin) / r;
                if (d.magnitude > 1f)
                {
                    // the stick base follows the thumb so it never runs out of travel
                    MoveOrigin = moveCurrent - d.normalized * r;
                    d = d.normalized;
                }
                Move = d.magnitude < 0.1f ? Vector2.zero : d;
            }
            else
            {
                Move = Vector2.zero;
            }
            FireHeld = fireFinger >= 0;

#if UNITY_EDITOR || UNITY_STANDALONE
            KeyboardMouseFallback();
#endif
        }

        void Begin(int id, Vector2 p)
        {
            if (HUD.I != null && HUD.I.IsOverButton(p)) return;
            if ((p - ReloadCenter).sqrMagnitude <= ReloadRadius * ReloadRadius * 1.3f)
            {
                ReloadPressed = true;
                return;
            }
            if (fireFinger < 0 && (p - FireCenter).sqrMagnitude <= FireRadius * FireRadius * 1.3f)
            {
                fireFinger = id;
                fireLast = p;
                return;
            }
            if (moveFinger < 0 && p.x < Screen.width * 0.42f)
            {
                moveFinger = id;
                float m = JoyRadius * 1.1f;
                MoveOrigin = new Vector2(Mathf.Clamp(p.x, m, Screen.width * 0.42f), Mathf.Clamp(p.y, m, Screen.height - m));
                moveCurrent = p;
                return;
            }
            if (lookFinger < 0)
            {
                lookFinger = id;
                lookLast = p;
            }
        }

        void Drag(int id, Vector2 p)
        {
            if (id == moveFinger)
            {
                moveCurrent = p;
            }
            else if (id == lookFinger)
            {
                LookDelta += p - lookLast;
                lookLast = p;
            }
            else if (id == fireFinger)
            {
                LookDelta += p - fireLast;
                fireLast = p;
            }
        }

        void End(int id)
        {
            if (id == moveFinger) moveFinger = -1;
            if (id == lookFinger) lookFinger = -1;
            if (id == fireFinger) fireFinger = -1;
        }

#if UNITY_EDITOR || UNITY_STANDALONE
        Vector3 lastMouse;

        void KeyboardMouseFallback()
        {
            if (Input.touchCount > 0) return;
            Vector2 k = new Vector2(
                (Input.GetKey(KeyCode.D) ? 1f : 0f) - (Input.GetKey(KeyCode.A) ? 1f : 0f),
                (Input.GetKey(KeyCode.W) ? 1f : 0f) - (Input.GetKey(KeyCode.S) ? 1f : 0f));
            if (k.sqrMagnitude > 0f) Move = Vector2.ClampMagnitude(k * (Input.GetKey(KeyCode.LeftShift) ? 1f : 0.8f), 1f);
            if (Input.GetMouseButton(1)) LookDelta += (Vector2)(Input.mousePosition - lastMouse);
            lastMouse = Input.mousePosition;
            if (Input.GetMouseButton(0)) FireHeld = true;
            if (Input.GetKeyDown(KeyCode.R)) ReloadPressed = true;
        }
#endif
    }
}
