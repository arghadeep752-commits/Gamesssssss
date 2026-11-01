using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace RealFPS
{
    /// <summary>
    /// In-game overlay: fixed joystick, buttons, crosshair, lantern counter, messages.
    /// Layout follows the classic mobile horror-game scheme: a fixed joystick bottom-left, the
    /// right half of the screen to look around, a small crosshair, crouch and settings buttons
    /// top-left, a big hand (interact) button on the right and an action button top-right.
    /// </summary>
    public class Hud : MonoBehaviour
    {
        class HudButton
        {
            public HudAction action;
            public RectTransform rect;
            public Image bg, icon;
            public float radiusRef;
            public bool pressed, highlighted, dimmed;
            public Text label;
        }

        public RectTransform Root { get; private set; }
        public float CanvasScale { get { return canvas != null ? canvas.scaleFactor : 1f; } }

        Canvas canvas;
        readonly List<HudButton> buttons = new List<HudButton>();
        RectTransform joyBase, joyKnob, joyHome;
        Image joyBaseImg, joyKnobImg;
        Text objective, toastTitle, toastSub, hint, fpsText, interactLabel;
        CanvasGroup toastGroup, hintGroup;
        Image crosshair;
        HudButton interact, run;
        float toastUntil, hintUntil;
        float fpsAccum;
        int fpsFrames;
        bool sprinting;

        static readonly Color BtnIdle = new Color(1f, 1f, 1f, 0.16f);
        static readonly Color BtnPressed = new Color(1f, 1f, 1f, 0.38f);
        static readonly Color IconColor = new Color(1f, 1f, 1f, 0.92f);

        public void Build(Canvas c, RectTransform safeRoot)
        {
            canvas = c;
            Root = UIKit.Rect(safeRoot, "HUD");
            Root.Stretch();
            GameAssets A = GameAssets.I;

            // fixed joystick, bottom-left: a ring with a big knob that moves inside it
            joyHome = UIKit.Rect(Root, "Joystick").Place(new Vector2(0f, 0f), new Vector2(0.5f, 0.5f), new Vector2(JoyX, JoyY), new Vector2(JoySize, JoySize));
            joyBaseImg = UIKit.Img(joyHome, "Base", A.circle, new Color(0f, 0f, 0f, 0.28f));
            joyBase = joyBaseImg.rectTransform;
            joyBase.Stretch();
            var baseRing = UIKit.Img(joyHome, "Ring", A.ring, new Color(1f, 1f, 1f, 0.5f));
            baseRing.rectTransform.Stretch();
            joyKnobImg = UIKit.Img(joyHome, "Stick", A.circle, new Color(1f, 1f, 1f, 0.42f));
            joyKnob = joyKnobImg.rectTransform;
            joyKnob.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(KnobSize, KnobSize));
            SetJoystick(false, Vector2.zero, Vector2.zero);

            // buttons
            AddButton(HudAction.Crouch, A.iconCrouch, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(69f, -174f), new Vector2(134f, 240f), false);
            AddButton(HudAction.Pause, A.iconGear, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(267f, -58f), new Vector2(100f, 100f), true);
            interact = AddButton(HudAction.Interact, A.iconHand, new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(-104f, 132f), new Vector2(240f, 240f), true);
            interact.label = UIKit.Label(interact.rect, "Label", "PICK UP", 28, UIKit.TextColor, TextAnchor.MiddleCenter, A.uiFontBold);
            interact.label.rectTransform.Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 1f), new Vector2(0f, -10f), new Vector2(260f, 40f));
            AddButton(HudAction.Jump, A.iconJump, new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-63f, -26f), new Vector2(250f, 250f), true);
            SetInteract(false, null);

            // crosshair
            crosshair = UIKit.Img(Root, "Crosshair", A.dot, new Color(1f, 1f, 1f, 0.8f));
            crosshair.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(7f, 7f));

            // lantern objective (top centre)
            var objBg = UIKit.Img(Root, "Objective", A.rounded, new Color(0f, 0f, 0f, 0.35f));
            objBg.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -30f), new Vector2(230f, 66f));
            var objIcon = UIKit.Img(objBg.transform, "Icon", A.iconLantern, UIKit.Accent);
            objIcon.rectTransform.Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(14f, 0f), new Vector2(48f, 48f));
            objective = UIKit.Label(objBg.transform, "Text", "0 / 5", 34, UIKit.TextColor, TextAnchor.MiddleLeft, A.uiFontBold);
            objective.rectTransform.Stretch(76, 10, 0, 0);

            // toast (top centre)
            var toast = UIKit.Rect(Root, "Toast").Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -70f), new Vector2(900f, 140f));
            toastGroup = toast.gameObject.AddComponent<CanvasGroup>();
            toastGroup.alpha = 0f;
            toastTitle = UIKit.Label(toast, "Title", "", 54, UIKit.TextColor, TextAnchor.MiddleCenter, A.titleFont);
            toastTitle.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), Vector2.zero, new Vector2(900f, 70f));
            toastSub = UIKit.Label(toast, "Sub", "", 30, UIKit.Accent, TextAnchor.MiddleCenter, A.uiFont);
            toastSub.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -72f), new Vector2(900f, 44f));

            // hint (bottom centre)
            var h = UIKit.Rect(Root, "Hint").Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 48f), new Vector2(1000f, 60f));
            hintGroup = h.gameObject.AddComponent<CanvasGroup>();
            hintGroup.alpha = 0f;
            var hbg = UIKit.Img(h, "Bg", A.rounded, new Color(0f, 0f, 0f, 0.4f));
            hbg.rectTransform.Stretch();
            hint = UIKit.Label(h, "Text", "", 28, UIKit.TextColor, TextAnchor.MiddleCenter, A.uiFont, false);
            hint.rectTransform.Stretch(20, 20, 0, 0);

            fpsText = UIKit.Label(Root, "FPS", "", 24, new Color(1f, 1f, 1f, 0.8f), TextAnchor.UpperCenter, A.uiFont);
            fpsText.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -104f), new Vector2(600f, 30f));
            UpdateObjective();
        }

        HudButton AddButton(HudAction action, Sprite icon, Vector2 anchor, Vector2 pivot, Vector2 pos, Vector2 size, bool round)
        {
            var b = new HudButton { action = action, radiusRef = Mathf.Min(size.x, size.y) * 0.5f };
            b.bg = UIKit.Img(Root, action + "Button", round ? GameAssets.I.circle : GameAssets.I.rounded, BtnIdle);
            b.rect = b.bg.rectTransform.Place(anchor, pivot, pos, size);
            if (round)
            {
                var ring = UIKit.Img(b.rect, "Ring", GameAssets.I.ring, new Color(1f, 1f, 1f, 0.45f));
                ring.rectTransform.Stretch();
            }
            b.icon = UIKit.Img(b.rect, "Icon", icon, IconColor);
            float iconSize = Mathf.Min(size.x, size.y) * 0.56f;
            b.icon.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(iconSize, iconSize));
            b.icon.preserveAspect = true;
            buttons.Add(b);
            return b;
        }

        // ------------------------------------------------------------------ input queries
        public int HitButton(Vector2 screen)
        {
            for (int i = 0; i < buttons.Count; i++)
            {
                HudButton b = buttons[i];
                if (!b.rect.gameObject.activeInHierarchy) continue;
                // a little extra margin around each button for fat fingers
                Vector2 local;
                if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(b.rect, screen, null, out local)) continue;
                Rect r = b.rect.rect;
                float m = 18f;
                if (local.x >= r.xMin - m && local.x <= r.xMax + m && local.y >= r.yMin - m && local.y <= r.yMax + m) return i;
            }
            return -1;
        }

        public HudAction ButtonAction(int i) { return buttons[i].action; }

        public void SetButtonPressed(int i, bool pressed)
        {
            if (i < 0 || i >= buttons.Count) return;
            buttons[i].pressed = pressed;
            RefreshButton(buttons[i]);
        }

        public void ReleaseAllButtons()
        {
            foreach (HudButton b in buttons)
            {
                b.pressed = false;
                RefreshButton(b);
            }
        }

        void RefreshButton(HudButton b)
        {
            Color c = b.pressed ? BtnPressed : BtnIdle;
            if (b.highlighted) c = new Color(UIKit.Accent.r, UIKit.Accent.g, UIKit.Accent.b, b.pressed ? 0.6f : 0.42f);
            if (b.dimmed && !b.pressed) c.a *= 0.55f;
            b.bg.color = c;
            b.icon.color = new Color(IconColor.r, IconColor.g, IconColor.b, b.dimmed ? 0.4f : IconColor.a);
            b.rect.localScale = Vector3.one * (b.pressed ? 0.93f : 1f);
        }

        public void SetRunLocked(bool on) { }

        public void SetSprinting(bool on)
        {
            if (on == sprinting) return;
            sprinting = on;
            joyKnobImg.color = on ? new Color(UIKit.Accent.r, UIKit.Accent.g, UIKit.Accent.b, 0.8f) : new Color(1f, 1f, 1f, 0.62f);
        }

        // joystick geometry in canvas units (1920x1080 reference)
        const float JoyX = 321f, JoyY = 258f, JoySize = 282f, KnobSize = 190f;

        /// <summary>Centre of the fixed joystick in screen pixels.</summary>
        public Vector2 JoyCenterScreen()
        {
            return RectTransformUtility.WorldToScreenPoint(null, joyHome.position);
        }

        /// <summary>How far the knob can travel, in screen pixels.</summary>
        public float JoyTravelScreen()
        {
            return (JoySize - KnobSize * 0.5f) * 0.5f * CanvasScale;
        }

        public float JoyRadiusScreen()
        {
            return JoySize * 0.5f * CanvasScale;
        }

        /// <summary>Shows the knob pushed from the centre (screen pixels); "active" brightens it.</summary>
        public void SetJoystick(bool active, Vector2 centerScreen, Vector2 knobScreen)
        {
            Vector2 offset = active ? (knobScreen - centerScreen) / CanvasScale : Vector2.zero;
            joyKnob.anchoredPosition = offset;
            if (!sprinting) joyKnobImg.color = new Color(1f, 1f, 1f, active ? 0.62f : 0.42f);
        }

        Vector2 SafeOffset()
        {
            // HUD root sits inside the safe area; convert from screen to root-local units
            Vector3[] corners = new Vector3[4];
            Root.GetWorldCorners(corners);
            return new Vector2(corners[0].x, corners[0].y) / CanvasScale;
        }

        /// <summary>The hand button is always there; it lights up when something can be picked up.</summary>
        public void SetInteract(bool available, string label)
        {
            if (interact.dimmed == !available && (label == null || interact.label.text == label)) return;
            interact.dimmed = !available;
            interact.highlighted = available;
            interact.label.gameObject.SetActive(available);
            if (available && label != null) interact.label.text = label;
            RefreshButton(interact);
        }

        // ------------------------------------------------------------------ messages
        public void UpdateObjective()
        {
            if (Game.I == null) return;
            objective.text = Game.I.LanternsFound + " / " + Game.I.LanternCount;
            objective.color = Game.I.LanternsFound >= Game.I.LanternCount && Game.I.LanternCount > 0 ? UIKit.Accent : UIKit.TextColor;
        }

        public void ShowToast(string title, string sub, float seconds)
        {
            toastTitle.text = title;
            toastSub.text = sub;
            toastUntil = Time.unscaledTime + seconds;
        }

        public void ShowHint(string text, float seconds)
        {
            hint.text = text;
            hintUntil = Time.unscaledTime + seconds;
        }

        public Vector2 ButtonScreenPos(HudAction a)
        {
            foreach (HudButton b in buttons)
                if (b.action == a) return RectTransformUtility.WorldToScreenPoint(null, b.rect.position);
            return Vector2.zero;
        }

        public Vector2 JoyHomeScreenPos()
        {
            return RectTransformUtility.WorldToScreenPoint(null, joyHome.position);
        }

        void Update()
        {
            float now = Time.unscaledTime;
            toastGroup.alpha = Mathf.MoveTowards(toastGroup.alpha, now < toastUntil ? 1f : 0f, Time.unscaledDeltaTime * 3f);
            hintGroup.alpha = Mathf.MoveTowards(hintGroup.alpha, now < hintUntil ? 1f : 0f, Time.unscaledDeltaTime * 2f);

            fpsText.gameObject.SetActive(GameSettings.ShowFps);
            if (GameSettings.ShowFps)
            {
                fpsAccum += Time.unscaledDeltaTime;
                fpsFrames++;
                if (fpsAccum > 0.5f)
                {
                    float scale = QualityManager.I != null ? QualityManager.I.RenderScale : 1f;
                    string level = QualityManager.I != null ? QualityManager.I.Level.ToString() : "";
                    fpsText.text = Mathf.RoundToInt(fpsFrames / fpsAccum) + " FPS  ·  " + Mathf.RoundToInt(scale * 100f) + "% res  ·  " + level;
                    fpsAccum = 0f;
                    fpsFrames = 0;
                }
            }
        }
    }
}
