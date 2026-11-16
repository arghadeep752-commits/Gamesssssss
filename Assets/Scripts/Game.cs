using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Moulika
{
    /// <summary>
    /// MOULIKA - The Indian Horror Game.  MXYAN GAMES OFFICIAL.
    /// Menu -> mode -> intro cutscene -> three days to escape the school -> caught / game over / escape cutscenes.
    /// Port of game/scripts/main.gd. Godot coordinates written in the code are converted with G(x, y, z).
    /// </summary>
    public class Game : MonoBehaviour
    {
        public enum S { Menu, Play, Cut, Pause }

        public static readonly Color SkyColor = new Color(0.02f, 0.025f, 0.04f).gamma;   // the fog colour (linear) as a clear colour
        static readonly string[] Modes = { "EASY", "NORMAL", "HARD" };

        public S state = S.Menu;
        public int mode = 1, day = 1;
        public float sensitivity = 1f;
        public bool floatingJoy = true;
        public string held = "";
        public bool skip, busy;
        public Level level;
        public Player player;
        public Enemy moulika;
        public GameAudio sound;
        public Hud hud;
        public Camera cutCam;

        Level.Hide hideRef;
        float ambT = 18f, nearT;
        readonly List<Level.Item> near = new List<Level.Item>();
        GameObject world;
        Camera bgCam;
        Transform listener;
        Canvas canvas;
        RectTransform menu;
        CanvasGroup menuGroup;
        Image fade, flash;
        Text caption, big, sub;
        Button skipBtn;
        Font fName, fUi;

        public static Vector3 G(float x, float y, float z) { return new Vector3(x, y, -z); }

        /// <summary>Godot Euler rotation (degrees, YXZ order) as a Unity rotation.</summary>
        public static Quaternion GQ(float x, float y, float z)
        {
            Quaternion q = Quaternion.Euler(x, y, z);
            return new Quaternion(-q.x, -q.y, q.z, q.w);
        }

        // ============================================================================================== start
        void Start()
        {
            Application.targetFrameRate = 60;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            Input.multiTouchEnabled = true;
            Shader.SetGlobalFloat("_MFogDensity", 0.018f);
            Shader.SetGlobalVector("_MFogColor", new Vector4(0.02f, 0.025f, 0.04f, 1f));

            fUi = Resources.Load<Font>("Fonts/dk_midnight_chalker") ?? Resources.Load<Font>("Fonts/Oswald");
            fName = Resources.Load<Font>("Fonts/baby_doll") ?? Resources.Load<Font>("Fonts/Creepster-Regular") ?? fUi;
            Ui.chalk = fUi;
            Ui.title = fName;
            Ui.chalkScaled = fUi != null && fUi.name.ToLowerInvariant().Contains("chalker");
            sensitivity = PlayerPrefs.GetFloat("sensitivity", 1f);
            floatingJoy = PlayerPrefs.GetInt("floating_joystick", 1) == 1;

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
            hud = Hud.Create(canvas.transform, fUi);
            hud.ApplyFont(fUi, Ui.chalkScaled ? Ui.ChalkScale : 1f);
            hud.floating = floatingJoy;
            hud.gameObject.SetActive(false);
            hud.onInteract = Interact;
            hud.onDrop = () => Drop(false);
            hud.onCrouch = Crouch;
            hud.onPause = Pause;
            flash = Ui.Rect(canvas.transform, new Color(0.6f, 0f, 0f, 0f), "Flash");
            fade = Ui.Rect(canvas.transform, new Color(0f, 0f, 0f, 0f), "Fade");
            caption = Ui.Label(canvas.transform, fUi, 30, new Color(0.92f, 0.9f, 0.85f), "Caption");
            RectTransform cr = caption.rectTransform;
            cr.anchorMin = new Vector2(0f, 0f);
            cr.anchorMax = new Vector2(1f, 0f);
            cr.offsetMin = new Vector2(80f, 60f);
            cr.offsetMax = new Vector2(-80f, 150f);
            big = Ui.Label(canvas.transform, fUi, 110, new Color(0.75f, 0.04f, 0.03f), "Big");
            big.horizontalOverflow = HorizontalWrapMode.Overflow;
            sub = Ui.Label(canvas.transform, fUi, 30, new Color(0.85f, 0.85f, 0.85f), "Sub");
            SubOffset(190f);
            menu = Ui.Node(canvas.transform, "Menu");
            Ui.Full(menu);
            menuGroup = menu.gameObject.AddComponent<CanvasGroup>();
            MakeSkipButton();
            ShowMainMenu();
#if MOULIKA_AUTOTEST
            gameObject.AddComponent<AutoTest>();
#endif
        }

        void SubOffset(float top)
        {
            sub.rectTransform.offsetMin = Vector2.zero;
            sub.rectTransform.offsetMax = new Vector2(0f, -top);
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape)) Back();
            if (flash.color.a > 0f)
            {
                Color c = flash.color;
                c.a = Mathf.Max(0f, c.a - Time.unscaledDeltaTime * 1.5f);
                flash.color = c;
            }
            if (state == S.Play && player != null) PlayUpdate(Time.deltaTime);
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
                case S.Menu: if (menu.childCount > 0 && !busy) ShowMainMenu(); break;
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
            Image bg = Ui.Rect(menu, new Color(0f, 0f, 0f, alpha), "Background");
            bg.raycastTarget = true;     // the menu swallows touches
        }

        IEnumerator FadeInMenu()
        {
            menuGroup.alpha = 0f;
            float t = 0f;
            while (t < 0.7f)
            {
                t += Time.unscaledDeltaTime;
                menuGroup.alpha = Mathf.Clamp01(t / 0.7f);
                yield return null;
            }
            menuGroup.alpha = 1f;
        }

        public void ShowMainMenu()
        {
            state = S.Menu;
            Time.timeScale = 1f;
            hud.gameObject.SetActive(false);
            big.text = "";
            sub.text = "";
            caption.text = "";
            SetAlpha(fade, 0f);
            ClearMenu();
            MenuBg();
            // the game's name with a soft red glow
            for (int k = 0; k < 12; k++)
            {
                float a = k * Mathf.PI * 2f / 12f, r = k % 2 == 0 ? 9f : 5f;
                Text g = Ui.TextAt(menu, "MOULIKA", fName, 165, new Color(0.55f, 0f, 0f, 0.07f), 0.12f);
                g.rectTransform.anchoredPosition = new Vector2(Mathf.Cos(a) * r, Mathf.Sin(a) * r);
            }
            Ui.TextAt(menu, "MOULIKA", fName, 165, new Color(0.70f, 0.02f, 0.02f), 0.12f);
            Ui.TextAt(menu, "THE INDIAN HORROR GAME", fName, 30, new Color(0.74f, 0.74f, 0.74f), 0.435f, 7f);
            Ui.Divider(menu, 0.52f, 280f);
            Ui.Button(menu, "PLAY", 0.55f, ShowModes, 50);
            Ui.Button(menu, "SETTINGS", 0.69f, ShowSettings, 40);
            Ui.TextAt(menu, "MXYAN GAMES OFFICIAL", fUi, 22, new Color(0.55f, 0.55f, 0.55f), 0.915f, 4f);
            StartCoroutine(FadeInMenu());
            sound.StopAll();
            sound.Loop("menu_music", -8f);
        }

        void SensitivitySlider(float y)
        {
            Ui.TextAt(menu, "SENSITIVITY", fUi, 34, new Color(0.85f, 0.85f, 0.85f), y);
            Text val = null;
            Ui.Slider(menu, y + 0.1f, sensitivity, 0.3f, 2.5f, v =>
            {
                v = Mathf.Round(v / 0.05f) * 0.05f;
                sensitivity = v;
                if (val != null) val.text = v.ToString("0.00");
                if (player != null) player.sensitivity = v;
                SaveSettings();
            });
            val = Ui.TextAt(menu, sensitivity.ToString("0.00"), fUi, 26, new Color(0.6f, 0.6f, 0.6f), y + 0.2f);
        }

        void SaveSettings()
        {
            PlayerPrefs.SetFloat("sensitivity", sensitivity);
            PlayerPrefs.SetInt("floating_joystick", floatingJoy ? 1 : 0);
            PlayerPrefs.Save();
        }

        string JoyLabel() { return "FLOATING JOYSTICK: " + (floatingJoy ? "ON" : "OFF"); }

        void JoyToggle(float y)
        {
            // on: the joystick appears under your thumb; off: it stays fixed in the corner
            Button b = Ui.Button(menu, JoyLabel(), y, null, 32, 340f);
            Text t = b.GetComponentInChildren<Text>();
            b.onClick.AddListener(() =>
            {
                floatingJoy = !floatingJoy;
                t.text = JoyLabel();
                hud.floating = floatingJoy;
                SaveSettings();
            });
        }

        void ShowSettings()
        {
            ClearMenu();
            MenuBg();
            Ui.TextAt(menu, "SETTINGS", fUi, 50, new Color(0.9f, 0.9f, 0.9f), 0.12f, 3f);
            Ui.Divider(menu, 0.255f, 220f);
            SensitivitySlider(0.3f);
            JoyToggle(0.6f);
            Ui.Button(menu, "BACK", 0.78f, ShowMainMenu, 38);
            StartCoroutine(FadeInMenu());
        }

        void ShowModes()
        {
            ClearMenu();
            MenuBg();
            Ui.TextAt(menu, "SELECT MODE", fUi, 50, new Color(0.9f, 0.9f, 0.9f), 0.1f, 3f);
            Ui.Divider(menu, 0.235f, 220f);
            for (int i = 0; i < 3; i++)
            {
                int m = i;
                Ui.Button(menu, Modes[i], 0.3f + i * 0.13f, () => StartGame(m), 46);
            }
            Ui.Button(menu, "BACK", 0.8f, ShowMainMenu, 34);
            StartCoroutine(FadeInMenu());
        }

        public void Pause()
        {
            if (state != S.Play) return;
            state = S.Pause;
            Time.timeScale = 0f;
            hud.gameObject.SetActive(false);
            ClearMenu();
            MenuBg(0.85f);
            Ui.TextAt(menu, "PAUSED", fUi, 46, new Color(0.9f, 0.9f, 0.9f), 0.08f, 3f);
            Ui.Divider(menu, 0.2f, 200f);
            Ui.Button(menu, "RESUME", 0.24f, Resume, 42);
            SensitivitySlider(0.38f);
            JoyToggle(0.66f);
            Ui.Button(menu, "MAIN MENU", 0.82f, QuitToMenu, 36);
        }

        public void Resume()
        {
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
            moulika = null;
            cutCam = null;
            held = "";
            hideRef = null;
            skipBtn.gameObject.SetActive(false);
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
            var mg = new GameObject("Moulika");
            mg.transform.SetParent(world.transform, false);
            moulika = mg.AddComponent<Enemy>();
            moulika.level = level;
            moulika.player = player;
            moulika.sound = sound;
            moulika.Setup(mode);
            moulika.Build();
            moulika.Caught += OnCaught;
            level.Noise += moulika.Hear;
            var cg = new GameObject("Cut camera");
            cg.transform.SetParent(world.transform, false);
            cutCam = cg.AddComponent<Camera>();
            cutCam.fieldOfView = 55f;
            cutCam.nearClipPlane = 0.05f;
            cutCam.farClipPlane = 150f;
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
            Vector3 sp = Json.GV(Json.Get(Json.Get(level.meta, "spawn"), "pos"));
            player.Teleport(new Vector3(sp.x, 0.05f, sp.z));
            player.Face(player.transform.position + new Vector3(-5f, 0f, 0f));
            player.SetCrouch(false);
            player.hidden = false;
            player.frozen = false;
            List<object> pts = Json.A(level.meta, "patrol");
            Vector3 far = Json.GV(pts[0]);
            float best = 0f;
            foreach (object p in pts)
            {
                Vector3 v = Json.GV(p);
                v.y = 0f;
                float d = Vector3.Distance(v, player.transform.position);
                if (d > best)
                {
                    best = d;
                    far = v;
                }
            }
            far.y = 0f;
            moulika.transform.position = far;
            moulika.Freeze(false);
            moulika.PickPatrol();
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
            Ui.TextAt(menu, "LOADING...", fUi, 40, new Color(0.8f, 0.8f, 0.8f), 0.45f);
            yield return null;
            yield return null;
            bool ok = BuildWorld();
            busy = false;
            if (!ok)
            {
                ClearMenu();
                MenuBg();
                Ui.TextAt(menu, "GAME FILES MISSING", fUi, 40, new Color(0.8f, 0.2f, 0.2f), 0.4f);
                Ui.Button(menu, "BACK", 0.6f, ShowMainMenu);
                yield break;
            }
            sound.StopAll();
            sound.Loop("night", -13f);
            sound.Loop("wind", -24f);
            sound.Loop("music_raga", -9f);         // the intro cutscene plays over a real raga recording
            PlaceStart();
            yield return StartCoroutine(Intro());
            sound.Stop("music_raga");
            // low horror suspense music under the night ambience while playing (the tanpura drone if it is missing)
            sound.Loop(sound.Has("game_music") ? "game_music" : "drone", -17f);
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
                    can = true;
                    AddMark(UsePoint(t), true);
                }
                // faint circles on items lying in view nearby
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
            hud.crouched = player.crouched;
            if (hideRef != null)
            {
                hideRef.t = Mathf.MoveTowards(hideRef.t, hideRef.target, dt * 3f);
                level.SetHideDoors(hideRef, hideRef.t);
            }
            sound.Loop("heartbeat", moulika.state == Enemy.State.Chase ? -4f : -60f);
            ambT -= dt;
            if (ambT <= 0f)
            {
                ambT = Random.Range(22f, 45f);
                string pick = new[] { "dog_howl", "owl", "dog_howl", "laugh" }[Random.Range(0, 4)];
                Vector3 off = new Vector3(Random.Range(-1f, 1f), 0f, Random.Range(-1f, 1f)).normalized * Random.Range(12f, 22f);
                sound.Play3D(pick, player.transform.position + off + new Vector3(0f, 3f, 0f), pick != "laugh" ? -10f : -14f);
            }
        }

        void AddMark(Vector3 wp, bool main)
        {
            Vector3 sp = player.cam.WorldToScreenPoint(wp);
            if (sp.z <= 0f) return;
            float k = Hud.H / Mathf.Max(Screen.height, 1);
            hud.marks.Add(new Hud.Mark { p = new Vector2(sp.x * k, (Screen.height - sp.y) * k), main = main });
        }

        /// <summary>Middle of an item's meshes, for the highlight circle.</summary>
        public static Vector3 Centre(Level.Item it)
        {
            Renderer[] rs = it.rends;
            if (rs == null || rs.Length == 0) return it.node.position;
            Bounds b = rs[0].bounds;
            for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            return b.center;
        }

        Vector3 UsePoint(Level.Target t)
        {
            return t.kind == "item" ? Centre((Level.Item)t.obj) : t.pos;
        }

        void NearItems()
        {
            near.Clear();
            Vector3 eye = player.Head;
            foreach (Level.Item it in level.items.Values)
            {
                if (it.held || !it.node.gameObject.activeInHierarchy) continue;
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
                            d.lockId = null;
                            sound.Play3D("unlock", d.pos, 0f);
                            hud.ShowMessage("Unlocked");
                            ConsumeHeld();
                        }
                        else
                        {
                            sound.Play3D("door_locked", d.pos, -2f);
                            hud.ShowMessage("Locked. Needs the " + Level.Capitalize(Json.S(Json.Get(Json.Get(level.meta, "items"), d.lockId), "label", d.lockId)));
                        }
                    }
                    else level.ToggleDoor(d);
                    break;
                }
                case "hide":
                    EnterHide((Level.Hide)t.obj);
                    break;
                case "plank":
                    if (held == "hammer") StartCoroutine(HitPlank((Level.Plank)t.obj));
                    else hud.ShowMessage("Nailed shut. Needs the Hammer");
                    break;
                case "maindoor":
                    hud.ShowMessage("Planks are nailed across the door");
                    break;
                case "padlock":
                    if (held == "main_key") StartCoroutine(Escape());
                    else
                    {
                        sound.Play3D("door_locked", level.doors["door_main"].pos, -2f);
                        hud.ShowMessage("Locked. Needs the Main Door Key");
                    }
                    break;
            }
        }

        void Pick(Level.Item it)
        {
            if (held != "") Drop(true);
            Transform n = it.node;
            n.SetParent(player.hold, false);
            n.localPosition = Vector3.zero;
            n.localRotation = GQ(-20f, 110f, 15f);
            n.localScale = it.id != "hammer" ? Vector3.one * 1.6f : Vector3.one;
            it.held = true;
            held = it.id;
            level.Relight(it, 0.55f);
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
            n.position = new Vector3(p.x, 0.03f, p.z);
            n.rotation = Quaternion.Euler(0f, Random.Range(0f, 360f), 0f);
            n.localScale = Vector3.one;
            it.held = false;
            held = "";
            level.Relight(it);
            if (!quiet)
            {
                sound.Play3D("drop", n.position, 0f);
                level.EmitNoise(n.position, 9f);
            }
        }

        void ConsumeHeld()
        {
            if (held == "") return;
            Level.Item it = level.items[held];
            it.node.gameObject.SetActive(false);
            it.held = true;
            held = "";
        }

        IEnumerator HitPlank(Level.Plank p)
        {
            p.hits++;
            sound.Play3D("hammer_hit", p.pos, 3f);
            level.EmitNoise(p.pos, 16f);
            if (p.hits < 2 || p.gone) yield break;
            p.gone = true;
            level.planksLeft--;
            if (level.planksLeft == 0) hud.ShowMessage("The planks are off");
            Transform n = p.node;
            sound.Play3D("nail_creak", p.pos, 0f);
            Vector3 from = n.localPosition;
            Vector3 to = new Vector3(from.x + Random.Range(-0.2f, 0.2f), 0.03f, from.z - 0.45f);
            Quaternion r0 = n.localRotation;
            Quaternion r1 = GQ(88f, Random.Range(-0.4f, 0.4f) * Mathf.Rad2Deg, 0f);
            float t = 0f;
            while (t < 0.45f && n != null)
            {
                t += Time.deltaTime;
                float k = Mathf.Clamp01(t / 0.45f);
                n.localPosition = Vector3.Lerp(from, to, k * k);          // ease in: it drops
                n.localRotation = Quaternion.Slerp(r0, r1, k);
                yield return null;
            }
            sound.Play3D("plank_fall", p.pos, 2f);
        }

        void EnterHide(Level.Hide h)
        {
            hideRef = h;
            h.target = 0.22f;
            player.SetCrouch(false);
            player.hidden = true;
            player.Teleport(h.pos + new Vector3(0f, 0.12f, 0f));
            player.yaw = Mathf.Atan2(h.front.x, h.front.z) * Mathf.Rad2Deg;
            player.pitch = 0f;
            player.Apply();
            sound.Play3D("door_close", h.pos, -14f);
        }

        void LeaveHide()
        {
            if (hideRef == null)
            {
                player.hidden = false;
                return;
            }
            Level.Hide h = hideRef;
            player.Teleport(h.pos + h.front * 0.95f + new Vector3(0f, 0.05f, 0f));
            player.hidden = false;
            h.target = 0f;
            sound.Play3D("door_open", h.pos, -14f);
            level.EmitNoise(h.pos, 5f);
        }

        // ============================================================================================== cutscenes
        void MakeSkipButton()
        {
            // SKIP, top right, shown while a story cutscene plays
            RectTransform rt = Ui.Node(canvas.transform, "Skip");
            rt.anchorMin = new Vector2(1f, 1f);
            rt.anchorMax = new Vector2(1f, 1f);
            rt.pivot = new Vector2(1f, 1f);
            rt.anchoredPosition = new Vector2(-40f, -30f);
            rt.sizeDelta = new Vector2(210f, 74f);
            var bg = rt.gameObject.AddComponent<Image>();
            bg.color = new Color(0f, 0f, 0f, 0.45f);
            RectTransform br = Ui.Node(rt, "Border");
            Ui.Full(br);
            var border = br.gameObject.AddComponent<Stroke>();
            border.box = true;
            border.radius = 12f;
            border.width = 2f;
            border.color = new Color(1f, 1f, 1f, 0.35f);
            border.raycastTarget = false;
            Text t = Ui.Label(rt, fUi, 38, Color.white, "Text");
            t.text = "SKIP";
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            skipBtn = rt.gameObject.AddComponent<Button>();
            skipBtn.targetGraphic = t;
            ColorBlock cb = skipBtn.colors;
            cb.normalColor = new Color(0.9f, 0.9f, 0.9f, 0.92f);
            cb.highlightedColor = cb.normalColor;
            cb.selectedColor = cb.normalColor;
            cb.pressedColor = new Color(0.78f, 0.06f, 0.05f, 1f);
            skipBtn.colors = cb;
            var nav = new Navigation();
            nav.mode = Navigation.Mode.None;
            skipBtn.navigation = nav;
            skipBtn.onClick.AddListener(OnSkip);
            rt.gameObject.SetActive(false);
        }

        public void OnSkip()
        {
            skip = true;
            skipBtn.gameObject.SetActive(false);
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
                yield return null;
                left -= Time.unscaledDeltaTime;
            }
        }

        IEnumerator FadeTo(float a, float t)
        {
            float from = fade.color.a, k = 0f;
            while (k < 1f)
            {
                yield return null;
                k += Time.unscaledDeltaTime / Mathf.Max(t, 0.01f) * (skip ? 4f : 1f);
                SetAlpha(fade, Mathf.Lerp(from, a, Mathf.Clamp01(k)));
            }
        }

        IEnumerator Shot(Vector3 from, Vector3 to, Vector3 lookA, Vector3 lookB, float dur, string text)
        {
            UseCamera(cutCam);
            cutCam.transform.position = from;
            cutCam.transform.LookAt(lookA);
            caption.text = text;
            yield return StartCoroutine(FadeTo(0f, 0.7f));
            float k = 0f;
            while (k < 1f && !skip)
            {
                yield return null;
                k += Time.unscaledDeltaTime / dur;
                float e = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(k));
                cutCam.transform.position = Vector3.Lerp(from, to, e);
                cutCam.transform.LookAt(Vector3.Lerp(lookA, lookB, e));
            }
            yield return StartCoroutine(FadeTo(1f, 0.6f));
            caption.text = "";
        }

        IEnumerator Intro()
        {
            state = S.Cut;
            skip = false;
            skipBtn.gameObject.SetActive(true);
            ClearMenu();
            hud.gameObject.SetActive(false);
            SetAlpha(fade, 1f);
            moulika.Freeze(true);
            player.frozen = true;
            object o = Json.Get(level.meta, "outside");
            Vector3 gate = Json.GV(Json.Get(o, "gate")), door = Json.GV(Json.Get(o, "door"));
            yield return StartCoroutine(Shot(gate + G(1.5f, 1.5f, 2.5f), gate + G(0.3f, 1.6f, -3.5f), door + G(0f, 2.4f, 0f), door + G(0f, 2.6f, 0f), 6f,
                "Adarsh Vidyalaya. Locked and forgotten since 1998."));
            if (!skip)
                yield return StartCoroutine(Shot(G(-7.8f, 1.5f, -2.2f), G(-2f, 1.5f, -2.2f), G(8f, 1.4f, -2.2f), G(8f, 1.4f, -2.6f), 6f,
                    "They say Moulika ma'am never left her school."));
            if (!skip)
            {
                Vector3 c5 = G(-13f, 0f, 2.5f);
                moulika.transform.position = c5;
                moulika.Yaw = 90f;
                moulika.Play("idle");
                yield return StartCoroutine(Shot(G(-8f, 1.3f, 4.6f), G(-9.6f, 1.4f, 3.4f), c5 + new Vector3(0f, 1.4f, 0f), c5 + new Vector3(0f, 1.55f, 0f), 6f,
                    "Children who stayed back after the last bell were never seen again."));
            }
            if (!skip)
            {
                caption.text = "";
                big.text = "";
                SubOffset(0f);
                sub.text = "Tonight, you stayed back.";
                yield return StartCoroutine(Wait(2.6f));
            }
            sub.text = "";
            SubOffset(190f);
            skipBtn.gameObject.SetActive(false);
            skip = false;
            PlaceStart();
            UseCamera(player.cam);
            big.text = "DAY 1";
            sub.text = "Find a way out of the school.";
            sound.Play("bell", -6f);
            yield return StartCoroutine(Wait(2.2f));
            big.text = "";
            sub.text = "";
            skip = false;
            yield return StartCoroutine(FadeTo(0f, 1.2f));
        }

        void OnCaught()
        {
            if (state != S.Play) return;
            StartCoroutine(CaughtRoutine());
        }

        IEnumerator CaughtRoutine()
        {
            state = S.Cut;
            skip = false;
            hud.gameObject.SetActive(false);
            hud.ResetTouches();
            player.frozen = true;
            if (player.hidden)
            {
                LeaveHide();
                player.Teleport(moulika.transform.position + moulika.FaceDir * 1f);
            }
            hideRef = null;
            Vector3 to = moulika.Eyes - player.Head;
            player.yaw = Mathf.Atan2(to.x, to.z) * Mathf.Rad2Deg;
            player.pitch = Mathf.Atan2(to.y, new Vector2(to.x, to.z).magnitude) * Mathf.Rad2Deg;
            player.Apply();
            sound.Play("scream", 0f);
            yield return new WaitForSeconds(0.55f);
            sound.Play("whack", 4f);
            SetAlpha(flash, 0.85f);
            yield return new WaitForSeconds(0.3f);
            sound.Play("whack", 4f, 0.9f);
            SetAlpha(flash, 0.85f);
            yield return StartCoroutine(FadeTo(1f, 0.5f));
            sound.SetVol("heartbeat", -60f);
            if (held != "") Drop(true);
            day++;
            if (day > 3)
            {
                yield return StartCoroutine(GameOver());
                yield break;
            }
            PlaceStart();
            big.text = "DAY " + day;
            sub.text = day == 2 ? "She let you live. This time." : "This is your last day.";
            yield return new WaitForSeconds(2.6f);
            big.text = "";
            sub.text = "";
            yield return StartCoroutine(FadeTo(0f, 1f));
            BeginDay();
        }

        IEnumerator GameOver()
        {
            moulika.Freeze(true);
            Vector3 p = G(0f, 0f, -8f);
            moulika.transform.position = p;
            moulika.Yaw = 0f;
            UseCamera(cutCam);
            cutCam.transform.position = p + G(0.25f, 1.5f, -2.2f);
            cutCam.transform.LookAt(p + new Vector3(0f, 1.5f, 0f));
            Vector3 c = cutCam.transform.position;
            moulika.Yaw = Mathf.Atan2(c.x - p.x, c.z - p.z) * Mathf.Rad2Deg;
            moulika.Play("scream", 0.1f);
            sound.Play("scream", 2f, 0.85f);
            yield return StartCoroutine(FadeTo(0f, 0.3f));
            float k = 0f;
            while (k < 1.5f)
            {
                yield return null;
                float dt = Time.unscaledDeltaTime;
                k += dt;
                cutCam.transform.position = Vector3.Lerp(cutCam.transform.position, p + G(0.05f, 1.56f, -0.75f), dt * 1.6f);
                cutCam.transform.LookAt(p + new Vector3(0f, 1.58f, 0f));
            }
            yield return StartCoroutine(FadeTo(1f, 0.25f));
            big.text = "GAME OVER";
            sub.text = "No one leaves Moulika ma'am's school.";
            yield return new WaitForSeconds(3.5f);
            FreeWorld();
            ShowMainMenu();
        }

        IEnumerator Escape()
        {
            state = S.Cut;
            skip = false;
            hud.gameObject.SetActive(false);
            player.frozen = true;
            moulika.Freeze(true);
            foreach (Transform n in level.padlockNodes) n.gameObject.SetActive(false);
            sound.Play("unlock", 2f);
            ConsumeHeld();
            yield return new WaitForSeconds(0.7f);
            level.OpenMain();
            yield return new WaitForSeconds(1.3f);
            yield return StartCoroutine(FadeTo(1f, 0.6f));
            object o = Json.Get(level.meta, "outside");
            Vector3 gate = Json.GV(Json.Get(o, "gate")), door = Json.GV(Json.Get(o, "door"));
            sound.SetVol("heartbeat", -60f);
            skipBtn.gameObject.SetActive(true);
            yield return StartCoroutine(Shot(door + G(0f, 1.6f, 1.2f), gate + G(0f, 1.6f, -1.5f), gate + G(0f, 1.5f, 6f), gate + G(0f, 1.5f, 6f), 5f,
                "The night air. The gate. You ran."));
            if (!skip)
            {
                moulika.transform.position = door + G(0f, 0f, -0.6f);
                moulika.Yaw = 180f;
                moulika.Play("scream", 0.1f);
                sound.Play("scream", 0f, 0.9f);
                yield return StartCoroutine(Shot(gate + G(0.4f, 1.6f, 0.5f), gate + G(0.4f, 1.6f, 2.5f), door + new Vector3(0f, 1.5f, 0f), door + new Vector3(0f, 1.5f, 0f), 4f,
                    "She cannot follow you past the door."));
            }
            skipBtn.gameObject.SetActive(false);
            big.text = "YOU ESCAPED";
            sub.text = "MXYAN GAMES OFFICIAL";
            yield return new WaitForSeconds(4.5f);
            FreeWorld();
            ShowMainMenu();
        }

        // ============================================================================================== for the build check
        public void TestBeginDay()
        {
            StopAllCoroutines();
            skipBtn.gameObject.SetActive(false);
            skip = false;
            big.text = "";
            sub.text = "";
            caption.text = "";
            SubOffset(190f);
            SetAlpha(fade, 0f);
            sound.Stop("music_raga");
            sound.Loop(sound.Has("game_music") ? "game_music" : "drone", -17f);
            BeginDay();
        }

        public bool TestBuildWorld(int m)
        {
            mode = m;
            day = 1;
            ClearMenu();
            bool ok = BuildWorld();
            if (ok) PlaceStart();
            return ok;
        }

        public void TestShowSettings() { ShowSettings(); }
        public void TestShowModes() { ShowModes(); }
        public Level.Hide TestHide { get { return hideRef; } }
    }
}
