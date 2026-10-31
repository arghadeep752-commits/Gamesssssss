using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;

namespace RealFPS.EditorTools
{
    /// <summary>
    /// Command-line entry point used by CI:
    ///   Unity -batchmode -quit -buildTarget Android -executeMethod RealFPS.EditorTools.RFBuild.BuildAndroid
    /// Configures the project for mobile (linear lighting, HDR, ASTC), builds the
    /// scene from code and produces the APK.
    /// </summary>
    public static class RFBuild
    {
        const string IconPath = "Assets/Art/Icons/app_icon.png";
        public const string AppId = "com.silentvalley.fps";

        [MenuItem("Silent Valley/Build Android APK")]
        public static void BuildAndroid()
        {
            try
            {
                int buildNumber = Math.Max(1, ReadIntArg("-buildNumber", 1));
                string output = ReadArg("-outputPath", "Build/SilentValley.apk");
                Log("Preparing build " + buildNumber + " -> " + output);

                ConfigureProject();
                AssetDatabase.Refresh();
                RFArtInfo art = RFArtInfo.Load();
                RFWorld.Build(art);
                ConfigurePlayer(buildNumber);
                ConfigureIcon();
                AssetDatabase.SaveAssets();

                string dir = Path.GetDirectoryName(output);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                var options = new BuildPlayerOptions
                {
                    scenes = new[] { RFWorld.ScenePath },
                    locationPathName = output,
                    target = BuildTarget.Android,
                    targetGroup = BuildTargetGroup.Android,
                    options = BuildOptions.None
                };
                BuildReport report = BuildPipeline.BuildPlayer(options);
                BuildSummary s = report.summary;
                Log("result=" + s.result + " size=" + s.totalSize + " errors=" + s.totalErrors + " warnings=" + s.totalWarnings + " time=" + s.totalTime);
                if (s.result != BuildResult.Succeeded)
                {
                    foreach (BuildStep step in report.steps)
                        foreach (BuildStepMessage m in step.messages)
                            if (m.type == LogType.Error || m.type == LogType.Exception)
                                Debug.Log("[RF-ERR] " + step.name + ": " + m.content);
                    EditorApplication.Exit(2);
                }
            }
            catch (Exception e)
            {
                Debug.LogError("[RF-BUILD] Build script failed: " + e);
                EditorApplication.Exit(3);
            }
        }

        static void Log(string msg) { Debug.Log("[RF-BUILD] " + msg); }

        static string ReadArg(string name, string fallback)
        {
            string[] args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++) if (args[i] == name) return args[i + 1];
            return fallback;
        }

        static int ReadIntArg(string name, int fallback)
        {
            int v;
            return int.TryParse(ReadArg(name, ""), out v) ? v : fallback;
        }

