using UnityEngine;

namespace RealFPS
{
    /// <summary>
    /// Detects software GPUs (the Android emulator's SwiftShader, llvmpipe). They cannot run
    /// GPU-instanced shaders because their uniform limits are tiny, so on them everything is
    /// drawn without instancing. Real phone GPUs (Mali, Adreno, PowerVR, Xclipse) keep the fast
    /// instanced path.
    /// </summary>
    public static class RenderCompat
    {
        static int software = -1;

        public static bool SoftwareGpu
        {
            get
            {
                if (software < 0)
                {
                    string gpu = (SystemInfo.graphicsDeviceName + " " + SystemInfo.graphicsDeviceVendor + " " + SystemInfo.graphicsDeviceVersion).ToLowerInvariant();
                    bool soft = gpu.Contains("swiftshader") || gpu.Contains("android emulator") || gpu.Contains("translator") ||
                                gpu.Contains("llvmpipe") || gpu.Contains("softpipe");
                    software = soft ? 1 : 0;
                }
                return software == 1;
            }
        }

        /// <summary>GPU instancing is used for trees and terrain unless the GPU cannot handle it.</summary>
        public static bool UseInstancing
        {
            get { return SystemInfo.supportsInstancing && !SoftwareGpu; }
        }

        public static string Describe()
        {
            return SystemInfo.graphicsDeviceName + " | " + SystemInfo.graphicsDeviceVersion + " | " + SystemInfo.graphicsDeviceType +
                   " | RAM " + SystemInfo.systemMemorySize + " MB | CPU " + SystemInfo.processorCount + "x " + SystemInfo.processorFrequency + " MHz" +
                   " | screen " + Screen.width + "x" + Screen.height + " | instancing " + (UseInstancing ? "on" : "off");
        }
    }
}
