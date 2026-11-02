using UnityEngine;

namespace NightClass
{
    public enum GraphicsLevel { Low = 0, Medium = 1, High = 2 }

    /// <summary>Player preferences (saved with PlayerPrefs).</summary>
    public static class GameSettings
    {
        public static GraphicsLevel Graphics;
        public static bool GraphicsChosen;
        public static float LookSensitivity;   // 0.3 .. 2.5
        public static float FieldOfView;       // vertical degrees
        public static bool HeadBob;
        public static bool Fps60;
        public static float Volume;
        static bool loaded;

        public static void Load()
        {
            if (loaded) return;
            loaded = true;
            GraphicsChosen = PlayerPrefs.HasKey("nc_gfx");
            Graphics = (GraphicsLevel)PlayerPrefs.GetInt("nc_gfx", (int)DefaultLevel());
            LookSensitivity = PlayerPrefs.GetFloat("nc_sens", 1f);
            FieldOfView = PlayerPrefs.GetFloat("nc_fov", 64f);
            HeadBob = PlayerPrefs.GetInt("nc_bob", 1) == 1;
            Fps60 = PlayerPrefs.GetInt("nc_fps60", 1) == 1;
            Volume = PlayerPrefs.GetFloat("nc_vol", 1f);
            Apply();
        }

        public static void Save()
        {
            PlayerPrefs.SetInt("nc_gfx", (int)Graphics);
            PlayerPrefs.SetFloat("nc_sens", LookSensitivity);
            PlayerPrefs.SetFloat("nc_fov", FieldOfView);
            PlayerPrefs.SetInt("nc_bob", HeadBob ? 1 : 0);
            PlayerPrefs.SetInt("nc_fps60", Fps60 ? 1 : 0);
            PlayerPrefs.SetFloat("nc_vol", Volume);
            PlayerPrefs.Save();
            GraphicsChosen = true;
            Apply();
        }

        public static void Apply()
        {
            Application.targetFrameRate = Fps60 ? 60 : 30;
            AudioListener.volume = Volume;
        }

        /// <summary>Picks a starting graphics profile from the GPU and memory.</summary>
        public static GraphicsLevel DefaultLevel()
        {
            int mem = SystemInfo.systemMemorySize;
            int tier = GpuTier(SystemInfo.graphicsDeviceName);
            if (tier >= 2 && mem >= 6000) return GraphicsLevel.High;
            if (tier >= 1 && mem >= 3500) return GraphicsLevel.Medium;
            return GraphicsLevel.Low;
        }

        /// <summary>0 = entry level (Mali-G52 / Adreno 50x class), 1 = mid range, 2 = high end.</summary>
        public static int GpuTier(string gpu)
        {
            if (string.IsNullOrEmpty(gpu)) return 0;
            string g = gpu.ToLowerInvariant();
            if (g.Contains("adreno"))
            {
                int n = Number(g);
                if (n >= 730) return 2;
                if (n >= 618) return 1;
                return 0;
            }
            if (g.Contains("mali"))
            {
                if (g.Contains("g7") || g.Contains("immortalis") || g.Contains("g610") || g.Contains("g615")) return g.Contains("g71") || g.Contains("g72") ? 0 : 2;
                if (g.Contains("g57") || g.Contains("g68") || g.Contains("g77") || g.Contains("g78")) return 1;
                return 0;
            }
            if (g.Contains("xclipse") || g.Contains("apple")) return 2;
            if (g.Contains("powervr")) return 0;
            return 1;
        }

        static int Number(string s)
        {
            int best = 0, cur = 0;
            foreach (char c in s)
            {
                if (char.IsDigit(c)) { cur = cur * 10 + (c - '0'); if (cur > best) best = cur; }
                else cur = 0;
            }
            return best;
        }
    }
}
