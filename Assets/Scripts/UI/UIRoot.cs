using System.Collections;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace NightClass
{
    /// <summary>Builds every screen in code: menu, difficulty, settings, loading, HUD, pause, lesson card, endings.</summary>
    public class UIRoot : MonoBehaviour
    {
        NCGame game;
        Canvas canvas;
        RectTransform safe;
        public Hud hud;
        GameObject menu, diff, settings, loading, pause, gameOver, escaped, intro, hudGo;
        Text loadingTip, hintText, escapedText, escapedSecret, msgText, subtitle, cardTitle, cardSub;
        CanvasGroup msgGroup, cardGroup;
        Image fader;
        GameObject settingsReturn;
        Coroutine fadeCo, msgCo, cardCo, subCo;
        Button[] gfxButtons = new Button[3];
        Text fpsLabel, bobLabel;

        public void Build(NCGame g)
        {
            game = g;
            var cgo = new GameObject("Canvas", typeof(RectTransform));
            cgo.layer = 5;
            cgo.transform.SetParent(transform, false);
            canvas = cgo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var scaler = cgo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 1f;
            cgo.AddComponent<GraphicRaycaster>();
            if (FindFirstObjectByType<EventSystem>() == null)
            {
                var es = new GameObject("EventSystem");
                es.AddComponent<EventSystem>();
                es.AddComponent<StandaloneInputModule>();
            }
            safe = UIKit.Rect(canvas.transform, "SafeArea");
            safe.Stretch();
            safe.gameObject.AddComponent<SafeArea>();

            // HUD
            hudGo = new GameObject("HudRoot", typeof(RectTransform));
            hudGo.transform.SetParent(safe, false);
            ((RectTransform)hudGo.transform).Stretch();
            hud = hudGo.AddComponent<Hud>();
            hud.Build(canvas, (RectTransform)hudGo.transform);
            if (TouchControls.I != null) TouchControls.I.hud = hud;
            if (Interactor.I != null) Interactor.I.hud = hud;

            BuildMenu();
            BuildDifficulty();
            BuildSettings();
            BuildLoading();
            BuildPause();
            BuildGameOver();
            BuildEscaped();
            BuildIntro();
            BuildMessages();
            BuildCard();

            fader = UIKit.Img(canvas.transform, "Fader", null, Color.black);
            fader.rectTransform.Stretch();
            fader.raycastTarget = false;
            cardGroup.transform.SetAsLastSibling();
            ShowNone();
        }

        Font Title { get { return GameAssets.I.titleFont; } }
        Font Chalk { get { return GameAssets.I.chalkFont; } }

        GameObject Panel(string name, bool dim)
        {
            RectTransform rt = UIKit.Rect(safe, name).Stretch();
            if (dim)
            {
                Image bg = UIKit.Img(rt, name + "Dim", null, new Color(0f, 0f, 0f, 0.62f));
                bg.rectTransform.Stretch(-400, -400, -400, -400);
                bg.transform.SetAsFirstSibling();
            }
            return rt.gameObject;
        }

        // ------------------------------------------------------------------ menu
        void BuildMenu()
        {
            menu = Panel("Menu", false);
            Image side = UIKit.Img(menu.transform, "Shade", GameAssets.I.vignette, new Color(0f, 0f, 0f, 0.85f));
            side.rectTransform.Stretch(-300, -300, -300, -300);
            Text t = UIKit.Label(menu.transform, "Title", "NIGHT CLASS", 150, UIKit.Chalk, TextAnchor.MiddleLeft, Title);
            t.rectTransform.Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(110f, 250f), new Vector2(1400f, 200f));
            var red = t.gameObject.AddComponent<Outline>();
            red.effectColor = new Color(0.55f, 0.03f, 0.02f, 0.9f);
            red.effectDistance = new Vector2(4f, -4f);
            Text s = UIKit.Label(menu.transform, "Sub", "Get out before the lesson ends.", 40, UIKit.DimText, TextAnchor.MiddleLeft, Chalk);
            s.rectTransform.Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(118f, 130f), new Vector2(1200f, 60f));
            Button play = UIKit.Btn(menu.transform, "Play", "PLAY", new Vector2(460f, 110f), () => Show(diff), 48);
            play.GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(118f, -10f), new Vector2(460f, 110f));
            play.GetComponent<Image>().color = new Color(0.45f, 0.06f, 0.05f, 0.92f);
            Button st = UIKit.Btn(menu.transform, "Settings", "SETTINGS", new Vector2(460f, 96f), () => OpenSettings(menu), 38);
            st.GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(118f, -135f), new Vector2(460f, 96f));
            Button q = UIKit.Btn(menu.transform, "Quit", "QUIT", new Vector2(460f, 96f), () => Application.Quit(), 38);
            q.GetComponent<RectTransform>().Place(new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(118f, -250f), new Vector2(460f, 96f));
            if (NCGame.HasEscapedBefore)
            {
                Text e = UIKit.Label(menu.transform, "Escaped", "You escaped once. The secret room is open.", 30, new Color(0.9f, 0.8f, 0.45f), TextAnchor.MiddleLeft, Chalk);
                e.rectTransform.Place(new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(118f, 60f), new Vector2(1200f, 50f));
            }
        }

        void BuildDifficulty()
        {
            diff = Panel("Difficulty", true);
            Text t = UIKit.Label(diff.transform, "Title", "CHOOSE YOUR LESSON", 70, UIKit.Chalk, TextAnchor.MiddleCenter, Chalk);
            t.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -70f), new Vector2(1600f, 100f));
            Card(diff.transform, "GHOST", "Explore freely.\nShe can't see you\nor catch you.", new Vector2(-560f, -20f), new Color(0.16f, 0.24f, 0.3f, 0.92f), Difficulty.Ghost);
            Card(diff.transform, "NORMAL", "The real lesson.\nFive lessons to\nescape the school.", new Vector2(0f, -20f), new Color(0.3f, 0.18f, 0.1f, 0.92f), Difficulty.Normal);
            Card(diff.transform, "HARD", "Thick fog, a faster\nteacher and no\nsounds to warn you.", new Vector2(560f, -20f), new Color(0.38f, 0.05f, 0.04f, 0.92f), Difficulty.Hard);
            Button back = UIKit.Btn(diff.transform, "Back", "BACK", new Vector2(300f, 90f), () => Show(menu), 36);
            back.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 60f), new Vector2(300f, 90f));
        }

        void Card(Transform parent, string title, string desc, Vector2 pos, Color col, Difficulty d)
        {
            Button b = UIKit.Btn(parent, title, "", new Vector2(500f, 560f), () => game.StartGame(d), 10);
            b.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), pos, new Vector2(500f, 560f));
            b.GetComponent<Image>().color = col;
            Text tt = UIKit.Label(b.transform, "T", title, 76, UIKit.Chalk, TextAnchor.MiddleCenter, Title);
            tt.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -50f), new Vector2(480f, 110f));
            Text dd = UIKit.Label(b.transform, "D", desc, 36, UIKit.TextColor, TextAnchor.MiddleCenter, Chalk);
            dd.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, -60f), new Vector2(440f, 300f));
        }

        // ------------------------------------------------------------------ settings
        void BuildSettings()
        {
            settings = Panel("Settings", true);
            Text t = UIKit.Label(settings.transform, "Title", "SETTINGS", 70, UIKit.Chalk, TextAnchor.MiddleCenter, Chalk);
            t.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -60f), new Vector2(1200f, 100f));
            float y = 275f;
            Row("Graphics", y);
            string[] names = { "LOW", "MEDIUM", "HIGH" };
            for (int i = 0; i < 3; i++)
            {
                int lvl = i;
                gfxButtons[i] = UIKit.Btn(settings.transform, "Gfx" + i, names[i], new Vector2(250f, 80f), () =>
                {
                    GameSettings.Graphics = (GraphicsLevel)lvl;
                    GameSettings.Save();
                    if (QualityManager.I != null) QualityManager.I.Apply();
                    RefreshSettings();
                }, 32);
                gfxButtons[i].GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(-60f + i * 270f, y), new Vector2(250f, 80f));
            }
            y -= 100f;
            Row("Brightness", y);
            Slider sb = UIKit.Slider(settings.transform, "Bright", new Vector2(520f, 54f), 0.6f, 2.2f, GameSettings.Brightness, v =>
            {
                GameSettings.Brightness = v;
                GameSettings.Save();
                if (QualityManager.I != null) QualityManager.I.ApplyBrightness();
            });
            sb.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(75f, y), new Vector2(520f, 54f));
            y -= 100f;
            Row("Frame rate", y);
            Button fps = UIKit.Btn(settings.transform, "Fps", "", new Vector2(520f, 80f), () =>
            {
                GameSettings.Fps60 = !GameSettings.Fps60;
                GameSettings.Save();
                RefreshSettings();
            }, 32);
            fps.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(75f, y), new Vector2(520f, 80f));
            fpsLabel = fps.GetComponentInChildren<Text>();
            y -= 100f;
            Row("Look speed", y);
            Slider s1 = UIKit.Slider(settings.transform, "Sens", new Vector2(520f, 54f), 0.3f, 2.5f, GameSettings.LookSensitivity, v => { GameSettings.LookSensitivity = v; GameSettings.Save(); });
            s1.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(75f, y), new Vector2(520f, 54f));
            y -= 100f;
            Row("Field of view", y);
            Slider s2 = UIKit.Slider(settings.transform, "Fov", new Vector2(520f, 54f), 55f, 80f, GameSettings.FieldOfView, v => { GameSettings.FieldOfView = v; GameSettings.Save(); });
            s2.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(75f, y), new Vector2(520f, 54f));
            y -= 100f;
            Row("Head bob", y);
            Button bob = UIKit.Btn(settings.transform, "Bob", "", new Vector2(520f, 80f), () =>
            {
                GameSettings.HeadBob = !GameSettings.HeadBob;
                GameSettings.Save();
                RefreshSettings();
            }, 32);
            bob.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(75f, y), new Vector2(520f, 80f));
            bobLabel = bob.GetComponentInChildren<Text>();
            y -= 100f;
            Row("Volume", y);
            Slider s3 = UIKit.Slider(settings.transform, "Vol", new Vector2(520f, 54f), 0f, 1f, GameSettings.Volume, v => { GameSettings.Volume = v; GameSettings.Save(); });
            s3.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(75f, y), new Vector2(520f, 54f));
            Button back = UIKit.Btn(settings.transform, "Back", "BACK", new Vector2(300f, 90f), () => Show(settingsReturn != null ? settingsReturn : menu), 36);
            back.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 50f), new Vector2(300f, 90f));
        }

        void Row(string label, float y)
        {
            Text l = UIKit.Label(settings.transform, label, label, 38, UIKit.TextColor, TextAnchor.MiddleRight, GameAssets.I.uiFontBold);
            l.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(1f, 0.5f), new Vector2(-220f, y), new Vector2(500f, 70f));
        }

        void RefreshSettings()
        {
            for (int i = 0; i < 3; i++)
                if (gfxButtons[i] != null)
                    gfxButtons[i].GetComponent<Image>().color = (int)GameSettings.Graphics == i ? new Color(0.5f, 0.08f, 0.06f, 0.95f) : UIKit.ButtonColor;
            if (fpsLabel != null) fpsLabel.text = GameSettings.Fps60 ? "60 FPS (smoother)" : "30 FPS (battery saver)";
            if (bobLabel != null) bobLabel.text = GameSettings.HeadBob ? "ON" : "OFF";
        }

        void OpenSettings(GameObject from)
        {
            settingsReturn = from;
            RefreshSettings();
            Show(settings);
        }

        // ------------------------------------------------------------------ loading / intro
        void BuildLoading()
        {
            loading = Panel("Loading", false);
            Image bg = UIKit.Img(loading.transform, "Bg", null, Color.black);
            bg.rectTransform.Stretch(-400, -400, -400, -400);
            Text t = UIKit.Label(loading.transform, "Title", "NIGHT CLASS", 120, UIKit.Chalk, TextAnchor.MiddleCenter, Title);
            t.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, 120f), new Vector2(1600f, 180f));
            Text l = UIKit.Label(loading.transform, "L", "Loading...", 40, UIKit.DimText, TextAnchor.MiddleCenter, Chalk);
            l.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, -10f), new Vector2(800f, 60f));
            loadingTip = UIKit.Label(loading.transform, "Tip", "", 34, UIKit.TextColor, TextAnchor.MiddleCenter, GameAssets.I.uiFont);
            loadingTip.rectTransform.Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 120f), new Vector2(1500f, 100f));
        }

        void BuildIntro()
        {
            intro = Panel("Intro", false);
            Text s = UIKit.Label(intro.transform, "Skip", "Tap to skip", 28, new Color(1f, 1f, 1f, 0.5f), TextAnchor.MiddleRight, GameAssets.I.uiFont);
            s.rectTransform.Place(new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-50f, 40f), new Vector2(400f, 50f));
        }

        // ------------------------------------------------------------------ pause / endings
        void BuildPause()
        {
            pause = Panel("Pause", true);
            Text t = UIKit.Label(pause.transform, "Title", "PAUSED", 90, UIKit.Chalk, TextAnchor.MiddleCenter, Chalk);
            t.rectTransform.Place(new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -80f), new Vector2(1200f, 120f));
            string[] labels = { "RESUME", "HINT", "RESTART", "SETTINGS", "MAIN MENU" };
            for (int i = 0; i < labels.Length; i++)
            {
                int k = i;
                Button b = UIKit.Btn(pause.transform, labels[i], labels[i], new Vector2(520f, 92f), () =>
                {
                    switch (k)
                    {
                        case 0: game.Resume(); break;
                        case 1: hintText.text = Progress.Hint(); break;
                        case 2: Time.timeScale = 1f; game.Restart(); break;
                        case 3: OpenSettings(pause); break;
                        case 4: Time.timeScale = 1f; game.QuitToMenu(); break;
                    }
                }, 38);
                b.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, 230f - i * 112f), new Vector2(520f, 92f));
            }
            hintText = UIKit.Label(pause.transform, "Hint", "", 32, new Color(0.95f, 0.85f, 0.5f), TextAnchor.MiddleCenter, Chalk);
            hintText.rectTransform.Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 50f), new Vector2(1500f, 90f));
        }

        void BuildGameOver()
        {
            gameOver = Panel("GameOver", true);
            Text t = UIKit.Label(gameOver.transform, "Title", "EXPELLED", 170, new Color(0.85f, 0.1f, 0.08f), TextAnchor.MiddleCenter, Title);
            t.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, 200f), new Vector2(1600f, 220f));
            Text s = UIKit.Label(gameOver.transform, "Sub", "She caught you five times.\nClass is never over.", 42, UIKit.TextColor, TextAnchor.MiddleCenter, Chalk);
            s.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, 30f), new Vector2(1400f, 140f));
            Button r = UIKit.Btn(gameOver.transform, "Restart", "TRY AGAIN", new Vector2(420f, 100f), () => game.Restart(), 40);
            r.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(-230f, -170f), new Vector2(420f, 100f));
            Button m = UIKit.Btn(gameOver.transform, "Menu", "MAIN MENU", new Vector2(420f, 100f), () => game.QuitToMenu(), 40);
            m.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(230f, -170f), new Vector2(420f, 100f));
        }

        void BuildEscaped()
        {
            escaped = Panel("Escaped", true);
            Text t = UIKit.Label(escaped.transform, "Title", "YOU ESCAPED", 150, new Color(0.95f, 0.9f, 0.7f), TextAnchor.MiddleCenter, Title);
            t.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, 210f), new Vector2(1700f, 200f));
            escapedText = UIKit.Label(escaped.transform, "Sub", "", 42, UIKit.TextColor, TextAnchor.MiddleCenter, Chalk);
            escapedText.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, 60f), new Vector2(1400f, 100f));
            escapedSecret = UIKit.Label(escaped.transform, "Secret", "", 34, new Color(0.95f, 0.8f, 0.4f), TextAnchor.MiddleCenter, Chalk);
            escapedSecret.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, -30f), new Vector2(1500f, 80f));
            Button r = UIKit.Btn(escaped.transform, "Again", "PLAY AGAIN", new Vector2(420f, 100f), () => game.Restart(), 40);
            r.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(-230f, -180f), new Vector2(420f, 100f));
            Button m = UIKit.Btn(escaped.transform, "Menu", "MAIN MENU", new Vector2(420f, 100f), () => game.QuitToMenu(), 40);
            m.GetComponent<RectTransform>().Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(230f, -180f), new Vector2(420f, 100f));
        }

        // ------------------------------------------------------------------ messages / lesson card
        void BuildMessages()
        {
            RectTransform box = UIKit.Img(safe, "Message", GameAssets.I.rounded, new Color(0f, 0f, 0f, 0.62f)).rectTransform;
            box.Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 300f), new Vector2(1100f, 110f));
            msgGroup = box.gameObject.AddComponent<CanvasGroup>();
            msgGroup.alpha = 0f;
            msgGroup.blocksRaycasts = false;
            msgText = UIKit.Label(box, "Text", "", 36, UIKit.TextColor, TextAnchor.MiddleCenter, GameAssets.I.uiFontBold);
            msgText.rectTransform.Stretch(30, 30, 8, 8);
            subtitle = UIKit.Label(safe, "Subtitle", "", 46, UIKit.Chalk, TextAnchor.MiddleCenter, Chalk);
            subtitle.rectTransform.Place(new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 150f), new Vector2(1600f, 120f));
        }

        void BuildCard()
        {
            RectTransform card = UIKit.Rect(canvas.transform, "LessonCard").Stretch();
            Image bg = UIKit.Img(card, "Bg", null, Color.black);
            bg.rectTransform.Stretch();
            cardGroup = card.gameObject.AddComponent<CanvasGroup>();
            cardGroup.alpha = 0f;
            cardGroup.blocksRaycasts = false;
            cardTitle = UIKit.Label(card, "Title", "", 150, UIKit.Chalk, TextAnchor.MiddleCenter, Chalk);
            cardTitle.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, 60f), new Vector2(1600f, 200f));
            cardSub = UIKit.Label(card, "Sub", "", 44, UIKit.DimText, TextAnchor.MiddleCenter, Chalk);
            cardSub.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, -80f), new Vector2(1600f, 80f));
        }

        public void ShowDayCard(int day, int max)
        {
            cardTitle.text = "LESSON " + day;
            int left = max - day;
            cardSub.text = left == 0 ? "This is your last chance." : left + (left == 1 ? " lesson left after this one." : " lessons left after this one.");
            if (cardCo != null) StopCoroutine(cardCo);
            cardCo = StartCoroutine(CardSeq());
        }

        IEnumerator CardSeq()
        {
            cardGroup.alpha = 1f;
            yield return new WaitForSeconds(2.2f);
            float t = 0f;
            while (t < 1f)
            {
                t += Time.unscaledDeltaTime / 0.9f;
                cardGroup.alpha = 1f - t;
                yield return null;
            }
            cardGroup.alpha = 0f;
        }

        public void Message(string text, float seconds)
        {
            if (msgCo != null) StopCoroutine(msgCo);
            msgCo = StartCoroutine(MsgSeq(text, seconds));
        }

        IEnumerator MsgSeq(string text, float seconds)
        {
            msgText.text = text;
            float t = msgGroup.alpha;
            while (t < 1f) { t += Time.unscaledDeltaTime / 0.15f; msgGroup.alpha = t; yield return null; }
            yield return new WaitForSecondsRealtime(seconds);
            while (t > 0f) { t -= Time.unscaledDeltaTime / 0.4f; msgGroup.alpha = t; yield return null; }
            msgGroup.alpha = 0f;
        }

        public void Subtitle(string text, float seconds)
        {
            if (subCo != null) StopCoroutine(subCo);
            subtitle.text = text;
            if (seconds > 0f) subCo = StartCoroutine(ClearSub(seconds));
        }

        IEnumerator ClearSub(float s)
        {
            yield return new WaitForSeconds(s);
            subtitle.text = "";
        }

        // ------------------------------------------------------------------ fading
        public void FadeTo(float alpha, float dur)
        {
            if (fadeCo != null) StopCoroutine(fadeCo);
            fadeCo = StartCoroutine(FadeSeq(fader.color.a, alpha, dur));
        }

        public void FadeFrom(float alpha, float dur)
        {
            if (fadeCo != null) StopCoroutine(fadeCo);
            fadeCo = StartCoroutine(FadeSeq(alpha, 0f, dur));
        }

        IEnumerator FadeSeq(float a, float b, float dur)
        {
            float t = 0f;
            while (t < 1f)
            {
                t += Time.unscaledDeltaTime / Mathf.Max(0.01f, dur);
                fader.color = new Color(0f, 0f, 0f, Mathf.Lerp(a, b, Mathf.SmoothStep(0f, 1f, t)));
                yield return null;
            }
            fader.color = new Color(0f, 0f, 0f, b);
        }

        // ------------------------------------------------------------------ switching
        void Show(GameObject panel)
        {
            GameObject[] all = { menu, diff, settings, loading, pause, gameOver, escaped, intro };
            foreach (GameObject p in all) if (p != null) p.SetActive(p == panel);
            hudGo.SetActive(false);
        }

        public void ShowMenu() { Show(menu); }
        public void ShowNone() { Show(null); }
        public void ShowIntro() { Show(intro); }

        public void ShowLoading(string tip)
        {
            loadingTip.text = "TIP: " + tip;
            Show(loading);
        }

        public void ShowHud()
        {
            Show(null);
            hudGo.SetActive(true);
        }

        public void ShowPause()
        {
            hintText.text = "";
            Show(pause);
        }

        public void ShowGameOver() { Show(gameOver); }

        public void ShowEscaped(int day, bool first)
        {
            escapedText.text = "You got out during lesson " + Mathf.Min(day, NCGame.MaxDays) + " of " + NCGame.MaxDays + ".";
            escapedSecret.text = first ? "Something has changed in your classroom... a secret room is open." : "";
            Show(escaped);
        }
    }
}
