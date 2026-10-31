using System.Collections;
using UnityEngine;

namespace RealFPS
{
    public enum GameState { Menu, Playing, Paused }

    /// <summary>
    /// Game flow: main menu (cinematic camera) -> playing -> paused, plus the
    /// lantern objective. Lives on the "Game" object the build script creates.
    /// </summary>
    public class Game : MonoBehaviour
    {
        public static Game I { get; private set; }

        [Header("Scene references (set by the build script)")]
        public FPController player;
        public Camera mainCamera;
        public Transform spawnPoint;
        public CinematicCamera menuCamera;
        public Lantern[] lanterns;
        public QualityManager quality;
        public AmbientAudio ambientAudio;
        public Transform[] tourPoints;
        public float lanternPickupRange = 2.6f;

        public GameState State { get; private set; } = GameState.Menu;
        public int LanternsFound { get; private set; }
        public int LanternCount { get { return lanterns != null ? lanterns.Length : 0; } }

        UIRoot ui;
        bool tour;

        void Awake()
        {
            I = this;
            Input.multiTouchEnabled = true;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            GameSettings.Load();
            AudioListener.volume = GameSettings.Volume;
        }

        void Start()
        {
            if (quality != null) quality.Apply();
            GameSettings.Changed += OnSettingsChanged;
            ui = gameObject.AddComponent<UIRoot>();
            ui.Build(this);
            EnterMenu(true);
            tour = DebugTour.Requested();
            if (tour) gameObject.AddComponent<DebugTour>();
            StartCoroutine(ReportLayout());
        }

        void OnDestroy()
        {
            GameSettings.Changed -= OnSettingsChanged;
        }

        void OnSettingsChanged()
        {
            if (quality != null) quality.Apply();
            AudioListener.volume = GameSettings.Volume;
            if (player != null) player.ApplySettings();
        }

        IEnumerator ReportLayout()
        {
            // Used by the automated emulator test to find the buttons.
            for (int i = 0; i < 3; i++) yield return null;
            Debug.Log("[RF] LAYOUT " + ui.LayoutReport());
        }

        public void EnterMenu(bool first)
        {
            State = GameState.Menu;
            Time.timeScale = 1f;
            if (player != null) player.SetActive(false);
            if (menuCamera != null)
            {
                mainCamera.transform.SetParent(null, true);
                menuCamera.Begin(mainCamera.transform, first);
            }
            ui.ShowMenu();
        }

        public void StartGame()
        {
            StartCoroutine(StartGameRoutine());
        }

        IEnumerator StartGameRoutine()
        {
            yield return ui.Fade(1f, 0.45f);
            if (menuCamera != null) menuCamera.Stop();
            player.Spawn(spawnPoint.position, spawnPoint.eulerAngles.y);
            player.AttachCamera(mainCamera.transform);
            player.SetActive(true);
            State = GameState.Playing;
            ui.ShowHud();
            yield return ui.Fade(0f, 0.6f);
            ui.Hud.ShowHint("Left side: move  •  Right side: look around", 6f);
        }

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

        public void QuitToMenu()
        {
            AudioListener.pause = false;
            StartCoroutine(QuitRoutine());
        }

        IEnumerator QuitRoutine()
        {
            Time.timeScale = 1f;
            yield return ui.Fade(1f, 0.4f);
            EnterMenu(false);
            yield return ui.Fade(0f, 0.6f);
        }

        public void OnLanternFound(Lantern l)
        {
            LanternsFound++;
            ui.Hud.UpdateObjective();
            if (LanternsFound >= LanternCount)
            {
                Sfx.Play2D(GameAssets.I.complete, 0.9f);
                ui.Hud.ShowToast("All lanterns found!", "The valley is yours to explore", 5f);
            }
            else
            {
                Sfx.Play2D(GameAssets.I.pickup, 0.8f);
                ui.Hud.ShowToast("Lantern found", LanternsFound + " of " + LanternCount, 2.6f);
            }
        }

        void OnApplicationPause(bool paused)
        {
            if (paused && State == GameState.Playing && !tour) Pause();
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape))
            {
                if (State == GameState.Playing) Pause();
                else if (State == GameState.Paused) Resume();
            }
            if (State == GameState.Playing && player != null && lanterns != null && ui != null)
            {
                Lantern near = null;
                float best = lanternPickupRange;
                Vector3 p = player.transform.position + Vector3.up * 0.9f;
                foreach (Lantern l in lanterns)
                {
                    if (l == null || l.Collected) continue;
                    float d = Vector3.Distance(p, l.transform.position);
                    if (d < best) { best = d; near = l; }
                }
                ui.Hud.SetInteract(near != null, "PICK UP");
                bool pressed = TouchControls.I != null && TouchControls.I.ConsumeInteract();
                if (near != null && pressed) near.Collect();
            }
        }
    }
}
