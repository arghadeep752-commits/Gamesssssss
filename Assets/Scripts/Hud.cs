using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace TradersMadness
{
    /// <summary>
    /// The in-game controls: the pause gear top-left, the combined stand/crouch button under it, the joystick
    /// bottom-left, the hand (interact) on the right, DROP at the bottom while you hold something (with what you hold
    /// written above it), and the name of whatever you are looking at under the centre dot. A circle marks what you can
    /// use: a bright one on the thing you are aiming at, faint ones on items lying nearby. Top right: the state of the
    /// main door (planks, padlocks, code) like a ticker. While hiding, a dark overlay with slats.
    /// All positions are in canvas units: 720 high, origin top-left, y down.
    /// </summary>
    public class Hud : MonoBehaviour
    {
        public struct Mark { public Vector2 p; public bool main; }

        public Action onInteract, onDrop, onCrouch, onPause;
        public Vector2 move;                 // joystick, screen convention (y down)
        public Vector2 look;                 // accumulated look drag in pixels (y up), consumed by the player
        public bool crouched, canInteract, holding, floating = true;
        public string labelText = "";
        public string dayText = "";
        public string heldText = "";
        public string statusText = "";
        public bool hidden;
        public readonly List<Mark> marks = new List<Mark>();
        public float fontScale = 1f;

        const float JoyR = 78f;              // thumb travel for full speed
        const float UiAlpha = 0.78f;         // the whole HUD is a little see-through

        RectTransform root;
        string message = "";
        float messageT, pulse;
        int joyId = -1, lookId = -1;
        Vector2 joyTarget, knob, joyOrigin, joyPos;

        RawImage ringImg, knobImg, gearImg, crouchImg, handImg;
        Texture2D texCrouch, texStand;
        Stroke gearBox, dot;
        Text label, labelShadow, msg, drop, held, status, day;
        RawImage slats;
        readonly List<Stroke[]> ringPool = new List<Stroke[]>();

        public float W { get { return root != null ? root.rect.width : 1280f; } }
        public const float H = 720f;

        public static Hud Create(Transform canvas, Font font)
        {
            RectTransform rt = Ui.Node(canvas, "HUD");
            Ui.Full(rt);
            var hud = rt.gameObject.AddComponent<Hud>();
            hud.root = rt;
            hud.Build(font);
            return hud;
        }

        static Texture2D UiTex(string n)
        {
            return Resources.Load<Texture2D>("UI/" + n);
        }

        RawImage Img(string name, Texture2D t)
        {
            RectTransform rt = Ui.Node(root, name);
            var img = rt.gameObject.AddComponent<RawImage>();
            img.texture = t;
            img.raycastTarget = false;
            return img;
        }

        Text TextNode(string name, Font f, int size)
        {
            Text t = Ui.Label(root, f, size, Color.white, name);
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.rectTransform.anchorMin = new Vector2(0f, 1f);
            t.rectTransform.anchorMax = new Vector2(0f, 1f);
            t.rectTransform.sizeDelta = new Vector2(900f, size * 2f);
            return t;
        }

        void Build(Font font)
        {
            texCrouch = UiTex("crouch");
            texStand = UiTex("stand");
            ringImg = Img("Joystick ring", UiTex("ring"));
            knobImg = Img("Joystick knob", UiTex("knob"));
            RectTransform gb = Ui.Node(root, "Gear box");
            gearBox = gb.gameObject.AddComponent<Stroke>();
            gearBox.box = true;
            gearBox.radius = 10f;
            gearBox.width = 3f;
            gearBox.color = new Color(1f, 1f, 1f, UiAlpha * 0.9f);
            gearBox.raycastTarget = false;
            gearImg = Img("Gear", UiTex("gear"));
            crouchImg = Img("Crouch", texStand);
            handImg = Img("Hand", UiTex("hand"));
            slats = Img("Hiding", MakeSlats());
            slats.rectTransform.SetAsFirstSibling();
            Ui.Full(slats.rectTransform);
            labelShadow = TextNode("Label shadow", font, 38);
            labelShadow.color = new Color(0f, 0f, 0f, 0.45f);
            label = TextNode("Label", font, 38);
            msg = TextNode("Message", font, 32);
            drop = TextNode("Drop", font, 47);
            held = TextNode("Held", Ui.mono != null ? Ui.mono : font, 22);
            status = TextNode("Status", Ui.mono != null ? Ui.mono : font, 21);
            status.alignment = TextAnchor.UpperRight;
            day = TextNode("Day", Ui.title != null ? Ui.title : font, 34);
            RectTransform dr = Ui.Node(root, "Centre dot");
            dot = dr.gameObject.AddComponent<Stroke>();
            dot.radius = 5f;
            dot.width = 1.6f;
            dot.segments = 24;
            dot.color = new Color(1f, 1f, 1f, UiAlpha * 0.7f);
            dot.raycastTarget = false;
            Layout();
        }

        public void ApplyFont(Font f, float scale)
        {
            fontScale = scale;
            foreach (Text t in new[] { label, labelShadow, msg, drop }) t.font = f;
        }

        /// <summary>Dark picture with light slits, seen from inside a wardrobe.</summary>
        static Texture2D MakeSlats()
        {
            const int w = 64, h = 256;
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false);
            var px = new Color32[w * h];
            for (int y = 0; y < h; y++)
            {
                float band = Mathf.Repeat(y / 18f, 1f);
                float open = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01((band - 0.62f) / 0.08f)) * (1f - Mathf.SmoothStep(0f, 1f, Mathf.Clamp01((band - 0.9f) / 0.08f)));
                for (int x = 0; x < w; x++)
                {
                    float edge = Mathf.Abs(x - w / 2f) / (w / 2f);
                    byte a = (byte)(255f * Mathf.Clamp01(0.97f - open * 0.85f + edge * edge * 0.25f));
                    px[y * w + x] = new Color32(4, 4, 6, a);
                }
            }
            t.SetPixels32(px);
            t.Apply();
            t.wrapMode = TextureWrapMode.Clamp;
            return t;
        }

        Vector2 JoyCenter() { return new Vector2(225f, H - 210f); }
        Rect RGear() { return new Rect(34f, 26f, 92f, 92f); }
        Rect RCrouch() { return new Rect(24f, 142f, 112f, 160f); }
        Rect RHand() { return new Rect(W - 290f, H * 0.33f, 188f, 170f); }
        Rect RDrop() { return new Rect(W / 2f - 135f, H - 135f, 270f, 100f); }

        static Rect Grow(Rect r, float g) { return new Rect(r.x - g, r.y - g, r.width + 2 * g, r.height + 2 * g); }

        /// <summary>Draw a texture as large as fits in r, centred, keeping its proportions (hud.gd _tex_in).</summary>
        static void Fit(RawImage img, Rect r, float a)
        {
            Texture t = img.texture;
            Vector2 ts = t != null ? new Vector2(t.width, t.height) : r.size;
            float k = Mathf.Min(r.width / ts.x, r.height / ts.y);
            Ui.Centre(img.rectTransform, r.center, ts * k);
            img.color = new Color(1f, 1f, 1f, a);
        }

        public void ShowMessage(string t, float secs = 2.5f)
        {
            message = t;
            messageT = secs;
        }

        public void ResetTouches()
        {
            joyId = -1;
            lookId = -1;
            move = Vector2.zero;
            joyTarget = Vector2.zero;
            knob = Vector2.zero;
            look = Vector2.zero;
            marks.Clear();
            joyOrigin = JoyCenter();
        }

        void OnEnable()
        {
            joyOrigin = JoyCenter();
        }

        static Vector2 ToCanvas(Vector2 px)
        {
            float k = H / Mathf.Max(Screen.height, 1);
            return new Vector2(px.x * k, (Screen.height - px.y) * k);
        }

        void Update()
        {
            float dt = Time.unscaledDeltaTime;
            if (messageT > 0f)
            {
                messageT -= dt;
                if (messageT <= 0f) message = "";
            }
            pulse += dt;
            for (int i = 0; i < Input.touchCount; i++) Touch(Input.GetTouch(i));
            if (joyId == -1)
            {
                joyTarget = Vector2.zero;
                knob = Vector2.Lerp(knob, Vector2.zero, 1f - Mathf.Exp(-dt * 18f));
                joyOrigin = Vector2.Lerp(joyOrigin, JoyCenter(), 1f - Mathf.Exp(-dt * 18f));
            }
            move = joyTarget;               // the player eases its speed itself
        }

        void Touch(UnityEngine.Touch t)
        {
            Vector2 p = ToCanvas(t.position);
            if (t.phase == TouchPhase.Began)
            {
                if (RGear().Contains(p)) { if (onPause != null) onPause(); }
                else if (Grow(RCrouch(), 10f).Contains(p)) { if (onCrouch != null) onCrouch(); }
                else if (canInteract && Grow(RHand(), 14f).Contains(p)) { if (onInteract != null) onInteract(); }
                else if (holding && Grow(RDrop(), 12f).Contains(p)) { if (onDrop != null) onDrop(); }
                else if (p.x < W * 0.4f && p.y > H * 0.3f && joyId == -1)
                {
                    // the stick starts where the thumb lands, so touching off-centre never jerks you forward
                    joyId = t.fingerId;
                    joyOrigin = floating && Vector2.Distance(p, JoyCenter()) >= 34f ? p : JoyCenter();
                    joyPos = p;
                    UpdateJoy();
                }
                else if (lookId == -1) lookId = t.fingerId;
            }
            else if (t.phase == TouchPhase.Moved || t.phase == TouchPhase.Stationary)
            {
                if (t.fingerId == joyId)
                {
                    joyPos = p;
                    UpdateJoy();
                }
                else if (t.fingerId == lookId && t.phase == TouchPhase.Moved)
                    look += t.deltaPosition;
            }
            else
            {
                if (t.fingerId == joyId)
                {
                    joyId = -1;
                    joyTarget = Vector2.zero;
                }
                if (t.fingerId == lookId) lookId = -1;
            }
        }

        /// <summary>Joystick input from code (the build check drives it the way a thumb would).</summary>
        public void TestJoy(bool down, Vector2 p)
        {
            if (down)
            {
                if (joyId == -1)
                {
                    joyId = 99;
                    joyOrigin = floating && Vector2.Distance(p, JoyCenter()) >= 34f ? p : JoyCenter();
                }
                joyPos = p;
                UpdateJoy();
            }
            else
            {
                joyId = -1;
                joyTarget = Vector2.zero;
            }
        }

        public Vector2 TestJoyCenter() { return JoyCenter(); }
        public Vector2 TestCrouchCentre() { return RCrouch().center; }

        void UpdateJoy()
        {
            float r = JoyR;
            Vector2 off = joyPos - joyOrigin;
            if (off.magnitude > r)
            {
                // past the rim a floating stick follows the thumb, so turning back responds at once
                if (floating) joyOrigin = joyPos - off.normalized * r;
                off = off.normalized * r;
            }
            Vector2 d = off / r;
            knob = d;
            float m = d.magnitude;
            if (m < 0.08f) joyTarget = Vector2.zero;
            else
            {
                float t = Mathf.Clamp01((m - 0.08f) / 0.92f);
                joyTarget = d / m * (t * t * (3f - 2f * t) * 0.35f + t * 0.65f);   // gentle near the centre, full at the rim
            }
        }

        void LateUpdate()
        {
            Layout();
        }

        Stroke[] Ring(int i)
        {
            while (ringPool.Count <= i)
            {
                var s = new Stroke[3];
                for (int k = 0; k < 3; k++)
                {
                    RectTransform rt = Ui.Node(root, "Mark " + ringPool.Count + "." + k);
                    rt.SetSiblingIndex(0);
                    s[k] = rt.gameObject.AddComponent<Stroke>();
                    s[k].raycastTarget = false;
                }
                ringPool.Add(s);
            }
            return ringPool[i];
        }

        void Layout()
        {
            if (root == null) return;
            // circles on the things you can use (a dark edge keeps them visible on white walls)
            var labAt = new Vector2(W / 2f, H * 0.585f);
            int used = 0;
            foreach (Mark m in marks)
            {
                Stroke[] s = Ring(used++);
                float rr = m.main ? 30f + 2.5f * Mathf.Sin(pulse * 5f) : 13f;
                float wd = m.main ? 3f : 2f;
                for (int k = 0; k < 3; k++)
                {
                    s[k].gameObject.SetActive(k < 2 || m.main);
                    Ui.Centre(s[k].rectTransform, m.p, new Vector2(10f, 10f));
                }
                s[0].Set(rr, wd + 2.5f);
                s[0].color = new Color(0f, 0f, 0f, 0.35f);
                s[1].Set(rr, wd);
                s[1].color = new Color(1f, 1f, 1f, UiAlpha * (m.main ? 0.95f : 0.6f));
                if (m.main)
                {
                    s[2].Set(rr + 7f, 1.5f);
                    s[2].color = new Color(1f, 1f, 1f, UiAlpha * 0.25f);
                    labAt = new Vector2(Mathf.Clamp(m.p.x, 160f, W - 160f), Mathf.Clamp(m.p.y + rr + 52f, H * 0.4f, H * 0.82f));
                }
            }
            for (int i = used; i < ringPool.Count; i++)
                foreach (Stroke s in ringPool[i]) s.gameObject.SetActive(false);

            // joystick: the ring under your thumb (it glides back home when you let go), the knob following it
            Ui.Centre(ringImg.rectTransform, joyOrigin, new Vector2(262f, 262f));
            ringImg.color = new Color(1f, 1f, 1f, UiAlpha * 0.75f);
            Ui.Centre(knobImg.rectTransform, joyOrigin + knob * JoyR, new Vector2(162f, 162f));
            knobImg.color = new Color(1f, 1f, 1f, UiAlpha);

            Rect rg = RGear();
            Ui.Centre(gearBox.rectTransform, rg.center, rg.size);
            Fit(gearImg, Grow(rg, -14f), UiAlpha);
            crouchImg.texture = crouched ? texCrouch : texStand;
            Fit(crouchImg, RCrouch(), UiAlpha);
            handImg.gameObject.SetActive(canInteract);
            if (canInteract) Fit(handImg, RHand(), UiAlpha);

            // DROP at the bottom, with a bigger first letter
            drop.gameObject.SetActive(holding);
            if (holding)
            {
                int big = Mathf.RoundToInt(64 * fontScale), small = Mathf.RoundToInt(47 * fontScale);
                drop.text = "<size=" + big + ">D</size><size=" + small + ">ROP</size>";
                drop.fontSize = small;
                Rect r = RDrop();
                Ui.Centre(drop.rectTransform, new Vector2(r.center.x, r.y + r.height * 0.72f - big * 0.33f), new Vector2(600f, big * 1.6f));
                drop.color = new Color(1f, 1f, 1f, UiAlpha);
            }

            // the name of what you are looking at, with a soft shadow
            bool hasLabel = !string.IsNullOrEmpty(labelText);
            label.gameObject.SetActive(hasLabel);
            labelShadow.gameObject.SetActive(hasLabel);
            if (hasLabel)
            {
                int fs = Mathf.RoundToInt(40 * fontScale);
                label.fontSize = fs;
                labelShadow.fontSize = fs;
                label.text = labelText;
                labelShadow.text = labelText;
                var c = new Vector2(labAt.x, labAt.y - fs * 0.33f);
                Ui.Centre(label.rectTransform, c, new Vector2(900f, fs * 1.8f));
                Ui.Centre(labelShadow.rectTransform, c + new Vector2(2f, 2f), new Vector2(900f, fs * 1.8f));
                label.color = new Color(1f, 1f, 1f, UiAlpha);
            }

            bool hasMsg = !string.IsNullOrEmpty(message);
            msg.gameObject.SetActive(hasMsg);
            if (hasMsg)
            {
                int fs2 = Mathf.RoundToInt(34 * fontScale);
                msg.fontSize = fs2;
                msg.text = message;
                Ui.Centre(msg.rectTransform, new Vector2(W / 2f, H * 0.72f - fs2 * 0.33f), new Vector2(Mathf.Max(W - 80f, 400f), fs2 * 1.8f));
                msg.color = new Color(1f, 1f, 1f, UiAlpha * Mathf.Clamp01(messageT));
            }

            Ui.Centre(dot.rectTransform, new Vector2(W / 2f, H / 2f), new Vector2(10f, 10f));
            dot.gameObject.SetActive(!hidden);

            // what you are holding, above DROP
            bool hasHeld = holding && !string.IsNullOrEmpty(heldText);
            held.gameObject.SetActive(hasHeld);
            if (hasHeld)
            {
                held.text = heldText.ToUpperInvariant();
                Rect r = RDrop();
                Ui.Centre(held.rectTransform, new Vector2(r.center.x, r.y - 6f), new Vector2(600f, 30f));
                held.color = new Color(Ui.Green.r, Ui.Green.g, Ui.Green.b, UiAlpha * 0.9f);
            }
            // the main door's state, top right, and the day, top middle
            status.gameObject.SetActive(!string.IsNullOrEmpty(statusText));
            if (status.gameObject.activeSelf)
            {
                status.text = statusText;
                status.rectTransform.anchorMin = new Vector2(0f, 1f);
                status.rectTransform.anchorMax = new Vector2(0f, 1f);
                status.rectTransform.pivot = new Vector2(1f, 1f);
                status.rectTransform.anchoredPosition = new Vector2(W - 24f, -22f);
                status.rectTransform.sizeDelta = new Vector2(520f, 120f);
                status.color = new Color(1f, 1f, 1f, UiAlpha * 0.85f);
            }
            day.gameObject.SetActive(!string.IsNullOrEmpty(dayText) && !hidden);
            if (day.gameObject.activeSelf)
            {
                day.text = dayText;
                Ui.Centre(day.rectTransform, new Vector2(W / 2f, 34f), new Vector2(400f, 50f));
                day.color = new Color(1f, 1f, 1f, 0.32f);
            }
            slats.gameObject.SetActive(hidden);
            if (hidden) Ui.Full(slats.rectTransform);
        }
    }
}
