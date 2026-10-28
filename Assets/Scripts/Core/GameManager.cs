using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ZombieStrike
{
    /// <summary>
    /// Entry point (lives on the "Game" object in the scene). Builds the world, the player and the UI,
    /// and runs the menu / playing / paused / game-over flow.
    /// </summary>
    public class GameManager : MonoBehaviour
    {
        public static GameManager I { get; private set; }
        static bool skipMenu;

        public GameState State { get; private set; }
        public int Score { get; private set; }
        public int Kills { get; private set; }
        public int Headshots { get; private set; }
        public WaveSpawner Waves { get; private set; }

        LevelBuilder level;
        HUD hud;
        TouchControls controls;
        PlayerController player;

        void Awake()
        {
            if (I != null && I != this)
            {
                Destroy(gameObject);
                return;
            }
            I = this;
            Zombie.All.Clear();
            Pickup.All.Clear();
            Time.timeScale = 1f;
            AudioListener.pause = false;

            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 0;
            QualitySettings.shadows = ShadowQuality.Disable;
            QualitySettings.pixelLightCount = 1;
            QualitySettings.antiAliasing = 0;
            QualitySettings.anisotropicFiltering = AnisotropicFiltering.Disable;
            QualitySettings.softParticles = false;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            Screen.autorotateToPortrait = false;
            Screen.autorotateToPortraitUpsideDown = false;
            Screen.autorotateToLandscapeLeft = true;
            Screen.autorotateToLandscapeRight = true;
            Screen.orientation = ScreenOrientation.AutoRotation;
            Input.multiTouchEnabled = true;
            Input.simulateMouseWithTouches = false;

            float t0 = Time.realtimeSinceStartup;
            Art.Init();
            gameObject.AddComponent<Sfx>();
            gameObject.AddComponent<Fx>();
            controls = gameObject.AddComponent<TouchControls>();
            level = gameObject.AddComponent<LevelBuilder>();
            level.Build();
            player = PlayerController.Create(level.PlayerStart, level.PlayerYaw);
            hud = gameObject.AddComponent<HUD>();
            hud.Build();
            Waves = gameObject.AddComponent<WaveSpawner>();
            Waves.Init(level.SpawnPoints, level.HasNavMesh);
            Debug.Log("[ZS] world built in " + Mathf.RoundToInt((Time.realtimeSinceStartup - t0) * 1000f) + " ms, screen " +
                      Screen.width + "x" + Screen.height);
        }

        void Start()
        {
            if (Sfx.I != null) Sfx.I.StartAmbience();
            if (skipMenu)
            {
                skipMenu = false;
                StartGame();
            }
            else
            {
                SetState(GameState.Menu);
            }
            Debug.Log("ZS-READY");
        }

        void SetState(GameState s)
        {
            State = s;
            controls.Active = s == GameState.Playing;
            hud.SetState(s);
        }

        public void StartGame()
        {
            if (State == GameState.Playing) return;
            Score = 0;
            Kills = 0;
            Headshots = 0;
            SetState(GameState.Playing);
            Waves.Begin();
            hud.ShowBanner("GET READY", "The dead are coming...", Color.white, 2.3f);
        }

        public void Pause()
        {
            if (State != GameState.Playing) return;
            SetState(GameState.Paused);
            Time.timeScale = 0f;
            AudioListener.pause = true;
        }

        public void Resume()
        {
            if (State != GameState.Paused) return;
            Time.timeScale = 1f;
            AudioListener.pause = false;
            SetState(GameState.Playing);
        }

        public void Restart()
        {
            skipMenu = true;
            ReloadScene();
        }

        public void GoToMenu()
        {
            skipMenu = false;
            ReloadScene();
        }

        void ReloadScene()
        {
            Time.timeScale = 1f;
            AudioListener.pause = false;
            SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
        }

        public void OnWaveStarted(int wave)
        {
            string sub = wave == 1 ? "Survive!" : (wave % 3 == 0 ? "A brute is coming..." : "They're getting stronger...");
            hud.ShowBanner("WAVE " + wave, sub, new Color(0.95f, 0.15f, 0.1f), 2.6f);
            if (Sfx.I != null) Sfx.I.Play2D("wave_start", 0.9f);
            if (wave > 1 && player.Gun != null) player.Gun.AddReserve(30);
        }

        public void OnWaveCleared(int wave)
        {
            int bonus = 250 * wave;
            Score += bonus;
            player.Heal(20f);
            hud.ShowBanner("WAVE " + wave + " CLEARED", "+" + bonus + " BONUS   •   +20 HEALTH", new Color(0.4f, 1f, 0.5f), 3.2f);
            if (Sfx.I != null) Sfx.I.Play2D("wave_clear", 0.8f);
        }

        public void OnZombieKilled(Zombie z, bool headshot)
        {
            Kills++;
            int points = z.Kind == ZombieKind.Brute ? 500 : (z.Kind == ZombieKind.Runner ? 150 : 100);
            if (headshot)
            {
                points += 50;
                Headshots++;
            }
            Score += points;
            hud.Popup(headshot ? "HEADSHOT  +" + points : "+" + points,
                headshot ? new Color(1f, 0.35f, 0.25f) : new Color(1f, 0.82f, 0.3f));
        }

        public void OnPlayerDied()
        {
            if (State != GameState.Playing) return;
            StartCoroutine(GameOverSequence());
        }

        IEnumerator GameOverSequence()
        {
            State = GameState.GameOver;
            controls.Active = false;
            Time.timeScale = 0.4f;
            if (Sfx.I != null) Sfx.I.Play2D("game_over", 0.9f);
            yield return new WaitForSecondsRealtime(1.8f);
            Time.timeScale = 0f;
            int wave = Waves.Wave;
            bool record = Settings.SubmitRun(Score, wave);
            Weapon gun = player.Gun;
            float accuracy = gun != null && gun.ShotsFired > 0 ? (float)gun.ShotsHit / gun.ShotsFired : 0f;
            hud.ShowGameOver(wave, Kills, Headshots, Score, accuracy, record);
            hud.SetState(GameState.GameOver);
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape))
            {
                if (State == GameState.Playing) Pause();
                else if (State == GameState.Paused) Resume();
                else if (State == GameState.Menu) Application.Quit();
            }
        }

        void OnApplicationPause(bool paused)
        {
            if (paused && State == GameState.Playing) Pause();
        }
    }
}