        public static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            string leaf = Path.GetFileName(path);
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, leaf);
        }

        // ------------------------------------------------------------------ project settings
        static void ConfigureProject()
        {
            if (PlayerSettings.colorSpace != ColorSpace.Linear)
            {
                PlayerSettings.colorSpace = ColorSpace.Linear;
                Log("colour space -> linear");
            }
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            GraphicsSettings.lightsUseLinearIntensity = true;
            GraphicsSettings.lightsUseColorTemperature = false;
            EditorUserBuildSettings.androidBuildSubtarget = MobileTextureSubtarget.ASTC;

            foreach (GraphicsTier tier in new[] { GraphicsTier.Tier1, GraphicsTier.Tier2, GraphicsTier.Tier3 })
            {
                TierSettings ts = EditorGraphicsSettings.GetTierSettings(BuildTargetGroup.Android, tier);
                ts.renderingPath = RenderingPath.Forward;
                ts.hdr = true;
                ts.hdrMode = CameraHDRMode.R11G11B10;
                ts.standardShaderQuality = ShaderQuality.Medium;
                ts.cascadedShadowMaps = true;
                ts.reflectionProbeBoxProjection = false;
                ts.reflectionProbeBlending = false;
                ts.semitransparentShadows = false;
                ts.enableLPPV = false;
                ts.detailNormalMap = false;
                ts.prefer32BitShadowMaps = false;
                EditorGraphicsSettings.SetTierSettings(BuildTargetGroup.Android, tier, ts);
            }
            KeepFogVariants();
            PlayerSettings.bakeCollisionMeshes = true;
            Log("project configured");
        }

        static void KeepFogVariants()
        {
            try
            {
                UnityEngine.Object[] objs = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/GraphicsSettings.asset");
                if (objs == null || objs.Length == 0) return;
                var so = new SerializedObject(objs[0]);
                SetBool(so, "m_FogKeepLinear", false);
                SetBool(so, "m_FogKeepExp", true);
                SetBool(so, "m_FogKeepExp2", false);
                SerializedProperty strip = so.FindProperty("m_FogStripping");
                if (strip != null) strip.intValue = 1;
                SerializedProperty inst = so.FindProperty("m_InstancingStripping");
                if (inst != null) inst.intValue = 0; // strip unused
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            catch (Exception e)
            {
                Debug.LogWarning("[RF-BUILD] Could not change shader stripping: " + e.Message);
            }
        }

        static void SetBool(SerializedObject so, string name, bool value)
        {
            SerializedProperty p = so.FindProperty(name);
            if (p != null) p.boolValue = value;
        }

        // ------------------------------------------------------------------ player settings
        static void ConfigurePlayer(int buildNumber)
        {
            PlayerSettings.companyName = "SilentValley";
            PlayerSettings.productName = "Silent Valley";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, AppId);
            PlayerSettings.bundleVersion = "1.0." + buildNumber;
            PlayerSettings.Android.bundleVersionCode = buildNumber;

            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel22;
            PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevelAuto;
            PlayerSettings.stripEngineCode = false;
            PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Android, ManagedStrippingLevel.Low);
            PlayerSettings.MTRendering = true;
            PlayerSettings.Android.optimizedFramePacing = true;

            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.Android.startInFullscreen = true;
            PlayerSettings.Android.renderOutsideSafeArea = true;

            PlayerSettings.SplashScreen.backgroundColor = Color.black;
            PlayerSettings.SplashScreen.unityLogoStyle = PlayerSettings.SplashScreen.UnityLogoStyle.LightOnDark;

            EditorUserBuildSettings.buildAppBundle = false;
            EditorUserBuildSettings.androidBuildSystem = AndroidBuildSystem.Gradle;
            EditorUserBuildSettings.development = false;

            string keystore = Environment.GetEnvironmentVariable("RF_KEYSTORE");
            if (!string.IsNullOrEmpty(keystore) && File.Exists(keystore))
            {
                string pass = Environment.GetEnvironmentVariable("RF_KEYSTORE_PASS") ?? "";
                PlayerSettings.Android.useCustomKeystore = true;
                PlayerSettings.Android.keystoreName = keystore;
                PlayerSettings.Android.keystorePass = pass;
                PlayerSettings.Android.keyaliasName = Environment.GetEnvironmentVariable("RF_KEY_ALIAS") ?? "silentvalley";
                PlayerSettings.Android.keyaliasPass = pass;
                Log("signing with the project keystore");
            }
            else
            {
                PlayerSettings.Android.useCustomKeystore = false;
                Log("signing with the debug keystore");
            }
        }

        static void ConfigureIcon()
        {
            var icon = AssetDatabase.LoadAssetAtPath<Texture2D>(IconPath);
            if (icon == null)
            {
                Debug.LogWarning("[RF-BUILD] App icon not found at " + IconPath);
                return;
            }
            PlayerSettings.SetIconsForTargetGroup(BuildTargetGroup.Unknown, new[] { icon });
            Log("app icon set");
        }
    }
}
