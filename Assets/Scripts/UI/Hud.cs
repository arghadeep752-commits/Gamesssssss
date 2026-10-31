using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace RealFPS
{
    /// <summary>In-game overlay: joystick, buttons, crosshair, lantern counter, messages.</summary>
    public class Hud : MonoBehaviour
    {
        class HudButton
        {
            public HudAction action;
            public RectTransform rect;
            public Image bg, icon;
            public float radiusRef;
            public bool pressed, highlighted;
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

            // joystick (floating). A faint "home" ring shows where to put the thumb.
            joyHome = UIKit.Img(Root, "JoyHome", A.ring, new Color(1f, 1f, 1f, 0.18f)).rectTransform
                .Place(new Vector2(0f, 0f), new Vector2(0.5f, 0.5f), new Vector2(260f, 230f), new Vector2(250f, 250f));
            joyBaseImg = UIKit.Img(Root, "JoyBase", A.ring, new Color(1f, 1f, 1f, 0.55f));
            joyBase = joyBaseImg.rectTransform;
            joyBase.Place(Vector2.zero, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(250f, 250f));
            var baseFill = UIKit.Img(joyBase, "Fill", A.circle, new Color(0f, 0f, 0f, 0.18f));
            baseFill.rectTransform.Stretch(8, 8, 8, 8);
            joyKnobImg = UIKit.Img(Root, "JoyKnob", A.circle, new Color(1f, 1f, 1f, 0.7f));
            joyKnob = joyKnobImg.rectTransform;
            joyKnob.Place(Vector2.zero, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(110f, 110f));
            SetJoystick(false, Vector2.zero, Vector2.zero);

            // buttons (bottom-right cluster + pause)
            AddButton(HudAction.Jump, A.iconJump, new Vector2(1f, 0f), new Vector2(-170f, 175f), 92f);
            AddButton(HudAction.Crouch, A.iconCrouch, new Vector2(1f, 0f), new Vector2(-370f, 110f), 66f);
            run = AddButton(HudAction.Run, A.iconRun, new Vector2(1f, 0f), new Vector2(-165f, 395f), 64f);
            AddButton(HudAction.Pause, A.iconPause, new Vector2(1f, 1f), new Vector2(-80f, -78f), 46f);
            interact = AddButton(HudAction.Interact, A.iconHand, new Vector2(1f, 0f), new Vector2(-405f, 320f), 70f);
            interact.label = UIKit.Label(interact.rect, "Label", "PICK UP", 26, UIKit.TextColor, TextAnchor.MiddleCenter, A.uiFontBold);
            interact.label.rectTransform.Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 1f), new Vector2(0f, -8f), new Vector2(200f, 40f));
            SetInteract(false, null);

            // crosshair
            crosshair = UIKit.Img(Root, "Crosshair", A.dot, new Color(1f, 1f, 1f, 0.75f));
            crosshair.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(10f, 10f));

            // lantern objective (top-left)
            var objBg = UIKit.Img(Root, "Objective", A.rounded, new Color(0f, 0f, 0f, 0.35f));
            objBg.rectTransform.Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(40f, -36f), new Vector2(260f, 70f));
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

            fpsText = UIKit.Label(Root, "FPS", "", 24, new Color(1f, 1f, 1f, 0.8f), TextAnchor.UpperLeft, A.uiFont);
            fpsText.rectTransform.Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(44f, -116f), new Vector2(300f, 30f));
            UpdateObjective();
        }

        HudButton AddButton(HudAction action, Sprite icon, Vector2 anchor, Vector2 pos, float radius)
        {
            var b = new HudButton { action = action, radiusRef = radius };
            b.bg = UIKit.Img(Root, action + "Button", GameAssets.I.circle, BtnIdle);
            b.rect = b.bg.rectTransform.Place(anchor, new Vector2(0.5f, 0.5f), pos, new Vector2(radius * 2f, radius * 2f));
            var ring = UIKit.Img(b.rect, "Ring", GameAssets.I.ring, new Color(1f, 1f, 1f, 0.45f));
            ring.rectTransform.Stretch();
            b.icon = UIKit.Img(b.rect, "Icon", icon, IconColor);
            b.icon.rectTransform.Stretch(radius * 0.42f, radius * 0.42f, radius * 0.42f, radius * 0.42f);
            buttons.Add(b);
            return b;
        }

        // ------------------------------------------------------------------ input queries
        public int HitButton(Vector2 screen)
        {
            int best = -1;
            float bestD = float.MaxValue;
            for (int i = 0; i < buttons.Count; i++)
            {
                HudButton b = buttons[i];
                if (!b.rect.gameObject.activeInHierarchy) continue;
                Vector2 c = RectTransformUtility.WorldToScreenPoint(null, b.rect.position);
                float r = b.radiusRef * CanvasScale * 1.3f;
                float d = Vector2.Distance(screen, c);
                if (d < r && d < bestD) { best = i; bestD = d; }
            }
            return best;
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
            b.bg.color = c;
            b.rect.localScale = Vector3.one * (b.pressed ? 0.93f : 1f);
        }

        public void SetRunLocked(bool on)
        {
            run.highlighted = on;
            RefreshButton(run);
        }

        public void SetSprinting(bool on)
        {
            if (on == sprinting) return;
            sprinting = on;
            joyKnobImg.color = on ? new Color(UIKit.Accent.r, UIKit.Accent.g, UIKit.Accent.b, 0.85f) : new Color(1f, 1f, 1f, 0.7f);
        }

        public void SetJoystick(bool visible, Vector2 centerScreen, Vector2 knobScreen)
        {
            joyBase.gameObject.SetActive(visible);
            joyKnob.gameObject.SetActive(visible);
            joyHome.gameObject.SetActive(!visible);
            if (!visible) return;
            float s = CanvasScale;
            joyBase.anchoredPosition = centerScreen / s - SafeOffset();
            joyKnob.anchoredPosition = knobScreen / s - SafeOffset();
        }

        Vector2 SafeOffset()
        {
            // HUD root sits inside the safe area; convert from screen to root-local units
            Vector3[] corners = new Vector3[4];
            Root.GetWorldCorners(corners);
            return new Vector2(corners[0].x, corners[0].y) / CanvasScale;
        }

        public void SetInteract(bool visible, string label)
        {
            interact.rect.gameObject.SetActive(visible);
            if (visible && label != null) interact.label.text = label;
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
                    fpsText.text = Mathf.RoundToInt(fpsFrames / fpsAccum) + " FPS  ·  " + Mathf.RoundToInt(scale * 100f) + "% res";
                    fpsAccum = 0f;
                    fpsFrames = 0;
                }
            }
        }
    }
}
