using UnityEngine;

namespace ZombieStrike
{
    public enum GameState { Menu, Playing, Paused, GameOver }

    public enum ZombieKind { Walker, Runner, Brute }

    public enum PickupKind { Ammo, Health }

    /// <summary>Physics / render layers (user layers need no names to work).</summary>
    public static class Layers
    {
        public const int Default = 0;
        public const int Weapon = 8;
        public const int Zombie = 9;
        public const int Player = 10;

        public static int ShootMask { get { return (1 << Default) | (1 << Zombie); } }
    }

    /// <summary>Saved settings and records.</summary>
    public static class Settings
    {
        const string SensKey = "zs_look_speed";
        const string BestScoreKey = "zs_best_score";
        const string BestWaveKey = "zs_best_wave";

        public static float LookSpeed
        {
            get { return PlayerPrefs.GetFloat(SensKey, 1f); }
            set
            {
                PlayerPrefs.SetFloat(SensKey, Mathf.Clamp(value, 0.4f, 2.5f));
                PlayerPrefs.Save();
            }
        }

        public static int BestScore { get { return PlayerPrefs.GetInt(BestScoreKey, 0); } }
        public static int BestWave { get { return PlayerPrefs.GetInt(BestWaveKey, 0); } }

        /// <returns>true when the score is a new record.</returns>
        public static bool SubmitRun(int score, int wave)
        {
            bool record = score > BestScore;
            if (record) PlayerPrefs.SetInt(BestScoreKey, score);
            if (wave > BestWave) PlayerPrefs.SetInt(BestWaveKey, wave);
            PlayerPrefs.Save();
            return record;
        }
    }

    public static class Ease
    {
        public static float OutCubic(float t)
        {
            t = Mathf.Clamp01(t);
            float u = 1f - t;
            return 1f - u * u * u;
        }

        public static float InQuad(float t)
        {
            t = Mathf.Clamp01(t);
            return t * t;
        }

        public static float OutBack(float t)
        {
            t = Mathf.Clamp01(t);
            const float c1 = 1.70158f;
            const float c3 = c1 + 1f;
            float u = t - 1f;
            return 1f + c3 * u * u * u + c1 * u * u;
        }
    }

    /// <summary>Makes sure the game starts even if the scene object were missing.</summary>
    public static class Bootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void EnsureGame()
        {
            if (Object.FindObjectOfType<GameManager>() == null)
            {
                new GameObject("Game").AddComponent<GameManager>();
            }
        }
    }
}
