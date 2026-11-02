using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace NightClass
{
    /// <summary>
    /// In-game HUD, Granny style: joystick bottom-left; hand (use), drop, torch, hide, crouch and jump
    /// buttons on the right; lesson counter and the item in hand at the top-left.
    /// Touches are routed here by <see cref="TouchControls"/> (no uGUI raycasts during play).
    /// </summary>
    public class Hud : MonoBehaviour
    {
        class HButton
        {
            public RectTransform rt;
            public Image bg, icon;
            public HudAction action;
            public bool visible = true, pressed, highlight;
            public float baseSize;
        }

        readonly List<HButton> buttons = new List<HButton>();
        Canvas canvas;
        RectTransform root, joyBase, joyKnob;
        Text prompt, lesson;
        Image itemSlot, itemIcon, crosshair;
        HButton bInteract, bDrop, bFire, bHide, bCrouch, bJump, bPause;
        const float JoySize = 260f;
        bool interactAvailable;
        string interactLabel = "";

        public void Build(Canvas c, RectTransform safeRoot)
        {
            canvas = c;
            root = UIKit.Rect(safeRoot, "HUD").Stretch();
            GameAssets a = GameAssets.I;

            crosshair = UIKit.Img(root, "Crosshair", a.dot, new Color(1f, 1f, 1f, 0.55f));
            crosshair.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(10f, 10f));

            // joystick
            joyBase = UIKit.Img(root, "JoyBase", a.ring, new Color(1f, 1f, 1f, 0.32f)).rectTransform
                .Place(new Vector2(0f, 0f), new Vector2(0.5f, 0.5f), new Vector2(230f, 210f), new Vector2(JoySize, JoySize));
            joyKnob = UIKit.Img(joyBase, "Knob", a.circle, new Color(1f, 1f, 1f, 0.42f)).rectTransform
                .Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(110f, 110f));

            // right-hand buttons
            bInteract = Add("Interact", HudAction.Interact, a.iconHand, new Vector2(-250f, 330f), 175f);
            bDrop = Add("Drop", HudAction.Drop, a.iconDrop, new Vector2(-450f, 300f), 120f);
            bFire = Add("Fire", HudAction.Fire, a.iconFire, new Vector2(-445f, 470f), 120f);
            bHide = Add("Hide", HudAction.Hide, a.iconHide, new Vector2(-250f, 540f), 140f);
            bCrouch = Add("Crouch", HudAction.Crouch, a.iconCrouch, new Vector2(-360f, 120f), 130f);
            bJump = Add("Jump", HudAction.Jump, a.iconJump, new Vector2(-150f, 140f), 150f);
            bPause = Add("Pause", HudAction.Pause, a.iconPause, Vector2.zero, 92f);
            bPause.rt.Place(new Vector2(1f, 1f), new Vector2(0.5f, 0.5f), new Vector2(-80f, -76f), new Vector2(92f, 92f));

            prompt = UIKit.Label(root, "Prompt", "", 30, UIKit.TextColor, TextAnchor.MiddleCenter, a.uiFontBold);
            prompt.rectTransform.Place(new Vector2(1f, 0f), new Vector2(0.5f, 0.5f), new Vector2(-250f, 450f), new Vector2(460f, 60f));

            // top-left: lesson counter and the item in hand
            lesson = UIKit.Label(root, "Lesson", "", 40, UIKit.Chalk, TextAnchor.MiddleLeft, a.chalkFont);
            lesson.rectTransform.Place(new Vector2(0f, 1f), new Vector2(0f, 0.5f), new Vector2(40f, -60f), new Vector2(420f, 60f));
            itemSlot = UIKit.Img(root, "ItemSlot", a.rounded, new Color(0f, 0f, 0f, 0.45f));
            itemSlot.rectTransform.Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(40f, -105f), new Vector2(120f, 120f));
            itemIcon = UIKit.Img(itemSlot.rectTransform, "Icon", null, Color.white);
            itemIcon.rectTransform.Stretch(12, 12, 12, 12);
            itemIcon.preserveAspect = true;
        }

        HButton Add(string name, HudAction action, Sprite icon, Vector2 posFromBottomRight, float size)
        {
            var b = new HButton { action = action, baseSize = size };
            b.bg = UIKit.Img(root, name, GameAssets.I.circle, new Color(0.05f, 0.05f, 0.06f, 0.55f));
            b.rt = b.bg.rectTransform.Place(new Vector2(1f, 0f), new Vector2(0.5f, 0.5f), posFromBottomRight, new Vector2(size, size));
            var ring = UIKit.Img(b.rt, "Ring", GameAssets.I.ring, new Color(1f, 1f, 1f, 0.45f));
            ring.rectTransform.Stretch();
            b.icon = UIKit.Img(b.rt, "Icon", icon, new Color(1f, 1f, 1f, 0.92f));
            b.icon.rectTransform.Stretch(size * 0.2f, size * 0.2f, size * 0.2f, size * 0.2f);
            b.icon.preserveAspect = true;
            buttons.Add(b);
            return b;
        }

        public int HitButton(Vector2 screen)
        {
            for (int i = 0; i < buttons.Count; i++)
            {
                HButton b = buttons[i];
                if (!b.visible || !b.rt.gameObject.activeInHierarchy) continue;
                Vector2 c = RectTransformUtility.WorldToScreenPoint(null, b.rt.position);
                float r = b.baseSize * 0.5f * Scale() * 1.12f;
                if ((screen - c).sqrMagnitude <= r * r) return i;
            }
            return -1;
        }

        float Scale() { return canvas != null ? canvas.scaleFactor : 1f; }
        public HudAction ButtonAction(int i) { return buttons[i].action; }

        public void SetButtonPressed(int i, bool pressed)
        {
            if (i < 0 || i >= buttons.Count) return;
            buttons[i].pressed = pressed;
        }

        public void ReleaseAllButtons()
        {
            foreach (HButton b in buttons) b.pressed = false;
        }

        public Vector2 JoyCenterScreen() { return RectTransformUtility.WorldToScreenPoint(null, joyBase.position); }
        public float JoyRadiusScreen() { return JoySize * 0.5f * Scale(); }
        public float JoyTravelScreen() { return JoySize * 0.38f * Scale(); }

        public void SetJoystick(bool active, Vector2 centerScreen, Vector2 knobScreen)
        {
            if (joyKnob == null) return;
            Vector2 off = active ? (knobScreen - centerScreen) / Scale() : Vector2.zero;
            joyKnob.anchoredPosition = off;
            joyKnob.GetComponent<Image>().color = new Color(1f, 1f, 1f, active ? 0.62f : 0.42f);
        }

        public void SetInteract(bool available, string label)
        {
            interactAvailable = available;
            interactLabel = label;
        }

        void Update()
        {
            if (root == null) return;
            FPController p = FPController.I;
            Inventory inv = Inventory.I;
            NCGame g = NCGame.I;
            bool hidden = p != null && p.Hidden;

            bInteract.visible = interactAvailable && !hidden;
            bDrop.visible = inv != null && inv.Held != ItemType.None && !hidden;
            bFire.visible = inv != null && inv.Held == ItemType.Torch && !hidden;
            bHide.visible = p != null && (hidden || p.SpotInRange != null);
            bCrouch.visible = !hidden;
            bJump.visible = !hidden && p != null && !p.Crouching;
            bHide.icon.sprite = hidden ? GameAssets.I.iconUnhide : GameAssets.I.iconHide;
            bCrouch.icon.sprite = p != null && p.Crouching ? GameAssets.I.iconStand : GameAssets.I.iconCrouch;
            prompt.text = bInteract.visible ? interactLabel : "";

            foreach (HButton b in buttons)
            {
                b.rt.gameObject.SetActive(b.visible);
                if (!b.visible) continue;
                float target = b.pressed ? 0.9f : 1f;
                float k = Mathf.MoveTowards(b.rt.localScale.x, target, Time.unscaledDeltaTime * 4f);
                b.rt.localScale = new Vector3(k, k, 1f);
                Color bgc = b.pressed ? new Color(0.6f, 0.1f, 0.08f, 0.7f) : new Color(0.05f, 0.05f, 0.06f, 0.55f);
                if (b == bInteract) bgc = b.pressed ? new Color(0.7f, 0.12f, 0.1f, 0.8f) : new Color(0.55f, 0.1f, 0.08f, 0.62f + 0.12f * Mathf.Sin(Time.unscaledTime * 5f));
                if (b == bFire && inv != null && !inv.CanFire) bgc.a *= 0.4f;
                b.bg.color = bgc;
                if (b == bFire && inv != null) b.icon.color = new Color(1f, 1f, 1f, inv.CanFire ? 0.95f : 0.35f);
            }
            crosshair.color = new Color(1f, 1f, 1f, interactAvailable ? 0.9f : 0.45f);
            crosshair.rectTransform.sizeDelta = interactAvailable ? new Vector2(16f, 16f) : new Vector2(9f, 9f);

            if (g != null) lesson.text = "LESSON " + Mathf.Min(g.Day, NCGame.MaxDays) + " / " + NCGame.MaxDays;
            Sprite ic = inv != null ? GameAssets.I.IconFor(inv.Held) : null;
            itemSlot.gameObject.SetActive(ic != null);
            itemIcon.sprite = ic;
        }
    }
}
