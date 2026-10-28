using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace ZombieStrike
{
    /// <summary>
    /// All on-screen UI, built in code: HUD, touch-control visuals, menus and banners.
    /// Buttons are handled directly from touches (no EventSystem needed).
    /// </summary>
    public class HUD : MonoBehaviour
    {
        public static HUD I { get; private set; }

        class UIButton
        {
            public RectTransform Rect;
            public Image Bg;
            public Action OnClick;
            public Color Normal;
            public int Finger = -1;
            public bool MouseDown;
        }

        static readonly Color Red = new Color(0.86f, 0.1f, 0.08f);
        static readonly Color Gold = new Color(1f, 0.8f, 0.25f);
        static readonly Vector2 Center = new Vector2(0.5f, 0.5f);

        RectTransform root, safe;
        GameObject hudGroup, menuPanel, pausePanel, overPanel;
        Image hpFill, damageVignette, lowHpVignette, crossDot, fireBg, reloadRing, joyBaseImg, joyKnobImg, dmgArcImg, sprintIcon;
        Text hpText, scoreText, killsText, waveText, remainText, ammoText, hintText, bannerText, bannerSub, popupText;
        Text menuBest, overStats, overBest, sensText;
        readonly Image[] cross = new Image[4];
        readonly Image[] hitBars = new Image[4];
        RectTransform hitRoot, dmgArc, joyBase, joyKnob, fireBtn, reloadBtn, popupRt, bannerRt;
        Vector2 joyDefaultPos;
        UIButton pauseButton, playButton;
        readonly List<UIButton> buttons = new List<UIButton>();

        float bannerT = -1f, bannerDur = 2f, popupT = -1f, hitT = -1f, dmgFlash, dmgArcT = -1f, hintT = -1f;
        bool hitKill;
        Vector3 dmgFrom;
        int lastHp = -1, lastScore = -1, lastKills = -1, lastWave = -1, lastRemain = -1, lastMag = -1, lastReserve = -1;
        Rect lastSafe;
        int layoutFrames;

        // ------------------------------------------------------------------ construction

        public void Build()
        {
            I = this;
            var cgo = new GameObject("HUD Canvas");
            cgo.layer = 5;
            var canvas = cgo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var scaler = cgo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1600f, 900f);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 1f;
            root = (RectTransform)cgo.transform;

            FullImage(root, "Vignette", Art.UISprite("vignette"), new Color(0f, 0f, 0f, 0.6f));
            damageVignette = FullImage(root, "DamageVignette", Art.UISprite("vignette"), new Color(0.85f, 0f, 0f, 0f));
            lowHpVignette = FullImage(root, "LowHealthVignette", Art.UISprite("vignette"), new Color(0.6f, 0f, 0f, 0f));

            safe = Stretch(root, "Safe");
            ApplySafeArea();
            hudGroup = Stretch(safe, "HUD").gameObject;
            BuildHud(hudGroup.transform as RectTransform);
            BuildMenu();
            BuildPause();
            BuildGameOver();
            SetState(GameState.Menu);
        }

        static RectTransform NewRect(Transform parent, string name, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.layer = 5;
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = anchor;
            rt.anchorMax = anchor;
            rt.pivot = Center;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            return rt;
        }

        static RectTransform Stretch(Transform parent, string name)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.layer = 5;
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.pivot = Center;
            rt.anchoredPosition = Vector2.zero;
            rt.sizeDelta = Vector2.zero;
            return rt;
        }

        static Image Img(Transform parent, string name, Sprite sprite, Color color, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            RectTransform rt = NewRect(parent, name, anchor, pos, size);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sprite;
            img.color = color;
            img.raycastTarget = false;
            return img;
        }

        static Image FullImage(Transform parent, string name, Sprite sprite, Color color)
        {
            RectTransform rt = Stretch(parent, name);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sprite;
            img.color = color;
            img.raycastTarget = false;
            return img;
        }

        static Text Label(Transform parent, string name, string text, int size, TextAnchor align, Color color, Vector2 anchor, Vector2 pos, Vector2 box)
        {
            RectTransform rt = NewRect(parent, name, anchor, pos, box);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = Art.Font;
            t.text = text;
            t.fontSize = size;
            t.fontStyle = FontStyle.Bold;
            t.alignment = align;
            t.color = color;
            t.raycastTarget = false;
            t.supportRichText = true;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            var shadow = rt.gameObject.AddComponent<Shadow>();
            shadow.effectColor = new Color(0f, 0f, 0f, 0.85f);
            shadow.effectDistance = new Vector2(3f, -3f);
            return t;
        }

        UIButton MakeButton(Transform parent, string text, Vector2 pos, Vector2 size, Color color, int fontSize, Action onClick)
        {
            RectTransform rt = NewRect(parent, text + " Button", Center, pos, size);
            var bg = rt.gameObject.AddComponent<Image>();
            bg.sprite = Art.UISprite("rounded", 40f);
            bg.type = Image.Type.Sliced;
            bg.color = color;
            bg.raycastTarget = false;
            Label(rt, "Label", text, fontSize, TextAnchor.MiddleCenter, Color.white, Center, Vector2.zero, size);
            var b = new UIButton { Rect = rt, Bg = bg, OnClick = onClick, Normal = color };
            buttons.Add(b);
            return b;
        }

        void BuildHud(RectTransform g)
        {
            Vector2 tl = new Vector2(0f, 1f), tc = new Vector2(0.5f, 1f), tr = new Vector2(1f, 1f);
            Vector2 bl = Vector2.zero, br = new Vector2(1f, 0f), bc = new Vector2(0.5f, 0f);

            // health
            Img(g, "Heart", Art.UISprite("icon_heart"), new Color(0.95f, 0.2f, 0.2f), tl, new Vector2(62f, -60f), new Vector2(56f, 56f));
            Image hpBack = Img(g, "HealthBack", Art.UISprite("rounded", 40f), new Color(0f, 0f, 0f, 0.55f), tl, new Vector2(300f, -60f), new Vector2(390f, 34f));
            hpBack.type = Image.Type.Sliced;
            hpBack.pixelsPerUnitMultiplier = 3f;
            hpFill = Img(hpBack.transform, "HealthFill", Art.White, new Color(0.3f, 0.85f, 0.35f), Center, Vector2.zero, new Vector2(380f, 24f));
            hpFill.type = Image.Type.Filled;
            hpFill.fillMethod = Image.FillMethod.Horizontal;
            hpFill.fillOrigin = 0;
            hpText = Label(g, "HealthText", "100", 34, TextAnchor.MiddleLeft, Color.white, tl, new Vector2(560f, -60f), new Vector2(120f, 40f));
            scoreText = Label(g, "Score", "SCORE 0", 30, TextAnchor.MiddleLeft, Color.white, tl, new Vector2(170f, -112f), new Vector2(300f, 40f));
            killsText = Label(g, "Kills", "KILLS 0", 24, TextAnchor.MiddleLeft, new Color(1f, 1f, 1f, 0.75f), tl, new Vector2(170f, -150f), new Vector2(300f, 34f));

            // wave
            waveText = Label(g, "Wave", "WAVE 1", 46, TextAnchor.MiddleCenter, Color.white, tc, new Vector2(0f, -48f), new Vector2(500f, 60f));
            remainText = Label(g, "Remaining", "", 26, TextAnchor.MiddleCenter, new Color(1f, 0.85f, 0.8f, 0.9f), tc, new Vector2(0f, -94f), new Vector2(500f, 36f));

            // pause button (top right)
            pauseButton = MakeButton(g, "", Vector2.zero, new Vector2(96f, 96f), new Color(0f, 0f, 0f, 0.45f), 10, () => GameManager.I.Pause());
            pauseButton.Rect.anchorMin = tr;
            pauseButton.Rect.anchorMax = tr;
            pauseButton.Rect.anchoredPosition = new Vector2(-72f, -66f);
            pauseButton.Bg.sprite = Art.UISprite("circle");
            pauseButton.Bg.type = Image.Type.Simple;
            Img(pauseButton.Rect, "PauseIcon", Art.UISprite("icon_pause"), Color.white, Center, Vector2.zero, new Vector2(52f, 52f));

            // crosshair & hit marker
            RectTransform crossRoot = NewRect(g, "Crosshair", Center, Vector2.zero, Vector2.zero);
            for (int i = 0; i < 4; i++)
                cross[i] = Img(crossRoot, "Bar", Art.White, new Color(1f, 1f, 1f, 0.9f), Center, Vector2.zero, i < 2 ? new Vector2(4f, 18f) : new Vector2(18f, 4f));
            crossDot = Img(crossRoot, "Dot", Art.UISprite("circle"), new Color(1f, 1f, 1f, 0.9f), Center, Vector2.zero, new Vector2(7f, 7f));
            hitRoot = NewRect(g, "HitMarker", Center, Vector2.zero, Vector2.zero);
            for (int i = 0; i < 4; i++)
            {
                float sx = (i == 0 || i == 3) ? 1f : -1f;
                float sy = i < 2 ? 1f : -1f;
                Image b = Img(hitRoot, "Hit", Art.White, Color.white, Center, new Vector2(sx * 15f, sy * 15f), new Vector2(5f, 20f));
                b.rectTransform.localRotation = Quaternion.Euler(0f, 0f, sx * sy > 0 ? -45f : 45f);
                hitBars[i] = b;
            }
            hitRoot.gameObject.SetActive(false);

            dmgArcImg = Img(g, "DamageArc", Art.UISprite("damage_arc"), new Color(1f, 0.1f, 0.05f, 0f), Center, Vector2.zero, new Vector2(560f, 560f));
            dmgArc = dmgArcImg.rectTransform;

            // banner, popup, hint
            bannerText = Label(g, "Banner", "", 96, TextAnchor.MiddleCenter, Color.white, Center, new Vector2(0f, 170f), new Vector2(1200f, 120f));
            bannerRt = bannerText.rectTransform;
            bannerSub = Label(g, "BannerSub", "", 36, TextAnchor.MiddleCenter, new Color(1f, 1f, 1f, 0.9f), Center, new Vector2(0f, 92f), new Vector2(1200f, 50f));
            popupText = Label(g, "Popup", "", 34, TextAnchor.MiddleCenter, Gold, Center, new Vector2(0f, -80f), new Vector2(800f, 50f));
            popupRt = popupText.rectTransform;
            hintText = Label(g, "Hint", "", 34, TextAnchor.MiddleCenter, Gold, bc, new Vector2(0f, 175f), new Vector2(800f, 50f));

            // controls
            joyBase = NewRect(g, "Joystick", bl, new Vector2(250f, 235f), new Vector2(270f, 270f));
            joyDefaultPos = joyBase.anchoredPosition;
            joyBaseImg = joyBase.gameObject.AddComponent<Image>();
            joyBaseImg.sprite = Art.UISprite("ring");
            joyBaseImg.color = new Color(1f, 1f, 1f, 0.35f);
            joyBaseImg.raycastTarget = false;
            Img(joyBase, "Inner", Art.UISprite("circle"), new Color(0f, 0f, 0f, 0.22f), Center, Vector2.zero, new Vector2(250f, 250f));
            joyKnobImg = Img(joyBase, "Knob", Art.UISprite("circle"), new Color(1f, 1f, 1f, 0.5f), Center, Vector2.zero, new Vector2(118f, 118f));
            joyKnob = joyKnobImg.rectTransform;
            sprintIcon = Img(g, "Sprint", Art.UISprite("icon_run"), new Color(1f, 1f, 1f, 0f), bl, new Vector2(250f, 420f), new Vector2(64f, 64f));

            fireBtn = NewRect(g, "FireButton", br, new Vector2(-230f, 240f), new Vector2(232f, 232f));
            fireBg = fireBtn.gameObject.AddComponent<Image>();
            fireBg.sprite = Art.UISprite("circle");
            fireBg.color = new Color(1f, 1f, 1f, 0.16f);
            fireBg.raycastTarget = false;
            Img(fireBtn, "Ring", Art.UISprite("ring"), new Color(1f, 1f, 1f, 0.5f), Center, Vector2.zero, new Vector2(232f, 232f));
            Img(fireBtn, "Icon", Art.UISprite("icon_fire"), new Color(1f, 1f, 1f, 0.95f), Center, Vector2.zero, new Vector2(120f, 120f));
            ammoText = Label(g, "Ammo", "", 34, TextAnchor.MiddleCenter, Color.white, br, new Vector2(-230f, 410f), new Vector2(400f, 80f));

            reloadBtn = NewRect(g, "ReloadButton", br, new Vector2(-465f, 128f), new Vector2(128f, 128f));
            Image rbg = reloadBtn.gameObject.AddComponent<Image>();
            rbg.sprite = Art.UISprite("circle");
            rbg.color = new Color(1f, 1f, 1f, 0.15f);
            rbg.raycastTarget = false;
            Img(reloadBtn, "Icon", Art.UISprite("icon_reload"), new Color(1f, 1f, 1f, 0.95f), Center, Vector2.zero, new Vector2(72f, 72f));
            reloadRing = Img(reloadBtn, "Progress", Art.UISprite("ring"), Gold, Center, Vector2.zero, new Vector2(140f, 140f));
            reloadRing.type = Image.Type.Filled;
            reloadRing.fillMethod = Image.FillMethod.Radial360;
            reloadRing.fillOrigin = (int)Image.Origin360.Top;
            reloadRing.fillClockwise = true;
            reloadRing.fillAmount = 0f;
        }

        void BuildMenu()
        {
            RectTransform p = Stretch(root, "Menu");
            menuPanel = p.gameObject;
            FullImage(p, "Shade", Art.White, new Color(0f, 0f, 0f, 0.45f));
            Text z = Label(p, "Title1", "ZOMBIE", 150, TextAnchor.MiddleCenter, Red, Center, new Vector2(0f, 250f), new Vector2(1400f, 170f));
            var o = z.gameObject.AddComponent<Outline>();
            o.effectColor = new Color(0f, 0f, 0f, 0.9f);
            o.effectDistance = new Vector2(4f, -4f);
            Label(p, "Title2", "S T R I K E", 84, TextAnchor.MiddleCenter, Color.white, Center, new Vector2(0f, 135f), new Vector2(1400f, 100f));
            Label(p, "Subtitle", "SURVIVE THE UNDEAD HORDE", 30, TextAnchor.MiddleCenter, new Color(1f, 1f, 1f, 0.75f), Center, new Vector2(0f, 60f), new Vector2(1200f, 40f));
            playButton = MakeButton(p, "PLAY", new Vector2(0f, -90f), new Vector2(440f, 124f), new Color(0.75f, 0.09f, 0.07f, 0.95f), 62, () => GameManager.I.StartGame());
            menuBest = Label(p, "Best", "", 30, TextAnchor.MiddleCenter, Gold, Center, new Vector2(0f, -210f), new Vector2(1200f, 40f));
            Label(p, "Controls", "LEFT SIDE: MOVE   •   RIGHT SIDE: LOOK   •   HOLD FIRE TO SHOOT", 24, TextAnchor.MiddleCenter,
                new Color(1f, 1f, 1f, 0.7f), new Vector2(0.5f, 0f), new Vector2(0f, 70f), new Vector2(1500f, 34f));
        }

        void BuildPause()
        {
            RectTransform p = Stretch(root, "Pause");
            pausePanel = p.gameObject;
            FullImage(p, "Shade", Art.White, new Color(0f, 0f, 0f, 0.72f));
            Label(p, "Title", "PAUSED", 90, TextAnchor.MiddleCenter, Color.white, Center, new Vector2(0f, 280f), new Vector2(1000f, 110f));
            MakeButton(p, "RESUME", new Vector2(0f, 135f), new Vector2(440f, 104f), new Color(0.75f, 0.09f, 0.07f, 0.95f), 46, () => GameManager.I.Resume());
            MakeButton(p, "RESTART", new Vector2(0f, 15f), new Vector2(440f, 104f), new Color(0.25f, 0.25f, 0.28f, 0.95f), 46, () => GameManager.I.Restart());
            MakeButton(p, "-", new Vector2(-260f, -110f), new Vector2(110f, 96f), new Color(0.25f, 0.25f, 0.28f, 0.95f), 56, () => ChangeSensitivity(-0.1f));
            MakeButton(p, "+", new Vector2(260f, -110f), new Vector2(110f, 96f), new Color(0.25f, 0.25f, 0.28f, 0.95f), 56, () => ChangeSensitivity(0.1f));
            sensText = Label(p, "Sensitivity", "", 34, TextAnchor.MiddleCenter, Color.white, Center, new Vector2(0f, -110f), new Vector2(380f, 50f));
            MakeButton(p, "MAIN MENU", new Vector2(0f, -240f), new Vector2(360f, 92f), new Color(0.18f, 0.18f, 0.2f, 0.95f), 38, () => GameManager.I.GoToMenu());
        }

        void BuildGameOver()
        {
            RectTransform p = Stretch(root, "GameOver");
            overPanel = p.gameObject;
            FullImage(p, "Shade", Art.White, new Color(0.18f, 0f, 0f, 0.72f));
            Text t = Label(p, "Title", "YOU DIED", 128, TextAnchor.MiddleCenter, Red, Center, new Vector2(0f, 270f), new Vector2(1400f, 150f));
            var o = t.gameObject.AddComponent<Outline>();
            o.effectColor = new Color(0f, 0f, 0f, 0.9f);
            o.effectDistance = new Vector2(4f, -4f);
            overStats = Label(p, "Stats", "", 38, TextAnchor.MiddleCenter, Color.white, Center, new Vector2(0f, 95f), new Vector2(1200f, 170f));
            overStats.lineSpacing = 1.15f;
            overBest = Label(p, "Best", "", 32, TextAnchor.MiddleCenter, Gold, Center, new Vector2(0f, -30f), new Vector2(1200f, 44f));
            MakeButton(p, "PLAY AGAIN", new Vector2(0f, -150f), new Vector2(470f, 118f), new Color(0.75f, 0.09f, 0.07f, 0.95f), 50, () => GameManager.I.Restart());
            MakeButton(p, "MAIN MENU", new Vector2(0f, -285f), new Vector2(360f, 92f), new Color(0.22f, 0.22f, 0.24f, 0.95f), 38, () => GameManager.I.GoToMenu());
        }

        // ------------------------------------------------------------------ state

        public void SetState(GameState s)
        {
            menuPanel.SetActive(s == GameState.Menu);
            pausePanel.SetActive(s == GameState.Paused);
            overPanel.SetActive(s == GameState.GameOver);
            hudGroup.SetActive(s == GameState.Playing || s == GameState.Paused);
            pauseButton.Rect.gameObject.SetActive(s == GameState.Playing);
            if (s == GameState.Menu)
                menuBest.text = Settings.BestScore > 0 ? "BEST SCORE " + Settings.BestScore + "   •   BEST WAVE " + Settings.BestWave : "";
            if (s == GameState.Paused) RefreshSensitivity();
            foreach (UIButton b in buttons)
            {
                b.Finger = -1;
                b.MouseDown = false;
                b.Bg.color = b.Normal;
            }
        }

        public void ShowGameOver(int wave, int kills, int headshots, int score, float accuracy, bool record)
        {
            overStats.text = "WAVE " + wave + "\nKILLS " + kills + "   •   HEADSHOTS " + headshots + "   •   ACCURACY " + Mathf.RoundToInt(accuracy * 100f) + "%\nSCORE " + score;
            overBest.text = record ? "NEW BEST SCORE!" : "BEST SCORE " + Settings.BestScore;
        }

        void ChangeSensitivity(float delta)
        {
            Settings.LookSpeed = Mathf.Round((Settings.LookSpeed + delta) * 10f) / 10f;
            RefreshSensitivity();
        }

        void RefreshSensitivity()
        {
            sensText.text = "LOOK SPEED " + Settings.LookSpeed.ToString("0.0");
        }

        // ------------------------------------------------------------------ events

        public void ShowBanner(string text, string sub, Color color, float duration)
        {
            bannerText.text = text;
            bannerText.color = color;
            bannerSub.text = sub ?? "";
            bannerT = 0f;
            bannerDur = duration;
        }

        public void Popup(string text, Color color)
        {
            popupText.text = text;
            popupText.color = color;
            popupT = 0f;
        }

        public void Hint(string text, float duration)
        {
            hintText.text = text;
            hintT = duration;
        }

        public void HitMarker(bool kill, bool head)
        {
            hitT = 0f;
            hitKill = kill || head;
        }

        public void OnDamaged(float fraction, Vector3 from)
        {
            dmgFlash = Mathf.Min(1f, dmgFlash + 0.35f + fraction * 2f);
            dmgFrom = from;
            dmgArcT = 0f;
        }

        // ------------------------------------------------------------------ input

        public bool IsOverButton(Vector2 screenPos)
        {
            return ButtonAt(screenPos) != null;
        }

        UIButton ButtonAt(Vector2 p)
        {
            for (int i = buttons.Count - 1; i >= 0; i--)
            {
                UIButton b = buttons[i];
                if (b.Rect.gameObject.activeInHierarchy && RectTransformUtility.RectangleContainsScreenPoint(b.Rect, p, null)) return b;
            }
            return null;
        }

        void Press(UIButton b, bool down)
        {
            b.Bg.color = down ? new Color(b.Normal.r * 0.65f, b.Normal.g * 0.65f, b.Normal.b * 0.65f, b.Normal.a) : b.Normal;
            b.Rect.localScale = down ? new Vector3(0.95f, 0.95f, 1f) : Vector3.one;
        }

        void Click(UIButton b)
        {
            Press(b, false);
            if (Sfx.I != null) Sfx.I.Play2D("ui_click", 0.8f);
            if (b.OnClick != null) b.OnClick();
        }

        void HandleButtons()
        {
            int count = Input.touchCount;
            for (int i = 0; i < count; i++)
            {
                Touch t = Input.GetTouch(i);
                if (t.phase == TouchPhase.Began)
                {
                    UIButton b = ButtonAt(t.position);
                    if (b != null)
                    {
                        b.Finger = t.fingerId;
                        Press(b, true);
                    }
                }
                else if (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled)
                {
                    UIButton owner = null;
                    foreach (UIButton b in buttons) if (b.Finger == t.fingerId) owner = b;
                    if (owner != null)
                    {
                        owner.Finger = -1;
                        Press(owner, false);
                        if (t.phase == TouchPhase.Ended && owner.Rect.gameObject.activeInHierarchy &&
                            RectTransformUtility.RectangleContainsScreenPoint(owner.Rect, t.position, null))
                        {
                            Click(owner);
                            return;
                        }
                    }
                    else if (t.phase == TouchPhase.Ended)
                    {
                        // a very quick tap can arrive without its "began" frame
                        UIButton b = ButtonAt(t.position);
                        if (b != null)
                        {
                            Click(b);
                            return;
                        }
                    }
                }
            }
            // a touch that vanished without an "ended" event still counts as a tap
            foreach (UIButton b in buttons)
            {
                if (b.Finger < 0) continue;
                bool present = false;
                for (int i = 0; i < count; i++) if (Input.GetTouch(i).fingerId == b.Finger) present = true;
                if (!present)
                {
                    b.Finger = -1;
                    if (b.Rect.gameObject.activeInHierarchy)
                    {
                        Click(b);
                        return;
                    }
                    Press(b, false);
                }
            }
#if UNITY_EDITOR || UNITY_STANDALONE
            if (count == 0)
            {
                Vector2 m = Input.mousePosition;
                if (Input.GetMouseButtonDown(0))
                {
                    UIButton b = ButtonAt(m);
                    if (b != null) { b.MouseDown = true; Press(b, true); }
                }
                if (Input.GetMouseButtonUp(0))
                {
                    foreach (UIButton b in buttons)
                    {
                        if (!b.MouseDown) continue;
                        b.MouseDown = false;
                        Press(b, false);
                        if (b.Rect.gameObject.activeInHierarchy && RectTransformUtility.RectangleContainsScreenPoint(b.Rect, m, null))
                        {
                            Click(b);
                            return;
                        }
                    }
                }
            }
#endif
        }

        // ------------------------------------------------------------------ per frame

        void ApplySafeArea()
        {
            Rect s = Screen.safeArea;
            lastSafe = s;
            float w = Mathf.Max(Screen.width, 1), h = Mathf.Max(Screen.height, 1);
            safe.anchorMin = new Vector2(s.xMin / w, s.yMin / h);
            safe.anchorMax = new Vector2(s.xMax / w, s.yMax / h);
            safe.offsetMin = Vector2.zero;
            safe.offsetMax = Vector2.zero;
        }

        static float Radius(RectTransform rt)
        {
            return rt.rect.width * 0.5f * rt.lossyScale.x;
        }

        void UpdateLayout()
        {
            TouchControls tc = TouchControls.I;
            if (tc == null) return;
            tc.FireCenter = fireBtn.position;
            tc.FireRadius = Radius(fireBtn);
            tc.ReloadCenter = reloadBtn.position;
            tc.ReloadRadius = Radius(reloadBtn);
            tc.JoyRadius = Radius(joyBase) * 0.8f;

            layoutFrames++;
            if (layoutFrames == 3)
            {
                Vector3 joy = joyBase.position;
                Debug.Log("ZS-LAYOUT w=" + Screen.width + " h=" + Screen.height +
                          " play=" + Mathf.RoundToInt(playButton.Rect.position.x) + "," + Mathf.RoundToInt(playButton.Rect.position.y) +
                          " fire=" + Mathf.RoundToInt(tc.FireCenter.x) + "," + Mathf.RoundToInt(tc.FireCenter.y) +
                          " joy=" + Mathf.RoundToInt(joy.x) + "," + Mathf.RoundToInt(joy.y) +
                          " reload=" + Mathf.RoundToInt(tc.ReloadCenter.x) + "," + Mathf.RoundToInt(tc.ReloadCenter.y));
            }
        }

        void Update()
        {
            if (Screen.safeArea != lastSafe) ApplySafeArea();
            UpdateLayout();
            HandleButtons();

            float dt = Time.unscaledDeltaTime;
            GameManager gm = GameManager.I;
            if (gm == null) return;

            // vignettes
            dmgFlash = Mathf.MoveTowards(dmgFlash, 0f, dt * 1.6f);
            damageVignette.color = new Color(0.85f, 0f, 0f, dmgFlash * 0.75f);
            PlayerController p = PlayerController.I;
            float lowHp = 0f;
            if (p != null && p.Alive && p.Health < 35f && gm.State == GameState.Playing)
                lowHp = (0.25f + 0.2f * Mathf.Sin(Time.unscaledTime * 6f)) * (1f - p.Health / 35f) + 0.15f;
            lowHpVignette.color = new Color(0.6f, 0f, 0f, lowHp);

            if (!hudGroup.activeSelf || p == null) return;
            UpdateStats(gm, p);
            UpdateControls(p, dt);
            UpdateEffects(p, dt);
        }

        void UpdateStats(GameManager gm, PlayerController p)
        {
            int hp = Mathf.CeilToInt(p.Health);
            if (hp != lastHp)
            {
                lastHp = hp;
                float f = p.Health / PlayerController.MaxHealth;
                hpFill.fillAmount = f;
                hpFill.color = Color.Lerp(new Color(0.9f, 0.15f, 0.1f), new Color(0.3f, 0.85f, 0.35f), Mathf.Clamp01((f - 0.2f) / 0.5f));
                hpText.text = hp.ToString();
            }
            if (gm.Score != lastScore)
            {
                lastScore = gm.Score;
                scoreText.text = "SCORE " + gm.Score;
            }
            if (gm.Kills != lastKills)
            {
                lastKills = gm.Kills;
                killsText.text = "KILLS " + gm.Kills;
            }
            WaveSpawner w = gm.Waves;
            int wave = w != null ? w.Wave : 0;
            int remain = w != null ? w.Remaining : 0;
            if (wave != lastWave || remain != lastRemain)
            {
                lastWave = wave;
                lastRemain = remain;
                waveText.text = wave > 0 ? "WAVE " + wave : "GET READY";
                remainText.text = wave > 0 ? (w.Between ? "WAVE CLEARED" : "ZOMBIES LEFT " + remain) : "";
            }
            Weapon gun = p.Gun;
            if (gun != null && (gun.Mag != lastMag || gun.Reserve != lastReserve))
            {
                lastMag = gun.Mag;
                lastReserve = gun.Reserve;
                string magColor = gun.Mag == 0 ? "#FF4030" : (gun.Mag <= 7 ? "#FFC040" : "#FFFFFF");
                ammoText.text = "<color=" + magColor + "><size=64>" + gun.Mag + "</size></color><size=34>  / " + gun.Reserve + "</size>";
            }
            if (gun != null && !gun.Reloading && hintT <= 0f)
            {
                if (gun.Mag == 0 && gun.Reserve == 0) Hint("NO AMMO - FIND AMMO BOXES", 0.5f);
                else if (gun.Mag <= 5 && gun.Reserve > 0) Hint("TAP RELOAD", 0.5f);
            }
        }

        void UpdateControls(PlayerController p, float dt)
        {
            TouchControls tc = TouchControls.I;
            if (tc == null) return;
            if (tc.MoveActive)
            {
                joyBase.position = tc.MoveOrigin;
                joyKnob.anchoredPosition = tc.Move * (joyBase.rect.width * 0.5f * 0.8f);
                joyBaseImg.color = new Color(1f, 1f, 1f, 0.55f);
                joyKnobImg.color = new Color(1f, 1f, 1f, 0.8f);
            }
            else
            {
                joyBase.anchoredPosition = joyDefaultPos;
                joyKnob.anchoredPosition = Vector2.zero;
                joyBaseImg.color = new Color(1f, 1f, 1f, 0.3f);
                joyKnobImg.color = new Color(1f, 1f, 1f, 0.45f);
            }
            sprintIcon.color = new Color(1f, 1f, 1f, p.Sprinting ? 0.85f : 0f);
            fireBg.color = tc.FireHeld ? new Color(0.9f, 0.15f, 0.1f, 0.45f) : new Color(1f, 1f, 1f, 0.16f);
            Weapon gun = p.Gun;
            reloadRing.fillAmount = gun != null && gun.Reloading ? gun.ReloadProgress : 0f;
        }

        void UpdateEffects(PlayerController p, float dt)
        {
            Weapon gun = p.Gun;
            float spread = gun != null ? gun.Spread : 0.5f;
            float gap = 10f + spread * 9f;
            Color cc = gun != null && gun.OnTarget ? new Color(1f, 0.25f, 0.2f, 0.95f) : new Color(1f, 1f, 1f, 0.9f);
            cross[0].rectTransform.anchoredPosition = new Vector2(0f, gap + 9f);
            cross[1].rectTransform.anchoredPosition = new Vector2(0f, -gap - 9f);
            cross[2].rectTransform.anchoredPosition = new Vector2(-gap - 9f, 0f);
            cross[3].rectTransform.anchoredPosition = new Vector2(gap + 9f, 0f);
            for (int i = 0; i < 4; i++) cross[i].color = cc;
            crossDot.color = cc;

            if (hitT >= 0f)
            {
                hitT += dt;
                bool on = hitT < 0.22f;
                hitRoot.gameObject.SetActive(on);
                if (on)
                {
                    float s = 1.25f - hitT;
                    hitRoot.localScale = new Vector3(s, s, 1f);
                    Color hc = hitKill ? new Color(1f, 0.2f, 0.15f, 1f) : Color.white;
                    for (int i = 0; i < 4; i++) hitBars[i].color = hc;
                }
                else hitT = -1f;
            }

            if (dmgArcT >= 0f)
            {
                dmgArcT += dt;
                Vector3 d = dmgFrom - p.transform.position;
                d.y = 0f;
                float angle = d.sqrMagnitude > 0.01f ? Vector3.SignedAngle(p.transform.forward, d, Vector3.up) : 0f;
                dmgArc.localRotation = Quaternion.Euler(0f, 0f, -angle);
                float a = Mathf.Clamp01(1f - dmgArcT / 1.2f);
                dmgArcImg.color = new Color(1f, 0.1f, 0.05f, a * 0.85f);
                if (dmgArcT > 1.2f) dmgArcT = -1f;
            }

            if (bannerT >= 0f)
            {
                bannerT += dt;
                float inT = Mathf.Clamp01(bannerT / 0.25f);
                float outT = Mathf.Clamp01((bannerDur - bannerT) / 0.4f);
                float a = Mathf.Min(inT, outT);
                Color c = bannerText.color;
                bannerText.color = new Color(c.r, c.g, c.b, a);
                bannerSub.color = new Color(1f, 1f, 1f, a * 0.9f);
                float s = Mathf.Lerp(1.3f, 1f, Ease.OutCubic(inT));
                bannerRt.localScale = new Vector3(s, s, 1f);
                if (bannerT > bannerDur)
                {
                    bannerT = -1f;
                    bannerText.text = "";
                    bannerSub.text = "";
                }
            }

            if (popupT >= 0f)
            {
                popupT += dt;
                float a = Mathf.Clamp01(1.3f - popupT);
                Color c = popupText.color;
                popupText.color = new Color(c.r, c.g, c.b, a);
                popupRt.anchoredPosition = new Vector2(0f, -80f + popupT * 40f);
                if (popupT > 1.3f)
                {
                    popupT = -1f;
                    popupText.text = "";
                }
            }

            if (hintT > 0f)
            {
                hintT -= dt;
                hintText.color = new Color(1f, 0.8f, 0.25f, 0.6f + 0.4f * Mathf.Abs(Mathf.Sin(Time.unscaledTime * 5f)));
                if (hintT <= 0f) hintText.text = "";
            }
        }
    }
}
