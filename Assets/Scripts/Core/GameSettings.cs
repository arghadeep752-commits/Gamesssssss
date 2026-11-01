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

        /// <summary>
        /// A sensible starting level from the phone's GPU and memory (the player can change it
        /// in Settings). Entry-level GPUs such as the Mali-G52 in the Galaxy A21s start on Low,
        /// mid-range GPUs on Medium, recent flagship GPUs with plenty of memory on High.
        /// </summary>
        public static GraphicsLevel DefaultLevel()
        {
            int ram = SystemInfo.systemMemorySize;        // MB
            string gpu = (SystemInfo.graphicsDeviceName ?? "").ToLowerInvariant();
            if (ram > 0 && ram < 3000) return GraphicsLevel.Low;
            int tier = GpuTier(gpu);
            if (tier <= 0) return GraphicsLevel.Low;
            if (tier >= 2 && ram >= 5500) return GraphicsLevel.High;
            return GraphicsLevel.Medium;
        }

        /// <summary>0 = entry level, 1 = mid range, 2 = high end (unknown GPUs count as mid range).</summary>
        public static int GpuTier(string gpu)
        {
            int n = NumberAfter(gpu, "adreno");
            if (n > 0)
            {
                if (n >= 650) return 2;                       // Snapdragon 865 and newer
                if (n >= 618) return 1;                       // Snapdragon 7xx-class
                return 0;                                     // Adreno 3xx-5xx, 610/612/613
            }
            if (gpu.Contains("immortalis") || gpu.Contains("xclipse")) return 2;
            if (gpu.Contains("mali"))
            {
                int g = NumberAfter(gpu, "mali-g");
                if (g <= 0) return 0;                         // Mali-4xx / T-series
                if (g >= 710 || g == 77 || g == 78) return 2;
                if (g == 31 || g == 51 || g == 52) return 0;  // e.g. Galaxy A21s (Mali-G52 MP1)
                return 1;                                     // G57, G68, G72, G76 ...
            }
            if (gpu.Contains("powervr") || gpu.Contains("ge8") || gpu.Contains("img bxm")) return 0;
            return 1;
        }

        static int NumberAfter(string s, string key)
        {
            int i = s.IndexOf(key, System.StringComparison.Ordinal);
            if (i < 0) return 0;
            i += key.Length;
            int limit = Mathf.Min(s.Length, i + 8);
            while (i < limit && !char.IsDigit(s[i])) i++;
            int v = 0, digits = 0;
            while (i < s.Length && char.IsDigit(s[i]) && digits < 4)
            {
                v = v * 10 + (s[i] - '0');
                i++;
                digits++;
            }
            return v;
        }
    }
}
