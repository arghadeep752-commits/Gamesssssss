using UnityEngine;

namespace RealFPS
{
    public enum GraphicsLevel { Low = 0, Medium = 1, High = 2 }

    /// <summary>Player options, saved with PlayerPrefs.</summary>
    public static class GameSettings
    {
        const string Prefix = "rf_";

        public static GraphicsLevel Graphics;
        public static float LookSensitivity;   // 0.3 .. 2.5
        public static float FieldOfView;       // vertical degrees
        public static bool InvertY;
        public static bool HeadBob;
        public static bool ShowFps;
        public static bool Fps60;
        public static float Volume;

        public static System.Action Changed;

        public static void Load()
        {
            int defLevel = (int)DefaultLevel();
            Graphics = (GraphicsLevel)Mathf.Clamp(PlayerPrefs.GetInt(Prefix + "gfx", defLevel), 0, 2);
            LookSensitivity = PlayerPrefs.GetFloat(Prefix + "sens", 1.0f);
            FieldOfView = PlayerPrefs.GetFloat(Prefix + "fov", 58f);
            InvertY = PlayerPrefs.GetInt(Prefix + "invy", 0) == 1;
            HeadBob = PlayerPrefs.GetInt(Prefix + "bob", 1) == 1;
            ShowFps = PlayerPrefs.GetInt(Prefix + "fps", 0) == 1;
            Fps60 = PlayerPrefs.GetInt(Prefix + "fps60", Graphics == GraphicsLevel.High ? 1 : 0) == 1;
            Volume = PlayerPrefs.GetFloat(Prefix + "vol", 1f);
        }

        public static void Save()
        {
            PlayerPrefs.SetInt(Prefix + "gfx", (int)Graphics);
            PlayerPrefs.SetFloat(Prefix + "sens", LookSensitivity);
            PlayerPrefs.SetFloat(Prefix + "fov", FieldOfView);
            PlayerPrefs.SetInt(Prefix + "invy", InvertY ? 1 : 0);
            PlayerPrefs.SetInt(Prefix + "bob", HeadBob ? 1 : 0);
            PlayerPrefs.SetInt(Prefix + "fps", ShowFps ? 1 : 0);
            PlayerPrefs.SetInt(Prefix + "fps60", Fps60 ? 1 : 0);
            PlayerPrefs.SetFloat(Prefix + "vol", Volume);
            PlayerPrefs.Save();
            if (Changed != null) Changed();
        }

        /// <summary>A sensible starting level from the device's memory and GPU.</summary>
        public static GraphicsLevel DefaultLevel()
        {
            int ram = SystemInfo.systemMemorySize;        // MB
            int vram = SystemInfo.graphicsMemorySize;     // MB (often unknown on Android)
            string gpu = (SystemInfo.graphicsDeviceName ?? "").ToLowerInvariant();
            if (ram > 0 && ram < 2600) return GraphicsLevel.Low;
            bool strongGpu = gpu.Contains("adreno (tm) 7") || gpu.Contains("adreno (tm) 6") && !gpu.Contains("adreno (tm) 610") && !gpu.Contains("adreno (tm) 612")
                             || gpu.Contains("mali-g7") || gpu.Contains("mali-g6") || gpu.Contains("xclipse") || gpu.Contains("immortalis");
            if (strongGpu && ram >= 5500) return GraphicsLevel.High;
            return GraphicsLevel.Medium;
        }
    }
}
