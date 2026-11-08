using UnityEngine;

namespace GridProto
{
    /// <summary>Player options, saved on the phone.</summary>
    public static class GameSettings
    {
        public static float Sensitivity = 1f;
        public static bool HighQuality = true;
        public static bool ShowFps = true;

        public static void Load()
        {
            Sensitivity = Mathf.Clamp(PlayerPrefs.GetFloat("gp_sensitivity", 1f), 0.2f, 3f);
            HighQuality = PlayerPrefs.GetInt("gp_high_quality", 1) == 1;
            ShowFps = PlayerPrefs.GetInt("gp_show_fps", 1) == 1;
        }

        public static void Save()
        {
            PlayerPrefs.SetFloat("gp_sensitivity", Sensitivity);
            PlayerPrefs.SetInt("gp_high_quality", HighQuality ? 1 : 0);
            PlayerPrefs.SetInt("gp_show_fps", ShowFps ? 1 : 0);
            PlayerPrefs.Save();
        }
    }
}
