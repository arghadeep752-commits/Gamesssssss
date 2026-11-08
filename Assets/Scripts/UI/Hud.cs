using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace GridProto
{
    /// <summary>
    /// Builds the on-screen controls at runtime: floating joystick (left), look area (right),
    /// jump / crouch / pause buttons, the interact button that pops up near the door, and the pause menu.
    /// </summary>
    public class Hud : MonoBehaviour
    {
        public PlayerController player;
        public PlayerInteractor interactor;
        public GameRoot root;

        static readonly Vector2 Center = new Vector2(0.5f, 0.5f);
        static readonly Color ButtonFill = new Color(0f, 0f, 0f, 0.38f);
        static readonly Color RingColor = new Color(1f, 1f, 1f, 0.6f);
        static readonly Color Accent = new Color(1f, 0.78f, 0.35f, 0.95f);
        static readonly Color MenuButtonColor = new Color(1f, 1f, 1f, 0.12f);
        static readonly Color ResumeColor = new Color(0.96f, 0.55f, 0.24f, 1f);

        Font font;
        RectTransform canvasRect, safe, controlsRoot;
        Image vignette, flash, fade;
        GameObject caughtPanel;
        Color flashColor;
        float flashAlpha, fadeTarget, fadeSpeed = 1f;
        bool gameOver;
        RectTransform interactWrap;
        CanvasGroup interactGroup;
        Text interactLabel;
        Text infoText;
        Image crouchRing;
        GameObject pauseMenu;
        Text sensitivityValue, graphicsValue, fpsValue;
        AudioSource uiAudio;
        float interactShow, interactScale = -1f;
        float fpsTimer;
        int fpsFrames;
        bool paused;

        public bool IsPaused { get { return paused; } }

        void Awake()
        {
            font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            uiAudio = gameObject.AddComponent<AudioSource>();
            uiAudio.playOnAwake = false;
            uiAudio.spatialBlend = 0f;
            uiAudio.ignoreListenerPause = true;
            EnsureEventSystem();
            BuildHud();
            BuildPauseMenu();
            BuildOverlays();
            pauseMenu.SetActive(false);
            interactWrap.gameObject.SetActive(false);
        }

        static void EnsureEventSystem()
        {
            if (EventSystem.current != null) return;
            var go = new GameObject("EventSystem");
            var system = go.AddComponent<EventSystem>();
            system.pixelDragThreshold = 5;
            go.AddComponent<StandaloneInputModule>();
        }

        void BuildHud()
        {
            var canvasGo = new GameObject("HUD Canvas", typeof(RectTransform));
            canvasGo.transform.SetParent(transform, false);
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var scaler = canvasGo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 1f;
            scaler.referencePixelsPerUnit = 100f;
            canvasGo.AddComponent<GraphicRaycaster>();
            canvasRect = (RectTransform)canvasGo.transform;

            // red screen edges while the enemy is hunting you (drawn under the controls)
            RectTransform vignetteRect = Stretch("Danger", canvasRect, Vector2.zero, Vector2.one);
            vignette = vignetteRect.gameObject.AddComponent<Image>();
            vignette.sprite = UISprites.Vignette;
            vignette.color = new Color(0.75f, 0f, 0f, 0f);
            vignette.raycastTarget = false;
            vignette.enabled = false;

            // everything the player touches lives under one root, hidden while the enemy has them
            controlsRoot = Stretch("Controls", canvasRect, Vector2.zero, Vector2.one);

            // touch areas first, so every button is drawn and hit-tested on top of them
            RectTransform lookZone = Stretch("Look Area", controlsRoot, new Vector2(0.42f, 0f), Vector2.one);
            lookZone.gameObject.AddComponent<RaycastArea>();
            lookZone.gameObject.AddComponent<TouchLookArea>();

            RectTransform moveZone = NewRect("Move Area", controlsRoot);
            moveZone.pivot = Vector2.zero;
            moveZone.anchorMin = Vector2.zero;
            moveZone.anchorMax = new Vector2(0.42f, 1f);
            moveZone.offsetMin = Vector2.zero;
            moveZone.offsetMax = Vector2.zero;
            moveZone.gameObject.AddComponent<RaycastArea>();

            Vector2 rest = new Vector2(300f, 270f);
            RectTransform joyBase = Box("Joystick", moveZone, Vector2.zero, rest, new Vector2(280f, 280f));
            AddImage(joyBase, UISprites.Circle, new Color(0f, 0f, 0f, 0.22f), false);
            RectTransform ringRect = Box("Ring", joyBase, Center, Vector2.zero, new Vector2(280f, 280f));
            Image joyRing = AddImage(ringRect, UISprites.Ring, new Color(1f, 1f, 1f, 0.55f), false);
            RectTransform knob = Box("Knob", joyBase, Center, Vector2.zero, new Vector2(124f, 124f));
            AddImage(knob, UISprites.Circle, new Color(1f, 1f, 1f, 0.82f), false);
            var joyGroup = joyBase.gameObject.AddComponent<CanvasGroup>();
            joyGroup.blocksRaycasts = false;
            joyGroup.interactable = false;
            joyGroup.alpha = 0.55f;
            var joystick = moveZone.gameObject.AddComponent<FloatingJoystick>();
            joystick.zone = moveZone;
            joystick.baseRect = joyBase;
            joystick.knob = knob;
            joystick.ring = joyRing;
            joystick.group = joyGroup;
            joystick.radius = 120f;
            joystick.restPosition = rest;

            RectTransform cross = Box("Crosshair", controlsRoot, Center, Vector2.zero, new Vector2(9f, 9f));
            AddImage(cross, UISprites.Dot, new Color(1f, 1f, 1f, 0.8f), false);

            safe = Stretch("Safe Area", controlsRoot, Vector2.zero, Vector2.one);
            safe.gameObject.AddComponent<SafeArea>();

            infoText = MakeText("Info", safe, new Vector2(0f, 1f), new Vector2(0f, 0.5f), new Vector2(36f, -40f),
                                new Vector2(700f, 44f), 26, TextAnchor.MiddleLeft, new Color(1f, 1f, 1f, 0.85f));

            Vector2 bottomRight = new Vector2(1f, 0f);
            Text noLabel;
            Image noRing;
            MakeRoundButton("Jump", safe, bottomRight, new Vector2(-210f, 220f), 210f, UISprites.JumpIcon, "JUMP",
                            () => TouchState.JumpPressed = true, out noLabel, out noRing);
            MakeRoundButton("Crouch", safe, bottomRight, new Vector2(-455f, 140f), 150f, UISprites.CrouchIcon, "CROUCH",
                            () => TouchState.CrouchPressed = true, out noLabel, out crouchRing);
            MakeRoundButton("Pause", safe, Vector2.one, new Vector2(-92f, -92f), 104f, UISprites.PauseIcon, null,
                            () => { Click(); SetPaused(true); }, out noLabel, out noRing);

            // interact button: only shown when the player is close to something usable (the door)
            interactWrap = Box("Interact", safe, bottomRight, new Vector2(-330f, 480f), new Vector2(190f, 190f));
            interactGroup = interactWrap.gameObject.AddComponent<CanvasGroup>();
            MakeRoundButton("Interact Button", interactWrap, Center, Vector2.zero, 190f, UISprites.DoorIcon, "OPEN",
                            () => TouchState.InteractPressed = true, out interactLabel, out noRing);
        }

        void BuildPauseMenu()
        {
            RectTransform dim = Stretch("Pause Menu", canvasRect, Vector2.zero, Vector2.one);
            var dimImage = dim.gameObject.AddComponent<Image>();
            dimImage.color = new Color(0f, 0f, 0f, 0.55f);
            dimImage.raycastTarget = true;
            pauseMenu = dim.gameObject;

            RectTransform panel = Box("Panel", dim, Center, Vector2.zero, new Vector2(880f, 660f));
            Image panelImage = AddImage(panel, UISprites.Rounded, new Color(0.08f, 0.09f, 0.1f, 0.94f), true);
            panelImage.type = Image.Type.Sliced;

            Vector2 top = new Vector2(0.5f, 1f);
            MakeText("Title", panel, top, Center, new Vector2(0f, -72f), new Vector2(700f, 70f), 50,
                     TextAnchor.MiddleCenter, Color.white).text = "PAUSED";

            float y = -190f;
            Label(panel, "Look sensitivity", y);
            MenuButton(panel, new Vector2(150f, y), new Vector2(90f, 76f), "-", () => ChangeSensitivity(-0.1f), MenuButtonColor);
            sensitivityValue = MakeText("Value", panel, top, Center, new Vector2(262f, y), new Vector2(120f, 60f), 36,
                                        TextAnchor.MiddleCenter, Color.white);
            MenuButton(panel, new Vector2(374f, y), new Vector2(90f, 76f), "+", () => ChangeSensitivity(0.1f), MenuButtonColor);

            y -= 115f;
            Label(panel, "Graphics", y);
            graphicsValue = MenuButton(panel, new Vector2(262f, y), new Vector2(314f, 76f), "HIGH", ToggleGraphics, MenuButtonColor);

            y -= 115f;
            Label(panel, "FPS counter", y);
            fpsValue = MenuButton(panel, new Vector2(262f, y), new Vector2(314f, 76f), "ON", ToggleFps, MenuButtonColor);

            MenuButton(panel, new Vector2(0f, -572f), new Vector2(440f, 96f), "RESUME", () => SetPaused(false), ResumeColor);
            RefreshMenu();
        }

        void BuildOverlays()
        {
            RectTransform flashRect = Stretch("Flash", canvasRect, Vector2.zero, Vector2.one);
            flash = flashRect.gameObject.AddComponent<Image>();
            flash.color = new Color(1f, 1f, 1f, 0f);
            flash.raycastTarget = false;
            flash.enabled = false;

            RectTransform fadeRect = Stretch("Fade", canvasRect, Vector2.zero, Vector2.one);
            fade = fadeRect.gameObject.AddComponent<Image>();
            fade.color = new Color(0f, 0f, 0f, 0f);
            fade.raycastTarget = false;
            fade.enabled = false;

            RectTransform panel = Stretch("Caught", canvasRect, Vector2.zero, Vector2.one);
            var block = panel.gameObject.AddComponent<Image>();
            block.color = new Color(0f, 0f, 0f, 0.2f);
            block.raycastTarget = true;
            caughtPanel = panel.gameObject;
            MakeText("Title", panel, Center, Center, new Vector2(0f, 140f), new Vector2(1400f, 120f), 84,
                     TextAnchor.MiddleCenter, new Color(0.85f, 0.08f, 0.06f, 1f)).text = "YOU WERE CAUGHT";
            MakeText("Subtitle", panel, Center, Center, new Vector2(0f, 40f), new Vector2(1400f, 60f), 34,
                     TextAnchor.MiddleCenter, new Color(1f, 1f, 1f, 0.75f)).text = "The hooded man got you.";
            RectTransform button = Box("Try Again", panel, Center, new Vector2(0f, -110f), new Vector2(460f, 104f));
            Image image = AddImage(button, UISprites.Rounded, ResumeColor, true);
            image.type = Image.Type.Sliced;
            var tryAgain = button.gameObject.AddComponent<Button>();
            tryAgain.targetGraphic = image;
            tryAgain.onClick.AddListener(() => { Click(); Restart(); });
            MakeText("Text", button, Center, Center, Vector2.zero, new Vector2(460f, 104f), 40, TextAnchor.MiddleCenter, Color.white).text = "TRY AGAIN";
            caughtPanel.SetActive(false);
        }

        /// <summary>Shows or hides every on-screen control (used during the jumpscare).</summary>
        public void SetControlsVisible(bool visible)
        {
            if (controlsRoot != null) controlsRoot.gameObject.SetActive(visible);
            if (!visible) TouchState.Clear();
        }

        public void Flash(Color color)
        {
            flashColor = color;
            flashAlpha = color.a;
            flash.color = color;
            flash.enabled = true;
        }

        public void FadeToBlack(float seconds)
        {
            fadeTarget = 1f;
            fadeSpeed = 1f / Mathf.Max(0.05f, seconds);
            fade.enabled = true;
        }

        public void ShowCaught()
        {
            gameOver = true;
            caughtPanel.SetActive(true);
        }

        void Restart()
        {
            Time.timeScale = 1f;
            AudioListener.pause = false;
            TouchState.Clear();
            UnityEngine.SceneManagement.SceneManager.LoadScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene().buildIndex);
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape) && !gameOver && controlsRoot.gameObject.activeSelf) SetPaused(!paused);   // Android back button

            // danger: red screen edges, pulsing faster as the enemy closes in
            float threat = root != null && root.enemy != null ? root.enemy.Threat : 0f;
            float pulse = 0.8f + 0.2f * Mathf.Sin(Time.unscaledTime * Mathf.Lerp(5f, 9f, threat));
            float vignetteAlpha = threat * 0.55f * pulse;
            if (Mathf.Abs(vignette.color.a - vignetteAlpha) > 0.004f) vignette.color = new Color(0.75f, 0f, 0f, vignetteAlpha);
            vignette.enabled = vignetteAlpha > 0.01f;

            // punch flashes fade out; the blackout fades in
            if (flashAlpha > 0f)
            {
                flashAlpha = Mathf.MoveTowards(flashAlpha, 0f, Time.unscaledDeltaTime * 2.2f);
                flash.color = new Color(flashColor.r, flashColor.g, flashColor.b, flashAlpha);
                flash.enabled = flashAlpha > 0.003f;
            }
            if (fade.enabled && !Mathf.Approximately(fade.color.a, fadeTarget))
                fade.color = new Color(0f, 0f, 0f, Mathf.MoveTowards(fade.color.a, fadeTarget, Time.unscaledDeltaTime * fadeSpeed));

            // interact button pops in when close to the door, and out again when walking away
            Interactable current = (!paused && interactor != null) ? interactor.Current : null;
            interactShow = Mathf.MoveTowards(interactShow, current != null ? 1f : 0f, Time.unscaledDeltaTime * 7f);
            bool visible = interactShow > 0.001f;
            if (interactWrap.gameObject.activeSelf != visible) interactWrap.gameObject.SetActive(visible);
            if (visible)
            {
                float s = EaseOutBack(interactShow);
                if (Mathf.Abs(s - interactScale) > 0.0005f)
                {
                    interactScale = s;
                    interactWrap.localScale = new Vector3(s, s, 1f);
                }
                interactGroup.alpha = Mathf.Clamp01(interactShow * 1.5f);
                interactGroup.blocksRaycasts = current != null;
                if (current != null && interactLabel != null && interactLabel.text != current.Prompt) interactLabel.text = current.Prompt;
            }

            if (crouchRing != null && player != null)
            {
                Color want = player.IsCrouching ? Accent : RingColor;
                if (crouchRing.color != want) crouchRing.color = want;
            }

            fpsFrames++;
            fpsTimer += Time.unscaledDeltaTime;
            if (fpsTimer >= 0.5f)
            {
                int fps = Mathf.RoundToInt(fpsFrames / fpsTimer);
                fpsFrames = 0;
                fpsTimer = 0f;
                infoText.text = GameSettings.ShowFps ? fps + " FPS  |  " + Screen.width + " x " + Screen.height : "";
            }
        }

        public void SetPaused(bool value)
        {
            paused = value;
            pauseMenu.SetActive(value);
            Time.timeScale = value ? 0f : 1f;
            AudioListener.pause = value;
            TouchState.Clear();
            RefreshMenu();
        }

        void OnApplicationPause(bool appPaused)
        {
            if (appPaused && !paused && pauseMenu != null) SetPaused(true);
        }

        void RefreshMenu()
        {
            if (sensitivityValue != null)
                sensitivityValue.text = GameSettings.Sensitivity.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture);
            if (graphicsValue != null) graphicsValue.text = GameSettings.HighQuality ? "HIGH" : "LOW";
            if (fpsValue != null) fpsValue.text = GameSettings.ShowFps ? "ON" : "OFF";
        }

        void ChangeSensitivity(float delta)
        {
            GameSettings.Sensitivity = Mathf.Clamp(Mathf.Round((GameSettings.Sensitivity + delta) * 10f) / 10f, 0.2f, 3f);
            GameSettings.Save();
            RefreshMenu();
        }

        void ToggleGraphics()
        {
            GameSettings.HighQuality = !GameSettings.HighQuality;
            GameSettings.Save();
            if (root != null) root.ApplyGraphics();
            RefreshMenu();
        }

        void ToggleFps()
        {
            GameSettings.ShowFps = !GameSettings.ShowFps;
            GameSettings.Save();
            if (!GameSettings.ShowFps) infoText.text = "";
            RefreshMenu();
        }

        void Click()
        {
            if (uiAudio != null) uiAudio.PlayOneShot(ProtoAudio.Click, 0.4f);
        }

        static float EaseOutBack(float t)
        {
            const float c1 = 1.70158f;
            const float c3 = c1 + 1f;
            float u = t - 1f;
            return 1f + c3 * u * u * u + c1 * u * u;
        }

        // ---------- UI building helpers ----------

        RectTransform MakeRoundButton(string name, RectTransform parent, Vector2 anchor, Vector2 position, float size, Sprite icon,
                                      string label, System.Action onPress, out Text labelText, out Image ringImage)
        {
            RectTransform rt = Box(name, parent, anchor, position, new Vector2(size, size));
            Image fill = AddImage(rt, UISprites.Circle, ButtonFill, true);
            RectTransform ringRect = Box("Ring", rt, Center, Vector2.zero, new Vector2(size, size));
            ringImage = AddImage(ringRect, UISprites.Ring, RingColor, false);
            bool hasLabel = !string.IsNullOrEmpty(label);
            float iconSize = size * (hasLabel ? 0.44f : 0.5f);
            RectTransform iconRect = Box("Icon", rt, Center, new Vector2(0f, hasLabel ? size * 0.1f : 0f), new Vector2(iconSize, iconSize));
            AddImage(iconRect, icon, Color.white, false);
            labelText = null;
            if (hasLabel)
            {
                labelText = MakeText("Label", rt, Center, Center, new Vector2(0f, -size * 0.25f), new Vector2(size, 40f),
                                     Mathf.RoundToInt(size * 0.12f), TextAnchor.MiddleCenter, Color.white);
                labelText.text = label;
            }
            var button = rt.gameObject.AddComponent<TouchButton>();
            button.fill = fill;
            button.normalColor = ButtonFill;
            button.onPress = onPress;
            return rt;
        }

        void Label(RectTransform panel, string text, float y)
        {
            MakeText("Label", panel, new Vector2(0.5f, 1f), new Vector2(0f, 0.5f), new Vector2(-390f, y), new Vector2(420f, 60f), 34,
                     TextAnchor.MiddleLeft, new Color(1f, 1f, 1f, 0.9f)).text = text;
        }

        Text MenuButton(RectTransform parent, Vector2 position, Vector2 size, string label, System.Action onClick, Color color)
        {
            RectTransform rt = Box("Button " + label, parent, new Vector2(0.5f, 1f), position, size);
            Image image = AddImage(rt, UISprites.Rounded, color, true);
            image.type = Image.Type.Sliced;
            var button = rt.gameObject.AddComponent<Button>();
            button.targetGraphic = image;
            button.onClick.AddListener(() => { Click(); onClick(); });
            Text text = MakeText("Text", rt, Center, Center, Vector2.zero, size, 34, TextAnchor.MiddleCenter, Color.white);
            text.text = label;
            return text;
        }

        Text MakeText(string name, Transform parent, Vector2 anchor, Vector2 pivot, Vector2 position, Vector2 size,
                      int fontSize, TextAnchor alignment, Color color)
        {
            RectTransform rt = NewRect(name, parent);
            rt.anchorMin = anchor;
            rt.anchorMax = anchor;
            rt.pivot = pivot;
            rt.sizeDelta = size;
            rt.anchoredPosition = position;
            var text = rt.gameObject.AddComponent<Text>();
            text.font = font;
            text.fontSize = fontSize;
            text.fontStyle = FontStyle.Bold;
            text.alignment = alignment;
            text.color = color;
            text.horizontalOverflow = HorizontalWrapMode.Overflow;
            text.verticalOverflow = VerticalWrapMode.Overflow;
            text.raycastTarget = false;
            var shadow = rt.gameObject.AddComponent<Shadow>();
            shadow.effectColor = new Color(0f, 0f, 0f, 0.45f);
            shadow.effectDistance = new Vector2(1.5f, -1.5f);
            return text;
        }

        static RectTransform NewRect(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            return (RectTransform)go.transform;
        }

        static RectTransform Stretch(string name, Transform parent, Vector2 anchorMin, Vector2 anchorMax)
        {
            RectTransform rt = NewRect(name, parent);
            rt.anchorMin = anchorMin;
            rt.anchorMax = anchorMax;
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            return rt;
        }

        static RectTransform Box(string name, Transform parent, Vector2 anchor, Vector2 position, Vector2 size)
        {
            RectTransform rt = NewRect(name, parent);
            rt.anchorMin = anchor;
            rt.anchorMax = anchor;
            rt.pivot = Center;
            rt.sizeDelta = size;
            rt.anchoredPosition = position;
            return rt;
        }

        static Image AddImage(RectTransform rt, Sprite sprite, Color color, bool raycast)
        {
            var image = rt.gameObject.AddComponent<Image>();
            image.sprite = sprite;
            image.color = color;
            image.raycastTarget = raycast;
            return image;
        }
    }
}
