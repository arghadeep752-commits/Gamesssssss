using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace TradersMadness
{
    /// <summary>
    /// TRADER'S MADNESS. Menu -> risk level -> intro -> five days to escape the binary trader's house -> caught /
    /// liquidated / escaped. The main door is held shut by three planks (claw hammer), a gold and a silver padlock
    /// (keys from the safe and the trading desk's drawer) and a six-digit code (shown on his trading PC once the
    /// fuse is back in the fuse box).
    /// </summary>
    public class Game : MonoBehaviour
    {
        public enum S { Menu, Play, Cut, Pause, Overlay }

        public static readonly Color SkyColor = new Color(0.01f, 0.014f, 0.025f);
        static readonly string[] Modes = { "LOW RISK", "MEDIUM RISK", "HIGH RISK" };
        static readonly string[] ModeSub = { "EASY", "NORMAL", "HARD" };
        const int Days = 5;

        public S state = S.Menu;
        public int mode = 1, day = 1;
        public float sensitivity = 1f, volume = 1f;
        public int graphics = 1;
        public bool floatingJoy = true;
        public string held = "";
        public bool skip, busy;
        public Level level;
        public Player player;
        public Enemy trader;
        public GameAudio sound;
        public Hud hud;
        public Camera cutCam;

        Level.Hide hideRef;
        float nearT, chaseVol = -60f;
        readonly List<Level.Item> near = new List<Level.Item>();
        GameObject world;
        Camera bgCam;
        Transform listener;
        Canvas canvas;
        RectTransform menu, overlay;
        CanvasGroup menuGroup;
        Image fade, flash;
        Text caption, big, sub;
        Button skipBtn;
        int nativeW, nativeH;
        S beforeOverlay;

        // ============================================================================================== start
        void Start()
        {
            Application.targetFrameRate = 60;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            Input.multiTouchEnabled = true;
            Shader.SetGlobalFloat("_TMFogDensity", 0.006f);
            Shader.SetGlobalVector("_TMFogColor", new Vector4(0.01f, 0.012f, 0.02f, 1f));
            Shader.SetGlobalFloat("_TMExposure", 1.0f);
            Ui.LoadFonts();
            nativeW = Display.main.systemWidth;
            nativeH = Display.main.systemHeight;
            sensitivity = PlayerPrefs.GetFloat("sensitivity", 1f);
            volume = PlayerPrefs.GetFloat("volume", 1f);
            graphics = PlayerPrefs.GetInt("graphics", 1);
            floatingJoy = PlayerPrefs.GetInt("floating_joystick", 1) == 1;
            AudioListener.volume = volume;
            ApplyGraphics();

            var bg = new GameObject("Background camera");
            bg.transform.SetParent(transform, false);
            bgCam = bg.AddComponent<Camera>();
            bgCam.clearFlags = CameraClearFlags.SolidColor;
            bgCam.backgroundColor = Color.black;
            bgCam.cullingMask = 0;
            bgCam.depth = -100;
            var lg = new GameObject("Listener");
            lg.transform.SetParent(transform, false);
            lg.AddComponent<AudioListener>();
            listener = lg.transform;

            var ag = new GameObject("Audio");
            ag.transform.SetParent(transform, false);
            sound = ag.AddComponent<GameAudio>();

            canvas = Ui.MakeCanvas("UI", 0);
            canvas.transform.SetParent(transform, false);
            Ui.EnsureEventSystem();
            hud = Hud.Create(canvas.transform, Ui.ui);
            hud.floating = floatingJoy;
            hud.gameObject.SetActive(false);
            hud.onInteract = Interact;
            hud.onDrop = () => Drop(false);
            hud.onCrouch = Crouch;
            hud.onPause = Pause;
            flash = Ui.Rect(canvas.transform, new Color(0.7f, 0f, 0f, 0f), "Flash");
            fade = Ui.Rect(canvas.transform, new Color(0f, 0f, 0f, 0f), "Fade");
            caption = Ui.Label(canvas.transform, Ui.ui, 30, new Color(0.93f, 0.95f, 0.94f), "Caption");
            RectTransform cr = caption.rectTransform;
            cr.anchorMin = new Vector2(0f, 0f);
            cr.anchorMax = new Vector2(1f, 0f);
            cr.offsetMin = new Vector2(100f, 50f);
            cr.offsetMax = new Vector2(-100f, 150f);
            big = Ui.Label(canvas.transform, Ui.title, 120, Ui.Red, "Big");
            big.horizontalOverflow = HorizontalWrapMode.Overflow;
            sub = Ui.Label(canvas.transform, Ui.mono, 26, Ui.Text, "Sub");
            sub.rectTransform.offsetMax = new Vector2(0f, -200f);
            menu = Ui.Node(canvas.transform, "Menu");
            Ui.Full(menu);
            menuGroup = menu.gameObject.AddComponent<CanvasGroup>();
            overlay = Ui.Node(canvas.transform, "Overlay");
            Ui.Full(overlay);
            MakeSkipButton();
            ShowMainMenu();
#if TM_AUTOTEST
            gameObject.AddComponent<AutoTest>();
#endif
        }

        void ApplyGraphics()
        {
            float[] scale = { 0.62f, 0.8f, 1f };
            int[] msaa = { 0, 2, 4 };
            graphics = Mathf.Clamp(graphics, 0, 2);
            if (nativeW > 0 && nativeH > 0)
                Screen.SetResolution(Mathf.RoundToInt(nativeW * scale[graphics]), Mathf.RoundToInt(nativeH * scale[graphics]), true);
            QualitySettings.antiAliasing = msaa[graphics];
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape)) Back();
            if (flash.color.a > 0f)
            {
                Color c = flash.color;
                c.a = Mathf.Max(0f, c.a - Time.unscaledDeltaTime * 1.4f);
                flash.color = c;
            }
            if (state == S.Play && player != null) PlayUpdate(Time.deltaTime);
            if ((state == S.Play || state == S.Overlay) && trader != null && sound != null)
            {
                bool chase = trader.state == Enemy.State.Chase;
                chaseVol = Mathf.MoveTowards(chaseVol, chase ? -6f : -60f, Time.deltaTime * (chase ? 60f : 15f));
                sound.Loop("chase_music", chaseVol);
                sound.Loop("heartbeat", chase ? -6f : -60f);
            }
        }

        void LateUpdate()
        {
            Camera c = cutCam != null && cutCam.enabled ? cutCam : (player != null && player.cam.enabled ? player.cam : null);
            if (c != null) listener.SetPositionAndRotation(c.transform.position, c.transform.rotation);
        }

        void Back()
        {
            switch (state)
            {
                case S.Play: Pause(); break;
                case S.Pause: Resume(); break;
                case S.Overlay: CloseOverlay(); break;
                case S.Menu: if (!busy) ShowMainMenu(); break;
                case S.Cut: if (skipBtn.gameObject.activeSelf) OnSkip(); break;
            }
        }

        // ============================================================================================== menus
        void ClearMenu()
        {
            for (int i = menu.childCount - 1; i >= 0; i--) Destroy(menu.GetChild(i).gameObject);
            menu.DetachChildren();
            menuGroup.alpha = 1f;
        }

        void MenuBg(float alpha = 1f)
        {
            Image bg = Ui.Rect(menu, new Color(Ui.Bg.r, Ui.Bg.g, Ui.Bg.b, alpha), "Background");
            bg.raycastTarget = true;
        }

        /// <summary>The trading terminal backdrop: the live chart, a red vignette and the ticker tape.</summary>
        void TerminalBackdrop(float chartAlpha)
        {
            MenuBg();
            RectTransform cr = Ui.Node(menu, "Chart");
            Ui.Full(cr);
            cr.offsetMin = new Vector2(0f, 46f);
            cr.offsetMax = new Vector2(0f, -40f);
            var chart = cr.gameObject.AddComponent<MenuChart>();
            chart.alpha = chartAlpha;
            Image vig = Ui.Rect(menu, new Color(0.25f, 0f, 0.02f, 0.18f), "Red wash");
            vig.raycastTarget = false;
            // ticker tape along the bottom
            RectTransform tape = Ui.Node(menu, "Ticker");
            tape.anchorMin = new Vector2(0f, 0f);
            tape.anchorMax = new Vector2(1f, 0f);
            tape.pivot = new Vector2(0.5f, 0f);
            tape.sizeDelta = new Vector2(0f, 42f);
            var tb = tape.gameObject.AddComponent<Image>();
            tb.color = new Color(0f, 0f, 0f, 0.85f);
            Text tt = Ui.Label(tape, Ui.mono, 22, Ui.Text, "Ticker text");
            tt.horizontalOverflow = HorizontalWrapMode.Overflow;
            tt.alignment = TextAnchor.MiddleLeft;
            tt.gameObject.AddComponent<Ticker>();
            // header bar
            RectTransform head = Ui.Node(menu, "Header");
            head.anchorMin = new Vector2(0f, 1f);
            head.anchorMax = new Vector2(1f, 1f);
            head.pivot = new Vector2(0.5f, 1f);
            head.sizeDelta = new Vector2(0f, 40f);
            var hb = head.gameObject.AddComponent<Image>();
            hb.color = new Color(0f, 0f, 0f, 0.7f);
            Text ht = Ui.Label(head, Ui.mono, 20, Ui.TextDim, "Header text");
            ht.alignment = TextAnchor.MiddleLeft;
            ht.rectTransform.offsetMin = new Vector2(20f, 0f);
            ht.text = "OPTION-X TERMINAL  //  ACCOUNT TRDR-0991  //  <color=#FA2E3C>MARGIN CALL</color>  //  SESSION: NIGHT";
            ht.horizontalOverflow = HorizontalWrapMode.Overflow;
        }

        IEnumerator FadeInMenu()
        {
            menuGroup.alpha = 0f;
            float t = 0f;
            while (t < 0.6f)
            {
                t += Time.unscaledDeltaTime;
                menuGroup.alpha = Mathf.Clamp01(t / 0.6f);
                yield return null;
            }
            menuGroup.alpha = 1f;
        }

        public void ShowMainMenu()
        {
            state = S.Menu;
            Time.timeScale = 1f;
            hud.gameObject.SetActive(false);
            CloseOverlayNodes();
            big.text = "";
            sub.text = "";
            caption.text = "";
            SetAlpha(fade, 0f);
            ClearMenu();
            TerminalBackdrop(0.5f);
            if (sound != null)
            {
                sound.StopAll();
                sound.Loop("menu_music", -10f);
                sound.Loop("rain", -22f);
            }
            // the title: red and green offset copies behind a white one (a glitchy screen)
            Text g1 = Ui.TextMid(menu, "TRADER'S MADNESS", Ui.title, 150, new Color(1f, 0.1f, 0.2f, 0.55f), -4f, -168f, 1400f, 170f);
            Text g2 = Ui.TextMid(menu, "TRADER'S MADNESS", Ui.title, 150, new Color(0.1f, 1f, 0.55f, 0.45f), 4f, -162f, 1400f, 170f);
            Text t0 = Ui.TextMid(menu, "TRADER'S MADNESS", Ui.title, 150, Ui.Text, 0f, -165f, 1400f, 170f);
            g1.gameObject.AddComponent<Glitch>().amount = 5f;
            g2.gameObject.AddComponent<Glitch>().amount = -5f;
            t0.raycastTarget = false;
            Ui.TextMid(menu, "ESCAPE THE BINARY TRADER", Ui.mono, 26, Ui.Green, 0f, -72f, 1000f, 40f);
            Ui.TermButton(menu, "PLAY", 0f, 30f, 360f, 70f, ShowModes, 38);
            Ui.TermButton(menu, "SETTINGS", 0f, 118f, 360f, 70f, ShowSettings, 38);
            Ui.TermButton(menu, "EXIT", 0f, 206f, 360f, 70f, Application.Quit, 38, Ui.Red);
            Text v = Ui.TextMid(menu, "v" + Application.version, Ui.mono, 18, Ui.TextDim, 0f, 0f, 300f, 30f, TextAnchor.LowerRight);
            v.rectTransform.anchorMin = new Vector2(1f, 0f);
            v.rectTransform.anchorMax = new Vector2(1f, 0f);
            v.rectTransform.pivot = new Vector2(1f, 0f);
            v.rectTransform.anchoredPosition = new Vector2(-16f, 50f);
            StartCoroutine(FadeInMenu());
        }

        void SaveSettings()
        {
            PlayerPrefs.SetFloat("sensitivity", sensitivity);
            PlayerPrefs.SetFloat("volume", volume);
            PlayerPrefs.SetInt("graphics", graphics);
            PlayerPrefs.SetInt("floating_joystick", floatingJoy ? 1 : 0);
            PlayerPrefs.Save();
            if (player != null) player.sensitivity = sensitivity;
            if (hud != null) hud.floating = floatingJoy;
            AudioListener.volume = volume;
        }

        void Row(Transform parent, string label, float y)
        {
            Ui.TextMid(parent, label, Ui.mono, 24, Ui.TextDim, -330f, y, 300f, 40f, TextAnchor.MiddleLeft);
        }

        void BuildSettings(Transform parent, UnityEngine.Events.UnityAction back)
        {
            Ui.PanelAt(parent, 0f, 20f, 860f, 520f, Ui.GreenDim);
            Ui.TextMid(parent, "SETTINGS", Ui.title, 64, Ui.Text, 0f, -200f, 600f, 70f);
            Row(parent, "SENSITIVITY", -120f);
            Text sv = Ui.TextMid(parent, sensitivity.ToString("0.00"), Ui.mono, 24, Ui.Green, 330f, -120f, 120f, 40f, TextAnchor.MiddleRight);
            Ui.MakeSlider(parent, 70f, -120f, 360f, sensitivity, 0.3f, 3f, v => { sensitivity = v; sv.text = v.ToString("0.00"); SaveSettings(); });
            Row(parent, "VOLUME", -50f);
            Text vv = Ui.TextMid(parent, Mathf.RoundToInt(volume * 100f) + "%", Ui.mono, 24, Ui.Green, 330f, -50f, 120f, 40f, TextAnchor.MiddleRight);
            Ui.MakeSlider(parent, 70f, -50f, 360f, volume, 0f, 1f, v => { volume = v; vv.text = Mathf.RoundToInt(v * 100f) + "%"; SaveSettings(); });
            Row(parent, "GRAPHICS", 20f);
            string[] gq = { "LOW", "MEDIUM", "HIGH" };
            Button gb = Ui.TermButton(parent, gq[graphics], 110f, 20f, 300f, 54f, null, 28);
            Text gt = gb.GetComponentInChildren<Text>();
            gb.onClick.AddListener(() => { graphics = (graphics + 1) % 3; gt.text = gq[graphics]; ApplyGraphics(); SaveSettings(); });
            Row(parent, "JOYSTICK", 90f);
            Button jb = Ui.TermButton(parent, floatingJoy ? "FLOATING" : "FIXED", 110f, 90f, 300f, 54f, null, 28);
            Text jt = jb.GetComponentInChildren<Text>();
            jb.onClick.AddListener(() => { floatingJoy = !floatingJoy; jt.text = floatingJoy ? "FLOATING" : "FIXED"; SaveSettings(); });
            Ui.TermButton(parent, "BACK", 0f, 190f, 300f, 62f, back, 32);
        }

        void ShowSettings()
        {
            ClearMenu();
            TerminalBackdrop(0.3f);
            BuildSettings(menu, ShowMainMenu);
        }

        void ShowModes()
        {
            ClearMenu();
            TerminalBackdrop(0.3f);
            Ui.PanelAt(menu, 0f, 30f, 760f, 500f, Ui.GreenDim);
            Ui.TextMid(menu, "CHOOSE YOUR RISK", Ui.title, 64, Ui.Text, 0f, -180f, 700f, 70f);
            Ui.TextMid(menu, "how badly does he want you?", Ui.mono, 22, Ui.TextDim, 0f, -125f, 700f, 34f);
            Color[] acc = { Ui.Green, Ui.Amber, Ui.Red };
            for (int i = 0; i < 3; i++)
            {
                int m = i;
                Ui.TermButton(menu, Modes[i] + "  <size=22><color=#8A9A98>" + ModeSub[i] + "</color></size>", 0f, -40f + i * 88f, 520f, 70f, () => StartGame(m), 34, acc[i]);
            }
            Ui.TermButton(menu, "BACK", 0f, 230f, 260f, 56f, ShowMainMenu, 28);
        }

        public void Pause()
        {
            if (state != S.Play) return;
            state = S.Pause;
            Time.timeScale = 0f;
            hud.gameObject.SetActive(false);
            ShowPauseMenu();
        }

        void ShowPauseMenu()
        {
            ClearMenu();
            MenuBg(0.8f);
            Ui.TextMid(menu, "PAUSED", Ui.title, 90, Ui.Text, 0f, -170f, 600f, 100f);
            Ui.TextMid(menu, "DAY " + day + " OF " + Days, Ui.mono, 24, Ui.Green, 0f, -100f, 600f, 34f);
            Ui.TermButton(menu, "RESUME", 0f, -10f, 360f, 66f, Resume, 34);
            Ui.TermButton(menu, "SETTINGS", 0f, 72f, 360f, 66f, () => { ClearMenu(); MenuBg(0.85f); BuildSettings(menu, ShowPauseMenu); }, 34);
            Ui.TermButton(menu, "MAIN MENU", 0f, 154f, 360f, 66f, QuitToMenu, 34, Ui.Red);
        }

        public void Resume()
        {
            if (state != S.Pause) return;
            ClearMenu();
            Time.timeScale = 1f;
            hud.ResetTouches();
            hud.gameObject.SetActive(true);
            state = S.Play;
        }

        void QuitToMenu()
        {
            Time.timeScale = 1f;
            StopAllCoroutines();
            FreeWorld();
            ShowMainMenu();
        }

        // ============================================================================================== world
        void FreeWorld()
        {
            bgCam.enabled = true;
            if (world != null) Destroy(world);
            world = null;
            level = null;
            player = null;
            trader = null;
            cutCam = null;
            held = "";
            hideRef = null;
            skipBtn.gameObject.SetActive(false);
            CloseOverlayNodes();
        }

        bool BuildWorld()
        {
            FreeWorld();
            world = new GameObject("World");
            var lg = new GameObject("Level");
            lg.transform.SetParent(world.transform, false);
            level = lg.AddComponent<Level>();
            level.sound = sound;
            if (!level.Build()) return false;
            player = Player.Create(world.transform);
            player.hud = hud;
            player.sound = sound;
            player.sensitivity = sensitivity;
            var tg = new GameObject("Trader");
            tg.transform.SetParent(world.transform, false);
            trader = tg.AddComponent<Enemy>();
            trader.level = level;
            trader.player = player;
            trader.sound = sound;
            trader.Setup(mode);
            trader.Build();
            trader.Caught += OnCaught;
            level.Noise += trader.Hear;
            var cg = new GameObject("Cut camera");
            cg.transform.SetParent(world.transform, false);
            cutCam = cg.AddComponent<Camera>();
            cutCam.fieldOfView = 55f;
            cutCam.nearClipPlane = 0.05f;
            cutCam.farClipPlane = 120f;
            cutCam.clearFlags = RenderSettings.skybox != null ? CameraClearFlags.Skybox : CameraClearFlags.SolidColor;
            cutCam.backgroundColor = SkyColor;
            cutCam.allowHDR = false;
            cutCam.enabled = false;
            UseCamera(player.cam);
            return true;
        }

        public void UseCamera(Camera c)
        {
            if (player != null) player.cam.enabled = c == player.cam;
            if (cutCam != null) cutCam.enabled = c == cutCam;
            bgCam.enabled = c == null;
        }

        public void PlaceStart()
        {
            object sp = Json.Get(level.meta, "spawn");
            Vector3 p = Json.V3(sp, "pos");
            player.Teleport(p + new Vector3(0f, 0.05f, 0f));
            player.yaw = Json.F(sp, "yaw");
            player.pitch = 0f;
            player.Apply();
            player.SetCrouch(false);
            player.hidden = false;
            player.frozen = false;
            hud.hidden = false;
            // the trader starts at the patrol point farthest from you (on the other floor if he can)
            List<object> pts = Json.A(level.meta, "patrol");
            Vector3 far = Json.V3(Json.Get(level.meta, "trader_start"));
            float best = Vector3.Distance(far, p) + Mathf.Abs(far.y - p.y) * 3f;
            foreach (object o in pts)
            {
                Vector3 v = Json.V3(o);
                if (Level.RoomAt(level.meta, v) == "garage") continue;
                float d = Vector3.Distance(v, p) + Mathf.Abs(v.y - p.y) * 3f;
                if (d > best)
                {
                    best = d;
                    far = v;
                }
            }
            trader.transform.position = far;
            trader.Freeze(false);
            trader.PickPatrol();
        }

        public void StartGame(int m)
        {
            if (busy) return;
            StartCoroutine(StartGameRoutine(m));
        }

        IEnumerator StartGameRoutine(int m)
        {
            busy = true;
            mode = m;
            day = 1;
            ClearMenu();
            MenuBg();
            Ui.TextMid(menu, "CONNECTING TO MARKET...", Ui.mono, 30, Ui.Green, 0f, 0f, 900f, 50f);
            yield return null;
            yield return null;
            bool ok = BuildWorld();
            busy = false;
            if (!ok)
            {
                ClearMenu();
                MenuBg();
                Ui.TextMid(menu, "GAME FILES MISSING", Ui.mono, 34, Ui.Red, 0f, -40f, 900f, 50f);
                Ui.TermButton(menu, "BACK", 0f, 60f, 300f, 62f, ShowMainMenu, 30);
                yield break;
            }
            sound.StopAll();
            sound.Loop("night", -16f);
            sound.Loop("rain", -20f);
            PlaceStart();
            yield return StartCoroutine(Intro());
            sound.Loop("game_music", -16f);
            BeginDay();
        }

        void BeginDay()
        {
            ClearMenu();
            state = S.Play;
            UseCamera(player.cam);
            player.frozen = false;
            hud.dayText = "DAY " + day;
            hud.ResetTouches();
            hud.gameObject.SetActive(true);
            big.text = "";
            sub.text = "";
            caption.text = "";
            StartCoroutine(DayBanner());
        }

        IEnumerator DayBanner()
        {
            big.color = new Color(1f, 1f, 1f, 0f);
            big.text = "DAY " + day;
            sub.text = day == Days ? "<color=#FA2E3C>LAST CHANCE</color>" : (Days - day + 1) + " DAYS LEFT";
            float t = 0f;
            while (t < 2.6f)
            {
                t += Time.deltaTime;
                float a = t < 0.4f ? t / 0.4f : (t > 2.0f ? 1f - (t - 2.0f) / 0.6f : 1f);
                big.color = new Color(1f, 1f, 1f, Mathf.Clamp01(a) * 0.9f);
                sub.color = new Color(Ui.Text.r, Ui.Text.g, Ui.Text.b, Mathf.Clamp01(a) * 0.8f);
                yield return null;
                if (state != S.Play && state != S.Overlay) break;
            }
            big.text = "";
            sub.text = "";
            big.color = Ui.Red;
            sub.color = Ui.Text;
        }

        // ============================================================================================== play
        void PlayUpdate(float dt)
        {
            string lab = "";
            bool can = false;
            hud.marks.Clear();
            if (player.hidden)
            {
                lab = "Leave";
                can = true;
            }
            else
            {
                Level.Target t = level.FindTarget(player.Head, player.Forward);
                if (t != null)
                {
                    lab = t.label;
                    can = !string.IsNullOrEmpty(lab);
                    if (can) AddMark(t.kind == "item" ? Centre((Level.Item)t.obj) : t.pos, true);
                }
                nearT -= dt;
                if (nearT <= 0f)
                {
                    nearT = 0.12f;
                    NearItems();
                }
                foreach (Level.Item it in near)
                    if (!it.held && (t == null || t.obj != it)) AddMark(Centre(it), false);
            }
            hud.labelText = lab;
            hud.canInteract = can;
            hud.holding = held != "";
            hud.heldText = held != "" && level.items.ContainsKey(held) ? level.items[held].label : "";
            hud.crouched = player.crouched;
            hud.hidden = player.hidden;
            hud.statusText = level.DoorStatus();
        }

        void AddMark(Vector3 wp, bool main)
        {
            Vector3 sp = player.cam.WorldToScreenPoint(wp);
            if (sp.z <= 0f) return;
            float k = Hud.H / Mathf.Max(Screen.height, 1);
            hud.marks.Add(new Hud.Mark { p = new Vector2(sp.x * k, (Screen.height - sp.y) * k), main = main });
        }

        public static Vector3 Centre(Level.Item it)
        {
            Renderer[] rs = it.rends;
            if (rs == null || rs.Length == 0) return it.node.position;
            Bounds b = rs[0].bounds;
            for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            return b.center;
        }

        void NearItems()
        {
            near.Clear();
            Vector3 eye = player.Head;
            foreach (Level.Item it in level.items.Values)
            {
                if (it.held || it.gone || !it.found || !it.node.gameObject.activeInHierarchy) continue;
                if (it.id == "gold_key" && !level.safeOpen) continue;
                if (it.id == "silver_key" && !level.drawerOpen) continue;
                Vector3 c = Centre(it);
                Vector3 to = c - eye;
                float d = to.magnitude;
                if (d > 5f || d < 0.2f || Vector3.Dot(player.Forward, to / d) < 0.35f) continue;
                RaycastHit hit;
                if (!Physics.Linecast(eye, c, out hit, Level.WallMask, QueryTriggerInteraction.Ignore) || Vector3.Distance(hit.point, c) < 0.25f)
                    near.Add(it);
            }
        }

        void Crouch()
        {
            if (state == S.Play && !player.hidden) player.SetCrouch(!player.crouched);
        }

        public void Interact()
        {
            if (state != S.Play) return;
            if (player.hidden)
            {
                LeaveHide();
                return;
            }
            Level.Target t = level.FindTarget(player.Head, player.Forward);
            if (t == null) return;
            switch (t.kind)
            {
                case "item":
                    Pick((Level.Item)t.obj);
                    break;
                case "door":
                {
                    var d = (Level.Door)t.obj;
                    if (d.Locked)
                    {
                        if (held == d.lockId)
                        {
                            level.Unlock(d);
                            hud.ShowMessage("Unlocked");
                            ConsumeHeld();
                        }
                        else
                        {
                            sound.Play3D("door_locked", d.pos, -2f);
                            hud.ShowMessage("Locked. You need the " + ItemLabel(d.lockId));
                        }
                    }
                    else level.ToggleDoor(d);
                    break;
                }
                case "hide":
                    EnterHide((Level.Hide)t.obj);
                    break;
                case "plank":
                    if (held == "hammer") StartCoroutine(PryPlank((Level.Plank)t.obj));
                    else hud.ShowMessage("Nailed shut. You need a claw hammer");
                    break;
                case "padlock":
                {
                    var p = (Level.Padlock)t.obj;
                    if (held == p.key) StartCoroutine(OpenPadlock(p));
                    else
                    {
                        sound.Play3D("door_locked", p.pos, -4f);
                        hud.ShowMessage("Locked. You need the " + ItemLabel(p.key));
                    }
                    break;
                }
                case "keypad":
                    OpenKeypad(true);
                    break;
                case "maindoor":
                    hud.ShowMessage(level.AllBarriersGone() ? "It's open!" : "Planks, two padlocks and a code keep it shut", 3f);
                    break;
                case "plant":
                    SearchPlant((Level.Plant)t.obj);
                    break;
                case "trophy":
                    OpenTrophy();
                    break;
                case "safe":
                    OpenKeypad(false);
                    break;
                case "drawer":
                    UseDrawer();
                    break;
                case "fusebox":
                    if (held == "fuse")
                    {
                        ConsumeHeld();
                        level.InsertFuse();
                        StartCoroutine(PowerOn());
                    }
                    else
                    {
                        sound.Play3D("door_locked", level.fuseboxPos, -6f);
                        hud.ShowMessage("The main fuse has been pulled out. Find a fuse", 3f);
                    }
                    break;
                case "pc":
                    if (!level.power) hud.ShowMessage("No power. Someone pulled the fuse", 3f);
                    else OpenTerminal();
                    break;
            }
        }

        string ItemLabel(string id)
        {
            Level.Item it;
            if (level.items.TryGetValue(id, out it)) return it.label;
            return id.Replace('_', ' ');
        }

        void Pick(Level.Item it)
        {
            if (held != "") Drop(true);
            Transform n = it.node;
            n.gameObject.SetActive(true);
            n.SetParent(player.hold, false);
            n.localPosition = Vector3.zero;
            n.localRotation = Quaternion.Euler(-15f, 115f, 10f);
            n.localScale = it.id == "hammer" ? Vector3.one * 0.9f : Vector3.one * 1.7f;
            it.held = true;
            it.found = true;
            held = it.id;
            level.Look(it, 0.55f);
            sound.Play("pickup", -6f);
        }

        public void Drop(bool quiet)
        {
            if (held == "" || player == null) return;
            Level.Item it = level.items[held];
            Transform n = it.node;
            n.SetParent(level.model, true);
            Vector3 f = player.Forward;
            f.y = 0f;
            f = f.magnitude > 0.01f ? f.normalized : Vector3.forward;
            Vector3 p = player.transform.position + f * 0.7f;
            if (Physics.Linecast(player.Head, new Vector3(p.x, player.Head.y, p.z), Level.WallMask, QueryTriggerInteraction.Ignore))
                p = player.transform.position;
            float fy = level.FloorHeightAt(player.transform.position);
            n.position = new Vector3(p.x, fy + 0.02f, p.z);
            n.rotation = Quaternion.Euler(0f, Random.Range(0f, 360f), 0f);
            n.localScale = Vector3.one;
            it.held = false;
            held = "";
            level.Look(it);
            if (!quiet)
            {
                sound.Play3D("drop", n.position, -2f);
                level.EmitNoise(n.position, 8f);
            }
        }

        void ConsumeHeld()
        {
            if (held == "") return;
            Level.Item it = level.items[held];
            it.node.gameObject.SetActive(false);
            it.held = false;
            it.gone = true;
            held = "";
        }

        void SearchPlant(Level.Plant p)
        {
            p.searched = true;
            sound.Play3D("plank_fall", p.pos, -18f, 1.6f);
            if (!p.hasKey)
            {
                hud.ShowMessage("Just soil and leaves");
                return;
            }
            Level.Item it;
            if (!level.items.TryGetValue("drawer_key", out it)) return;
            it.found = true;
            Pick(it);
            hud.ShowMessage("A small key was buried in the soil!", 3f);
        }

        void UseDrawer()
        {
            if (!level.drawerUnlocked)
            {
                if (held == "drawer_key")
                {
                    ConsumeHeld();
                    level.drawerUnlocked = true;
                    sound.Play3D("unlock", level.drawerPos, -2f);
                    level.SetDrawer(true);
                    hud.ShowMessage("The drawer is unlocked");
                }
                else
                {
                    sound.Play3D("door_locked", level.drawerPos, -6f);
                    hud.ShowMessage("Locked. There's a tiny keyhole");
                }
                return;
            }
            level.SetDrawer(!level.drawerOpen);
        }

        IEnumerator PowerOn()
        {
            yield return new WaitForSeconds(0.5f);
            level.SetPower(true);
            sound.Play3D("pc_boot", level.pcPos, -2f);
            level.EmitNoise(level.fuseboxPos, 9f);
            hud.ShowMessage("Power is back. Upstairs, his monitors light up", 3.5f);
        }

        IEnumerator PryPlank(Level.Plank p)
        {
            if (p.gone) yield break;
            p.gone = true;
            level.planksLeft--;
            sound.Play3D("plank_crack", p.pos, 2f);
            level.EmitNoise(p.pos, 12f);
            Transform n = p.node;
            Vector3 from = n.position;
            Vector3 to = new Vector3(from.x + Random.Range(-0.25f, 0.25f), level.FloorHeightAt(from) + 0.02f, from.z + 0.5f);
            Quaternion r0 = n.rotation;
            Quaternion r1 = Quaternion.Euler(0f, Random.Range(-25f, 25f), 90f) * Quaternion.Euler(90f, 0f, 0f);
            float t = 0f;
            while (t < 0.55f && n != null)
            {
                t += Time.deltaTime;
                float k = Mathf.Clamp01(t / 0.55f);
                n.position = Vector3.Lerp(from, to, k * k) + new Vector3(0f, Mathf.Sin(k * Mathf.PI) * 0.12f, 0f);
                n.rotation = Quaternion.Slerp(r0, r1, k);
                yield return null;
            }
            sound.Play3D("plank_fall", p.pos, 0f);
            hud.ShowMessage(level.planksLeft == 0 ? "The planks are off" : level.planksLeft + (level.planksLeft == 1 ? " plank left" : " planks left"));
            CheckEscape();
        }

        IEnumerator OpenPadlock(Level.Padlock p)
        {
            ConsumeHeld();
            p.gone = true;
            sound.Play3D("padlock", p.pos, 0f);
            level.EmitNoise(p.pos, 7f);
            Transform n = p.node;
            Vector3 from = n.position;
            float floorY = level.FloorHeightAt(from);
            float t = 0f, vy = 0f;
            yield return new WaitForSeconds(0.3f);
            while (n != null && n.position.y > floorY + 0.02f && t < 2f)
            {
                t += Time.deltaTime;
                vy -= 9.8f * Time.deltaTime;
                n.position += new Vector3(0f, vy * Time.deltaTime, 0.25f * Time.deltaTime);
                n.Rotate(200f * Time.deltaTime, 0f, 90f * Time.deltaTime);
                yield return null;
            }
            if (n != null)
            {
                sound.Play3D("drop", n.position, -6f, 1.3f);
                n.position = new Vector3(n.position.x, floorY + 0.02f, n.position.z);
            }
            hud.ShowMessage(p.label + " opened");
            CheckEscape();
        }

        void CheckEscape()
        {
            if (state == S.Play && level.AllBarriersGone()) StartCoroutine(Escape());
        }

        void EnterHide(Level.Hide h)
        {
            hideRef = h;
            player.SetCrouch(false);
            player.hidden = true;
            player.Teleport(h.pos + h.front * 0.02f + new Vector3(0f, 0.05f, 0f));
            player.yaw = Mathf.Atan2(h.front.x, h.front.z) * Mathf.Rad2Deg;
            player.pitch = -4f;
            player.Apply();
            sound.Play3D("door_close", h.pos, -16f, 1.2f);
        }

        void LeaveHide()
        {
            if (hideRef == null)
            {
                player.hidden = false;
                return;
            }
            Level.Hide h = hideRef;
            player.Teleport(h.pos + h.front * (h.depth * 0.5f + 0.55f) + new Vector3(0f, 0.05f, 0f));
            player.hidden = false;
            hideRef = null;
            sound.Play3D("door_open", h.pos, -16f, 1.2f);
        }

        // ============================================================================================== overlays
        void CloseOverlayNodes()
        {
            if (overlay == null) return;
            for (int i = overlay.childCount - 1; i >= 0; i--) Destroy(overlay.GetChild(i).gameObject);
            overlay.DetachChildren();
        }

        void BeginOverlay()
        {
            beforeOverlay = state;
            state = S.Overlay;
            hud.gameObject.SetActive(false);
            CloseOverlayNodes();
            Image dim = Ui.Rect(overlay, new Color(0f, 0f, 0f, 0.6f), "Dim");
            dim.raycastTarget = true;
        }

        public void CloseOverlay()
        {
            if (state != S.Overlay) return;
            CloseOverlayNodes();
            state = S.Play;
            hud.ResetTouches();
            hud.gameObject.SetActive(true);
        }

        /// <summary>The code keypad: six digits for the main door, four for the safe.</summary>
        void OpenKeypad(bool door)
        {
            BeginOverlay();
            int digits = door ? 6 : 4;
            string code = door ? level.doorCode : level.safeCode;
            string entered = "";
            RectTransform pnl = Ui.PanelAt(overlay, 0f, 10f, 430f, 600f, door ? Ui.GreenDim : new Color(Ui.Amber.r, Ui.Amber.g, Ui.Amber.b, 0.4f), "Keypad");
            Ui.TextMid(pnl, door ? "MAIN DOOR LOCK" : "SAFE", Ui.mono, 22, Ui.TextDim, 0f, -262f, 400f, 34f);
            RectTransform disp = Ui.Node(pnl, "Display");
            Ui.Mid(disp, 0f, -205f, 360f, 70f);
            var di = disp.gameObject.AddComponent<Image>();
            di.color = new Color(0.01f, 0.03f, 0.02f, 1f);
            Text dt = Ui.Label(disp, Ui.mono, 46, Ui.Green, "Digits");
            System.Action show = () =>
            {
                string s = "";
                for (int i = 0; i < digits; i++) s += i < entered.Length ? entered[i].ToString() : "_";
                dt.text = string.Join(" ", s.ToCharArray());
                dt.color = Ui.Green;
            };
            show();
            string[] keys = { "1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "OK" };
            for (int k = 0; k < keys.Length; k++)
            {
                string key = keys[k];
                float x = (k % 3 - 1) * 118f, y = -110f + (k / 3) * 96f;
                Color ac = key == "OK" ? Ui.Green : (key == "C" ? Ui.Red : new Color(0.5f, 0.6f, 0.6f, 1f));
                Ui.TermButton(pnl, key, x, y, 104f, 82f, () =>
                {
                    if (key == "C")
                    {
                        entered = "";
                        sound.Play("keypad_beep", -10f, 0.8f);
                    }
                    else if (key == "OK")
                    {
                        if (entered == code)
                        {
                            sound.Play("keypad_ok", -4f);
                            CloseOverlay();
                            if (door)
                            {
                                level.SetKeypadSolved();
                                hud.ShowMessage("Code accepted. The lock clicks open");
                                level.EmitNoise(level.keypadPos, 6f);
                                CheckEscape();
                            }
                            else
                            {
                                level.OpenSafe();
                                hud.ShowMessage("The safe swings open");
                            }
                            return;
                        }
                        sound.Play("keypad_bad", -4f);
                        entered = "";
                        dt.text = "DENIED";
                        dt.color = Ui.Red;
                        if (door) level.EmitNoise(level.keypadPos, 11f);   // the alarm beep carries
                        return;
                    }
                    else if (entered.Length < digits)
                    {
                        entered += key;
                        sound.Play("keypad_beep", -10f, 1f + entered.Length * 0.03f);
                    }
                    show();
                }, 36, ac);
            }
            Ui.TermButton(overlay, "X", 0f, 0f, 70f, 60f, CloseOverlay, 32, Ui.Red).GetComponent<RectTransform>().anchoredPosition = new Vector2(250f, 270f);
        }

        void OpenTrophy()
        {
            BeginOverlay();
            RectTransform pnl = Ui.PanelAt(overlay, 0f, 0f, 700f, 420f, new Color(Ui.Amber.r, Ui.Amber.g, Ui.Amber.b, 0.5f), "Trophy");
            Ui.TextMid(pnl, "TOP TRADER 2025", Ui.title, 70, Ui.Amber, 0f, -120f, 640f, 80f);
            Ui.TextMid(pnl, "37 WINNING TRADES IN A ROW", Ui.mono, 24, Ui.Text, 0f, -55f, 640f, 34f);
            Ui.TextMid(pnl, "Engraved under the base:", Ui.ui, 26, Ui.TextDim, 0f, 15f, 640f, 34f);
            Ui.TextMid(pnl, "\"MY LUCKY NUMBER  " + string.Join(" ", level.safeCode.ToCharArray()) + "\"", Ui.mono, 36, Ui.Text, 0f, 65f, 640f, 50f);
            Ui.TermButton(pnl, "CLOSE", 0f, 150f, 220f, 56f, CloseOverlay, 28);
        }

        /// <summary>The trader's PC: his account, his losing trades, and the note with the door code.</summary>
        void OpenTerminal()
        {
            BeginOverlay();
            sound.Play("ui_click", -6f);
            RectTransform pnl = Ui.PanelAt(overlay, 0f, 0f, 1180f, 640f, Ui.GreenDim, "Terminal");
            RectTransform bar = Ui.Node(pnl, "Bar");
            bar.anchorMin = new Vector2(0f, 1f);
            bar.anchorMax = new Vector2(1f, 1f);
            bar.pivot = new Vector2(0.5f, 1f);
            bar.sizeDelta = new Vector2(-4f, 44f);
            bar.anchoredPosition = new Vector2(0f, -2f);
            bar.gameObject.AddComponent<Image>().color = new Color(0.06f, 0.09f, 0.1f, 1f);
            Text bt = Ui.Label(bar, Ui.mono, 22, Ui.Text, "Title");
            bt.alignment = TextAnchor.MiddleLeft;
            bt.rectTransform.offsetMin = new Vector2(16f, 0f);
            bt.text = "OPTION-X PRO  //  TRDR-0991  //  <color=#FA2E3C>ACCOUNT FROZEN</color>";
            Ui.TextMid(pnl, "BALANCE", Ui.mono, 20, Ui.TextDim, -390f, -235f, 300f, 30f, TextAnchor.MiddleLeft);
            Ui.TextMid(pnl, "-$1,284,550.00", Ui.mono, 50, Ui.Red, -330f, -190f, 420f, 60f, TextAnchor.MiddleLeft);
            // chart
            RectTransform ch = Ui.Node(pnl, "Chart");
            Ui.Mid(ch, -250f, 0f, 620f, 300f);
            ch.gameObject.AddComponent<Image>().color = new Color(0f, 0.01f, 0.02f, 1f);
            RectTransform chi = Ui.Node(ch, "Candles");
            Ui.Full(chi);
            var mc = chi.gameObject.AddComponent<MenuChart>();
            mc.alpha = 0.95f;
            mc.speed = 1.6f;
            mc.crash = 0.62f;
            mc.count = 48;
            // trade log
            Ui.TextMid(pnl, "LAST TRADES", Ui.mono, 20, Ui.TextDim, 290f, -235f, 520f, 30f, TextAnchor.MiddleLeft);
            string[] assets = { "EUR/USD", "BTC/USD", "GOLD", "GBP/JPY", "ETH/USD", "USD/INR", "OIL", "NAS100" };
            var log = new System.Text.StringBuilder();
            var rng = new System.Random(level.doorCode.GetHashCode());
            for (int i = 0; i < 9; i++)
            {
                bool win = rng.NextDouble() < 0.12;
                string dir = rng.NextDouble() < 0.5 ? "CALL" : "PUT ";
                int amt = (rng.Next(5, 99)) * 1000;
                log.Append(string.Format("{0:00}:{1:00}  {2,-8} {3}  {4}\n", 23 - i / 3, rng.Next(0, 60), assets[rng.Next(assets.Length)], dir,
                                         win ? "<color=#22F07F>+$" + (amt * 0.8f).ToString("#,##0") + "</color>" : "<color=#FA2E3C>-$" + amt.ToString("#,##0") + "</color>"));
            }
            Ui.TextMid(pnl, log.ToString(), Ui.mono, 22, Ui.Text, 290f, -40f, 520f, 330f, TextAnchor.UpperLeft);
            // the sticky note
            RectTransform note = Ui.Node(pnl, "Note");
            Ui.Mid(note, 300f, 205f, 360f, 120f);
            note.localRotation = Quaternion.Euler(0f, 0f, 3f);
            note.gameObject.AddComponent<Image>().color = new Color(0.98f, 0.86f, 0.3f, 1f);
            Text nt = Ui.Label(note, Ui.mono, 28, new Color(0.15f, 0.1f, 0.02f, 1f), "Note text");
            nt.text = "front door:\n" + string.Join(" ", level.doorCode.ToCharArray());
            Ui.TermButton(pnl, "LOG OFF", -250f, 230f, 260f, 58f, CloseOverlay, 28);
        }

        // ============================================================================================== cut scenes
        void MakeSkipButton()
        {
            Button b = Ui.TermButton(canvas.transform, "SKIP >>", 0f, 0f, 190f, 60f, OnSkip, 28, Ui.Amber);
            RectTransform rt = b.GetComponent<RectTransform>();
            rt.anchorMin = new Vector2(1f, 1f);
            rt.anchorMax = new Vector2(1f, 1f);
            rt.pivot = new Vector2(1f, 1f);
            rt.anchoredPosition = new Vector2(-30f, -24f);
            skipBtn = b;
            skipBtn.gameObject.SetActive(false);
        }

        public void OnSkip()
        {
            skip = true;
        }

        static void SetAlpha(Graphic g, float a)
        {
            Color c = g.color;
            c.a = a;
            g.color = c;
        }

        IEnumerator Wait(float t)
        {
            float left = t;
            while (left > 0f && !skip)
            {
                left -= Time.deltaTime;
                yield return null;
            }
        }

        IEnumerator FadeTo(float a, float t)
        {
            float from = fade.color.a, k = 0f;
            while (k < 1f)
            {
                k += Time.unscaledDeltaTime / Mathf.Max(t, 0.01f);
                SetAlpha(fade, Mathf.Lerp(from, a, Mathf.Clamp01(k)));
                yield return null;
            }
        }

        IEnumerator Shot(Vector3 from, Vector3 to, Vector3 lookA, Vector3 lookB, float dur, string text)
        {
            caption.text = text;
            UseCamera(cutCam);
            float k = 0f;
            while (k < 1f && !skip)
            {
                k += Time.deltaTime / dur;
                float e = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(k));
                cutCam.transform.position = Vector3.Lerp(from, to, e);
                cutCam.transform.rotation = Quaternion.LookRotation(Vector3.Lerp(lookA, lookB, e) - cutCam.transform.position);
                yield return null;
            }
        }

        IEnumerator Intro()
        {
            state = S.Cut;
            skip = false;
            skipBtn.gameObject.SetActive(true);
            trader.Freeze(true);
            SetAlpha(fade, 1f);
            StartCoroutine(FadeTo(0f, 1.2f));
            yield return Shot(new Vector3(9.0f, 1.8f, -9.6f), new Vector3(8.6f, 1.75f, -6.8f), new Vector3(8.5f, 3.2f, 0f), new Vector3(8.0f, 3.4f, 0f), 6f,
                              "You came to his house to learn binary trading from the man who never loses.");
            if (!skip)
                yield return Shot(new Vector3(9.9f, 4.95f, 0.8f), new Vector3(10.6f, 4.9f, 1.4f), new Vector3(13.5f, 4.2f, 6.0f), new Vector3(13.5f, 4.3f, 6.0f), 5.5f,
                                  "Tonight he lost everything on a single trade... and he blames you.");
            if (!skip)
                yield return Shot(new Vector3(7.4f, 1.7f, 3.4f), new Vector3(7.2f, 1.6f, 1.6f), new Vector3(7.0f, 1.2f, 0f), new Vector3(7.0f, 1.25f, 0f), 6f,
                                  "Three planks, two padlocks and a code lock the front door. Five days. Get out.");
            caption.text = "";
            skipBtn.gameObject.SetActive(false);
            yield return FadeTo(1f, 0.4f);
            UseCamera(player.cam);
            trader.Freeze(false);
            trader.PickPatrol();
            StartCoroutine(FadeTo(0f, 0.8f));
        }

        void OnCaught()
        {
            if (state != S.Play && state != S.Overlay) return;
            StartCoroutine(CaughtRoutine());
        }

        IEnumerator CaughtRoutine()
        {
            CloseOverlayNodes();
            state = S.Cut;
            hud.gameObject.SetActive(false);
            player.frozen = true;
            if (player.hidden) LeaveHide();
            if (held != "") Drop(true);
            player.SetCrouch(false);
            // turn to face him: his head fills the view
            Vector3 head = trader.HeadPos;
            Quaternion r0 = player.cam.transform.rotation;
            float t = 0f;
            sound.Play("jumpscare", 0f);
            while (t < 0.35f)
            {
                t += Time.deltaTime;
                player.cam.transform.rotation = Quaternion.Slerp(r0, Quaternion.LookRotation(head - player.cam.transform.position), t / 0.35f);
                yield return null;
            }
            for (int hit = 0; hit < 2; hit++)
            {
                yield return new WaitForSeconds(0.32f);
                sound.Play("punch", 2f, 1f + hit * 0.08f);
                SetAlpha(flash, 0.75f);
                Vector3 basePos = player.cam.transform.localPosition;
                float s = 0f;
                while (s < 0.25f)
                {
                    s += Time.deltaTime;
                    player.cam.transform.localPosition = basePos + Random.insideUnitSphere * 0.06f * (1f - s / 0.25f);
                    yield return null;
                }
                player.cam.transform.localPosition = basePos;
            }
            yield return FadeTo(1f, 0.5f);
            trader.Freeze(true);
            if (day >= Days)
            {
                yield return GameOver();
                yield break;
            }
            day++;
            big.text = "DAY " + day;
            big.color = Ui.Red;
            sub.text = "HE CAUGHT YOU";
            yield return new WaitForSeconds(2.2f);
            big.text = "";
            sub.text = "";
            PlaceStart();
            SetAlpha(fade, 1f);
            StartCoroutine(FadeTo(0f, 1f));
            BeginDay();
        }

        IEnumerator GameOver()
        {
            state = S.Cut;
            sound.StopAll();
            sound.Play("spotted", -2f, 0.8f);
            ClearMenu();
            MenuBg(1f);
            Text t = Ui.TextMid(menu, "LIQUIDATED", Ui.title, 170, Ui.Red, 0f, -60f, 1200f, 190f);
            t.gameObject.AddComponent<Glitch>().amount = 6f;
            Ui.TextMid(menu, "five days gone. the trader closed your position.", Ui.mono, 26, Ui.TextDim, 0f, 50f, 1100f, 40f);
            SetAlpha(fade, 0f);
            yield return new WaitForSeconds(1.5f);
            Ui.TermButton(menu, "MAIN MENU", 0f, 160f, 340f, 66f, QuitToMenu, 34);
        }

        IEnumerator Escape()
        {
            state = S.Cut;
            hud.gameObject.SetActive(false);
            player.frozen = true;
            trader.Freeze(true);
            if (held != "") Drop(true);
            yield return new WaitForSeconds(0.6f);
            level.OpenMain();
            sound.Play("keypad_ok", -6f);
            Vector3 a = new Vector3(7.0f, 1.6f, 2.6f), b = new Vector3(7.0f, 1.6f, -2.8f);
            UseCamera(cutCam);
            cutCam.transform.position = a;
            cutCam.transform.rotation = Quaternion.LookRotation(Vector3.back);
            yield return new WaitForSeconds(1.2f);
            float k = 0f;
            while (k < 1f)
            {
                k += Time.deltaTime / 3.2f;
                cutCam.transform.position = Vector3.Lerp(a, b, Mathf.SmoothStep(0f, 1f, k));
                yield return null;
            }
            yield return FadeTo(1f, 1.0f);
            sound.StopAll();
            sound.Loop("menu_music", -10f);
            ClearMenu();
            TerminalBackdrop(0.35f);
            Ui.TextMid(menu, "YOU ESCAPED", Ui.title, 150, Ui.Green, 0f, -90f, 1200f, 170f);
            Ui.TextMid(menu, "day " + day + "  //  position closed in profit", Ui.mono, 26, Ui.Text, 0f, 10f, 1100f, 40f);
            Ui.TextMid(menu, "the market never sleeps. neither will he.", Ui.mono, 22, Ui.TextDim, 0f, 55f, 1100f, 36f);
            SetAlpha(fade, 0f);
            UseCamera(null);
            yield return new WaitForSeconds(1.2f);
            Ui.TermButton(menu, "MAIN MENU", 0f, 170f, 340f, 66f, QuitToMenu, 34);
        }

        // ============================================================================================== for the emulator check
        public void TestShowSettings() { ShowSettings(); }
        public void TestShowModes() { ShowModes(); }
        public void TestBeginDay() { skip = true; }
        public void TestOpenTerminal() { if (state == S.Play) OpenTerminal(); }
        public void TestOpenKeypad() { if (state == S.Play) OpenKeypad(true); }
        public void TestPower() { if (level != null && !level.power) { level.InsertFuse(); level.SetPower(true); } }
    }
}
