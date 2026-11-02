using System.Collections;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace NightClass
{
    public enum GameState { Menu, Loading, Intro, Playing, Paused, Caught, GameOver, Escaped }

    /// <summary>
    /// Game flow: menu -> difficulty -> loading -> intro -> five lessons (days). Being caught costs a
    /// lesson; after the fifth the player is expelled. Escaping through the main door wins and opens
    /// the secret room for the next run.
    /// </summary>
    public class NCGame : MonoBehaviour
    {
        public static NCGame I { get; private set; }
        public static bool PendingStart;
        public static Difficulty PendingDifficulty = Difficulty.Normal;
        public const int MaxDays = 5;

        public GameState State { get; private set; }
        public Difficulty Diff { get; private set; }
        public int Day { get; private set; }

        [Header("Scene")]
        public FPController player;
        public Inventory inventory;
        public TeacherAI teacher;
        public UIRoot ui;
        public Camera mainCam;
        public Transform playerSpawn;
        public Transform introCam;
        public Transform[] menuCamPoints;
        public Transform[] endingCamPoints;
        public NavBaker navBaker;

        AudioSource chase, heart, ambient;
        float menuT;
        bool skipIntro;
        public static bool HasEscapedBefore { get { return PlayerPrefs.GetInt("nc_escaped", 0) == 1; } }

        void Awake()
        {
            I = this;
            Time.timeScale = 1f;
            Progress.Reset();
        }

        void Start()
        {
            GameSettings.Load();
            if (QualityManager.I != null) QualityManager.I.Apply();
            ApplyAmbient(GameAssets.I.ambientColor);
            ui.Build(this);
            if (navBaker != null) navBaker.Build();
            chase = Sfx.Loop(gameObject, GameAssets.I.chaseLoop, 0f, 20f, false);
            heart = Sfx.Loop(gameObject, GameAssets.I.heartbeat, 0f, 20f, false);
            ambient = Sfx.Loop(gameObject, GameAssets.I.ambientLoop, 0.35f, 20f, false);
            if (PendingStart)
            {
                PendingStart = false;
                StartCoroutine(LoadingSeq(PendingDifficulty));
            }
            else EnterMenu();
        }

        // ------------------------------------------------------------------ menu
        public void EnterMenu()
        {
            State = GameState.Menu;
            player.SetActive(false);
            if (teacher != null) teacher.SetMenuMode(true);
            ui.ShowMenu();
            ui.FadeFrom(1f, 1.2f);
            menuT = 0f;
        }

        void UpdateMenuCamera()
        {
            if (menuCamPoints == null || menuCamPoints.Length < 2) return;
            menuT += Time.unscaledDeltaTime * 0.035f;
            float f = menuT % (menuCamPoints.Length);
            int a = Mathf.FloorToInt(f);
            int b = (a + 1) % menuCamPoints.Length;
            float t = Mathf.SmoothStep(0f, 1f, f - a);
            Transform c = mainCam.transform;
            if (c.parent != null) c.SetParent(null, true);
            c.position = Vector3.Lerp(menuCamPoints[a].position, menuCamPoints[b].position, t);
            c.rotation = Quaternion.Slerp(menuCamPoints[a].rotation, menuCamPoints[b].rotation, t);
            mainCam.fieldOfView = 55f;
        }

        public void StartGame(Difficulty d)
        {
            PendingStart = true;
            PendingDifficulty = d;
            StartCoroutine(Reload());
        }

        IEnumerator Reload()
        {
            ui.FadeTo(1f, 0.4f);
            yield return new WaitForSecondsRealtime(0.45f);
            Time.timeScale = 1f;
            SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
        }

        // ------------------------------------------------------------------ loading + intro
        IEnumerator LoadingSeq(Difficulty d)
        {
            State = GameState.Loading;
            Diff = d;
            Day = 1;
            ApplyDifficulty();
            player.SetActive(false);
            ui.ShowLoading(Progress.Hint());
            ui.FadeFrom(1f, 0.4f);
            yield return new WaitForSeconds(2.2f);
            yield return StartCoroutine(IntroSeq());
        }

        /// <summary>Night ambient light. Set explicitly: a scene generated in batch mode has no baked ambient probe,
        /// and Unity's default one (a bright daytime sky) would wash everything out.</summary>
        public static void ApplyAmbient(Color c)
        {
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = c;
            RenderSettings.ambientIntensity = 1f;
            var sh = new SphericalHarmonicsL2();
            sh.AddAmbientLight(c);
            RenderSettings.ambientProbe = sh;
            RenderSettings.reflectionIntensity = 0f;
        }

        void ApplyDifficulty()
        {
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = GameAssets.I.fogColor;
            RenderSettings.fogDensity = Diff == Difficulty.Hard ? GameAssets.I.fogDensityHard : GameAssets.I.fogDensity;
            ApplyAmbient(GameAssets.I.ambientColor * (Diff == Difficulty.Hard ? 0.65f : 1f));
            if (ambient != null) ambient.volume = Diff == Difficulty.Hard ? 0f : 0.35f;
            if (teacher != null) teacher.Configure(Diff);
        }

        IEnumerator IntroSeq()
        {
            State = GameState.Intro;
            skipIntro = false;
            ui.ShowIntro();
            Transform c = mainCam.transform;
            c.SetParent(null, true);
            Vector3 p0 = introCam.position + introCam.up * 0.25f - introCam.forward * 0.15f;
            Quaternion r0 = introCam.rotation * Quaternion.Euler(28f, -12f, 8f);
            Vector3 p1 = playerSpawn.position + Vector3.up * 1.62f;
            Quaternion r1 = playerSpawn.rotation;
            mainCam.fieldOfView = 58f;
            ui.FadeFrom(1f, 2.5f);
            Sfx.Play2D(GameAssets.I.bell, 0.55f);
            string[] lines =
            {
                "You fell asleep in class...",
                "It's night. Every door out is locked.",
                "And the teacher is still here.",
                "Get out without getting caught."
            };
            float t = 0f, dur = 9f;
            int shown = -1;
            while (t < dur && !skipIntro)
            {
                t += Time.deltaTime;
                float k = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(1.5f, dur - 0.5f, t));
                c.position = Vector3.Lerp(p0, p1, k);
                c.rotation = Quaternion.Slerp(r0, r1, k);
                int li = Mathf.Min(lines.Length - 1, (int)(t / (dur / lines.Length)));
                if (li != shown) { shown = li; ui.Subtitle(lines[li], 2.4f); }
                yield return null;
            }
            ui.Subtitle("", 0f);
            BeginPlay();
            ui.ShowDayCard(Day, MaxDays);
        }

        public void SkipIntro() { skipIntro = true; }

        void BeginPlay()
        {
            State = GameState.Playing;
            player.Spawn(playerSpawn.position, playerSpawn.eulerAngles.y);
            player.AttachCamera(mainCam.transform);
            player.SetActive(true);
            if (teacher != null) teacher.SetMenuMode(false);
            ui.ShowHud();
        }

        // ------------------------------------------------------------------ caught
        public void OnCaught()
        {
            if (State != GameState.Playing) return;
            StartCoroutine(CaughtSeq());
        }

        IEnumerator CaughtSeq()
        {
            State = GameState.Caught;
            Vector3 where = player.transform.position;
            if (player.Hidden) player.ForceUnhide();
            inventory.DropOnCatch(where);
            player.SetActive(false);
            ui.ShowNone();
            teacher.BeginJumpscare(mainCam);
            float t = 0f;
            Vector3 basePos = mainCam.transform.localPosition;
            while (t < 1.25f)
            {
                t += Time.deltaTime;
                float shake = Mathf.Lerp(0.035f, 0.005f, t / 1.25f);
                mainCam.transform.localPosition = basePos + Random.insideUnitSphere * shake;
                yield return null;
            }
            ui.FadeTo(1f, 0.35f);
            yield return new WaitForSeconds(0.6f);
            teacher.EndJumpscare();
            Day++;
            if (Day > MaxDays)
            {
                StartCoroutine(GameOverSeq());
                yield break;
            }
            teacher.ResetToSpawn();
            player.Spawn(playerSpawn.position, playerSpawn.eulerAngles.y);
            player.AttachCamera(mainCam.transform);
            ui.ShowDayCard(Day, MaxDays);
            Sfx.Play2D(GameAssets.I.bell, 0.6f);
            yield return new WaitForSeconds(1.2f);
            ui.FadeFrom(1f, 1.2f);
            State = GameState.Playing;
            player.SetActive(true);
            ui.ShowHud();
        }

        IEnumerator GameOverSeq()
        {
            State = GameState.GameOver;
            ui.ShowGameOver();
            ui.FadeFrom(1f, 1.5f);
            Sfx.Play2D(GameAssets.I.slam, 0.8f);
            yield break;
        }

        // ------------------------------------------------------------------ escape
        public void OnEscaped()
        {
            if (State != GameState.Playing) return;
            StartCoroutine(EscapeSeq());
        }

        IEnumerator EscapeSeq()
        {
            State = GameState.Escaped;
            player.SetActive(false);
            ui.ShowNone();
            if (teacher != null) teacher.Freeze();
            Transform c = mainCam.transform;
            c.SetParent(null, true);
            if (endingCamPoints != null && endingCamPoints.Length >= 2)
            {
                Vector3 sp = c.position;
                Quaternion sr = c.rotation;
                float t = 0f, dur = 7f;
                while (t < dur)
                {
                    t += Time.deltaTime;
                    float k = t / dur;
                    float f = k * (endingCamPoints.Length - 1);
                    int a = Mathf.Min(endingCamPoints.Length - 2, Mathf.FloorToInt(f));
                    float s = Mathf.SmoothStep(0f, 1f, f - a);
                    Vector3 pos = Vector3.Lerp(endingCamPoints[a].position, endingCamPoints[a + 1].position, s);
                    Quaternion rot = Quaternion.Slerp(endingCamPoints[a].rotation, endingCamPoints[a + 1].rotation, s);
                    float blend = Mathf.Clamp01(t / 1.2f);
                    c.position = Vector3.Lerp(sp, pos, blend);
                    c.rotation = Quaternion.Slerp(sr, rot, blend);
                    if (t > dur - 1.5f && t - Time.deltaTime <= dur - 1.5f) ui.FadeTo(1f, 1.4f);
                    yield return null;
                }
            }
            bool first = !HasEscapedBefore;
            PlayerPrefs.SetInt("nc_escaped", 1);
            PlayerPrefs.Save();
            ui.ShowEscaped(Day, first);
            ui.FadeFrom(1f, 1.2f);
        }

        // ------------------------------------------------------------------ pause / restart
        public void Pause()
        {
            if (State != GameState.Playing) return;
            State = GameState.Paused;
            Time.timeScale = 0f;
            AudioListener.pause = true;
            ui.ShowPause();
        }

        public void Resume()
        {
            if (State != GameState.Paused) return;
            State = GameState.Playing;
            Time.timeScale = 1f;
            AudioListener.pause = false;
            ui.ShowHud();
        }

        public void Restart()
        {
            AudioListener.pause = false;
            StartGame(Diff);
        }

        public void QuitToMenu()
        {
            AudioListener.pause = false;
            PendingStart = false;
            StartCoroutine(Reload());
        }

        public void Message(string text, float seconds = 3.5f)
        {
            if (ui != null) ui.Message(text, seconds);
        }

        // ------------------------------------------------------------------ music
        void Update()
        {
            if (State == GameState.Menu) UpdateMenuCamera();
            if (State == GameState.Intro && (Input.touchCount > 0 && Input.GetTouch(0).phase == TouchPhase.Began || Input.GetMouseButtonDown(0)))
                SkipIntro();

            bool playing = State == GameState.Playing;
            float chaseTarget = playing && teacher != null && teacher.IsChasing ? 0.7f : 0f;
            float heartTarget = 0f;
            if (playing && teacher != null && Diff != Difficulty.Ghost && teacher.IsActiveHunter)
            {
                float d = Vector3.Distance(teacher.transform.position, player.transform.position);
                heartTarget = Mathf.InverseLerp(10f, 2.5f, d) * 0.8f;
            }
            if (chase != null) chase.volume = Mathf.MoveTowards(chase.volume, chaseTarget, Time.unscaledDeltaTime * (chaseTarget > chase.volume ? 0.9f : 0.3f));
            if (heart != null) heart.volume = Mathf.MoveTowards(heart.volume, heartTarget, Time.unscaledDeltaTime * 0.8f);
        }
    }
}
