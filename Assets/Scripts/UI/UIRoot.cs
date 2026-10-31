using System.Collections;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace RealFPS
{
    /// <summary>Builds the canvas and switches between menu, HUD, pause and settings.</summary>
    public class UIRoot : MonoBehaviour
    {
        public Hud Hud { get; private set; }

        Canvas canvas;
        RectTransform safe;
        GameObject menu, pause, settings;
        Image fade;
        Text pauseLanterns;
        Game game;
        Button playButton;
        System.Action settingsBack;

        // settings widgets
        Button[] gfxButtons, fpsButtons;
        Button invertBtn, bobBtn, fpsShowBtn;

        public void Build(Game g)
        {
            game = g;
            GameAssets A = GameAssets.I;

            var cgo = new GameObject("UI", typeof(RectTransform));
            cgo.layer = 5;
            canvas = cgo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var scaler = cgo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 1f;
            cgo.AddComponent<GraphicRaycaster>();

            if (FindObjectOfType<EventSystem>() == null)
            {
                var es = new GameObject("EventSystem");
                es.AddComponent<EventSystem>();
                es.AddComponent<StandaloneInputModule>();
            }

            safe = UIKit.Rect(cgo.transform, "SafeArea");
            safe.gameObject.AddComponent<SafeArea>();

            Hud = gameObject.AddComponent<Hud>();
            Hud.Build(canvas, safe);
            var controls = gameObject.AddComponent<TouchControls>();
            controls.hud = Hud;

            BuildMenu(safe);
            BuildPause(safe);
            BuildSettings(safe);

            fade = UIKit.Img(cgo.transform, "Fade", null, Color.black, false);
            fade.rectTransform.Stretch();
            fade.color = new Color(0f, 0f, 0f, 1f);
            StartCoroutine(Fade(0f, 1.2f));
        }

        // ------------------------------------------------------------------ screens
        void BuildMenu(RectTransform parent)
        {
            GameAssets A = GameAssets.I;
            RectTransform root = UIKit.Rect(parent, "Menu").Stretch();
            menu = root.gameObject;

            var shade = UIKit.Img(root, "Shade", A.fadeH, new Color(0f, 0f, 0f, 0.62f));
            shade.rectTransform.anchorMin = new Vector2(0f, 0f);
            shade.rectTransform.anchorMax = new Vector2(0.62f, 1f);
            shade.rectTransform.offsetMin = new Vector2(-200f, -50f);
            shade.rectTransform.offsetMax = Vector2.zero;
            shade.type = Image.Type.Simple;

            Text title = UIKit.Label(root, "Title", "SILENT VALLEY", 112, Color.white, TextAnchor.MiddleLeft, A.titleFont);
            title.rectTransform.Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(120f, -150f), new Vector2(1200f, 140f));
            Text sub = UIKit.Label(root, "Subtitle", "A REALISTIC FIRST-PERSON PROTOTYPE", 30, UIKit.Accent, TextAnchor.MiddleLeft, A.uiFontBold);
            sub.rectTransform.Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(126f, -290f), new Vector2(1200f, 44f));

            float y = -420f;
            playButton = UIKit.Btn(root, "Play", "PLAY", new Vector2(420f, 96f), () => game.StartGame(), 40);
            playButton.GetComponent<RectTransform>().Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(120f, y), new Vector2(420f, 96f));
            var playImg = playButton.GetComponent<Image>();
            playImg.color = new Color(UIKit.Accent.r * 0.9f, UIKit.Accent.g * 0.75f, UIKit.Accent.b * 0.45f, 0.92f);
            Button set = UIKit.Btn(root, "Settings", "SETTINGS", new Vector2(420f, 84f), () => OpenSettings(ShowMenu));
            set.GetComponent<RectTransform>().Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(120f, y - 120f), new Vector2(420f, 84f));
            Button quit = UIKit.Btn(root, "Quit", "QUIT", new Vector2(420f, 84f), () => Application.Quit());
            quit.GetComponent<RectTransform>().Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(120f, y - 228f), new Vector2(420f, 84f));

            Text help = UIKit.Label(root, "Goal", "Explore the valley and find the 5 lost lanterns.", 28, UIKit.DimText, TextAnchor.MiddleLeft, A.uiFont);
            help.rectTransform.Place(new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(124f, y - 340f), new Vector2(1000f, 40f));

            Text credit = UIKit.Label(root, "Credits", "Made with Unity  •  Sky, textures & models: Poly Haven (CC0)", 22, new Color(1f, 1f, 1f, 0.6f), TextAnchor.LowerLeft, A.uiFont);
            credit.rectTransform.Place(new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(120f, 34f), new Vector2(1200f, 30f));
            Text ver = UIKit.Label(root, "Version", "v" + Application.version, 22, new Color(1f, 1f, 1f, 0.6f), TextAnchor.LowerRight, A.uiFont);
            ver.rectTransform.Place(new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-40f, 34f), new Vector2(400f, 30f));
        }

        void BuildPause(RectTransform parent)
        {
            GameAssets A = GameAssets.I;
            RectTransform root = UIKit.Rect(parent, "Pause").Stretch(-200, -200, -200, -200);
            pause = root.gameObject;
            var dim = UIKit.Img(root, "Dim", null, new Color(0f, 0f, 0f, 0.55f), true);
            dim.rectTransform.Stretch();
            RectTransform box = UIKit.Rect(root, "Box").Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(600f, 640f));
            Text t = UIKit.Label(box, "Title", "PAUSED", 84, Color.white, TextAnchor.MiddleCenter, A.titleFont);
            t.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -10f), new Vector2(600f, 110f));
            pauseLanterns = UIKit.Label(box, "Lanterns", "", 30, UIKit.Accent, TextAnchor.MiddleCenter, A.uiFont);
            pauseLanterns.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -122f), new Vector2(600f, 40f));
            string[] labels = { "RESUME", "SETTINGS", "MAIN MENU" };
            UnityEngine.Events.UnityAction[] actions = { () => game.Resume(), () => OpenSettings(ShowPause), () => game.QuitToMenu() };
            for (int i = 0; i < 3; i++)
            {
                Button b = UIKit.Btn(box, labels[i], labels[i], new Vector2(440f, 92f), actions[i]);
                b.GetComponent<RectTransform>().Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -210f - i * 116f), new Vector2(440f, 92f));
            }
        }

        void BuildSettings(RectTransform parent)
        {
            GameAssets A = GameAssets.I;
            RectTransform root = UIKit.Rect(parent, "Settings").Stretch(-200, -200, -200, -200);
            settings = root.gameObject;
            var dim = UIKit.Img(root, "Dim", null, new Color(0f, 0f, 0f, 0.6f), true);
            dim.rectTransform.Stretch();
            var panel = UIKit.Img(root, "Panel", A.rounded, UIKit.PanelColor);
            RectTransform box = panel.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(1180f, 860f));
            Text t = UIKit.Label(box, "Title", "SETTINGS", 64, Color.white, TextAnchor.MiddleCenter, A.titleFont);
            t.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -20f), new Vector2(800f, 90f));

            float rowY = -150f;
            const float rowH = 86f;
            int row = 0;

            RectTransform Row(string label)
            {
                RectTransform r = UIKit.Rect(box, label).Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, rowY - row * rowH), new Vector2(1060f, 72f));
                Text l = UIKit.Label(r, "Label", label, 32, UIKit.TextColor, TextAnchor.MiddleLeft, A.uiFont, false);
                l.rectTransform.Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), Vector2.zero, new Vector2(420f, 60f));
                row++;
                return r;
            }

            RectTransform gfx = Row("Graphics");
            string[] gl = { "LOW", "MEDIUM", "HIGH" };
            gfxButtons = new Button[3];
            for (int i = 0; i < 3; i++)
            {
                int level = i;
                gfxButtons[i] = UIKit.Btn(gfx, gl[i], gl[i], new Vector2(196f, 66f), () => { GameSettings.Graphics = (GraphicsLevel)level; GameSettings.Save(); RefreshSettings(); }, 28);
                gfxButtons[i].GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(440f + i * 208f, 0f), new Vector2(196f, 66f));
            }

            RectTransform fr = Row("Frame rate");
            string[] fl = { "30 FPS", "60 FPS" };
            fpsButtons = new Button[2];
            for (int i = 0; i < 2; i++)
            {
                bool sixty = i == 1;
                fpsButtons[i] = UIKit.Btn(fr, fl[i], fl[i], new Vector2(196f, 66f), () => { GameSettings.Fps60 = sixty; GameSettings.Save(); RefreshSettings(); }, 28);
                fpsButtons[i].GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(440f + i * 208f, 0f), new Vector2(196f, 66f));
            }

            RectTransform sens = Row("Look sensitivity");
            Slider ss = UIKit.Slider(sens, "Slider", new Vector2(560f, 44f), 0.3f, 2.5f, GameSettings.LookSensitivity, v => { GameSettings.LookSensitivity = v; });
            ss.GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(450f, 0f), new Vector2(560f, 44f));

            RectTransform fov = Row("Field of view");
            Slider fs = UIKit.Slider(fov, "Slider", new Vector2(560f, 44f), 48f, 75f, GameSettings.FieldOfView, v => { GameSettings.FieldOfView = v; if (game.player != null) game.player.ApplySettings(); });
            fs.GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(450f, 0f), new Vector2(560f, 44f));

            RectTransform vol = Row("Volume");
            Slider vs = UIKit.Slider(vol, "Slider", new Vector2(560f, 44f), 0f, 1f, GameSettings.Volume, v => { GameSettings.Volume = v; AudioListener.volume = v; });
            vs.GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(450f, 0f), new Vector2(560f, 44f));

            RectTransform toggles = Row("");
            invertBtn = Toggle(toggles, "Invert look", 0, () => { GameSettings.InvertY = !GameSettings.InvertY; GameSettings.Save(); RefreshSettings(); });
            bobBtn = Toggle(toggles, "Head bob", 1, () => { GameSettings.HeadBob = !GameSettings.HeadBob; GameSettings.Save(); RefreshSettings(); });
            fpsShowBtn = Toggle(toggles, "Show FPS", 2, () => { GameSettings.ShowFps = !GameSettings.ShowFps; GameSettings.Save(); RefreshSettings(); });

            Button back = UIKit.Btn(box, "Back", "BACK", new Vector2(360f, 86f), () => { GameSettings.Save(); if (settingsBack != null) settingsBack(); });
            back.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 36f), new Vector2(360f, 86f));
        }

        Button Toggle(RectTransform parent, string label, int index, UnityEngine.Events.UnityAction onClick)
        {
            Button b = UIKit.Btn(parent, label, label, new Vector2(340f, 66f), onClick, 27);
            b.GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(index * 360f, 0f), new Vector2(340f, 66f));
            return b;
        }

        void RefreshSettings()
        {
            for (int i = 0; i < gfxButtons.Length; i++)
                Highlight(gfxButtons[i], (int)GameSettings.Graphics == i);
            Highlight(fpsButtons[0], !GameSettings.Fps60);
            Highlight(fpsButtons[1], GameSettings.Fps60);
            UIKit.SetLabel(invertBtn, "Invert look: " + (GameSettings.InvertY ? "ON" : "OFF"));
            UIKit.SetLabel(bobBtn, "Head bob: " + (GameSettings.HeadBob ? "ON" : "OFF"));
            UIKit.SetLabel(fpsShowBtn, "Show FPS: " + (GameSettings.ShowFps ? "ON" : "OFF"));
            Highlight(invertBtn, GameSettings.InvertY);
            Highlight(bobBtn, GameSettings.HeadBob);
            Highlight(fpsShowBtn, GameSettings.ShowFps);
        }

        static void Highlight(Button b, bool on)
        {
            var img = b.GetComponent<Image>();
            img.color = on ? new Color(UIKit.Accent.r * 0.85f, UIKit.Accent.g * 0.68f, UIKit.Accent.b * 0.4f, 0.95f) : UIKit.ButtonColor;
        }

        // ------------------------------------------------------------------ switching
        void Show(GameObject active)
        {
            menu.SetActive(active == menu);
            pause.SetActive(active == pause);
            settings.SetActive(active == settings);
            Hud.Root.gameObject.SetActive(active == null);
        }

        public void ShowMenu() { Show(menu); }
        public void ShowHud() { Show(null); }

        public void ShowPause()
        {
            pauseLanterns.text = "Lanterns found: " + game.LanternsFound + " / " + game.LanternCount;
            Show(pause);
        }

        void OpenSettings(System.Action back)
        {
            settingsBack = back;
            RefreshSettings();
            Show(settings);
        }

        public IEnumerator Fade(float target, float duration)
        {
            fade.gameObject.SetActive(true);
            fade.raycastTarget = target > 0.5f;
            float start = fade.color.a;
            float t = 0f;
            while (t < duration)
            {
                t += Time.unscaledDeltaTime;
                float a = Mathf.Lerp(start, target, Mathf.SmoothStep(0f, 1f, t / duration));
                fade.color = new Color(0f, 0f, 0f, a);
                yield return null;
            }
            fade.color = new Color(0f, 0f, 0f, target);
            if (target <= 0.001f) fade.gameObject.SetActive(false);
        }

        public string LayoutReport()
        {
            Vector2 play = RectTransformUtility.WorldToScreenPoint(null, playButton.transform.position);
            bool hudOn = Hud.Root.gameObject.activeSelf;
            Hud.Root.gameObject.SetActive(true);
            Canvas.ForceUpdateCanvases();
            Vector2 jump = Hud.ButtonScreenPos(HudAction.Jump);
            Vector2 crouch = Hud.ButtonScreenPos(HudAction.Crouch);
            Vector2 run = Hud.ButtonScreenPos(HudAction.Run);
            Vector2 pz = Hud.ButtonScreenPos(HudAction.Pause);
            Vector2 joy = Hud.JoyHomeScreenPos();
            Hud.Root.gameObject.SetActive(hudOn);
            System.Func<Vector2, string> f = v => Mathf.RoundToInt(v.x) + "," + Mathf.RoundToInt(v.y);
            return "w=" + Screen.width + " h=" + Screen.height + " play=" + f(play) + " jump=" + f(jump) + " crouch=" + f(crouch) +
                   " run=" + f(run) + " pause=" + f(pz) + " joy=" + f(joy);
        }
    }
}
