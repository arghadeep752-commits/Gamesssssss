using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;

namespace RealFPS.EditorTools
{
    /// <summary>
    /// Command-line entry point used by CI (Unity 6, Universal Render Pipeline):
    ///   Unity -batchmode -quit -buildTarget Android -executeMethod RealFPS.EditorTools.RFBuild.BuildAndroid
    /// Configures the project for mobile (linear lighting, URP with three graphics profiles,
    /// ASTC textures), builds the scene from code and produces the APK.
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
                // CI runners set UNITY_THISISABUILDMACHINE; with it, Unity 6's Android build adds
                // Unity's own private Maven mirrors to Gradle, which cannot be reached from here.
                if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("UNITY_THISISABUILDMACHINE")))
                {
                    Environment.SetEnvironmentVariable("UNITY_THISISABUILDMACHINE", null);
                    Log("cleared UNITY_THISISABUILDMACHINE (keeps Gradle on the public Google / Maven Central repositories)");
                }
                int buildNumber = Math.Max(1, ReadIntArg("-buildNumber", 1));
                string output = ReadArg("-outputPath", "Build/SilentValley.apk");
                Log("Preparing build " + buildNumber + " -> " + output);

                ConfigureProject();
                RFRenderSetup.Setup();
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
            // OpenGL ES 3 is the most compatible API on older Mali / Adreno phones (Galaxy A21s
            // class); the forest is GPU-instanced, so the draw-call count stays low anyway.
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            GraphicsSettings.lightsUseLinearIntensity = true;
            GraphicsSettings.lightsUseColorTemperature = false;
            EditorUserBuildSettings.androidBuildSubtarget = MobileTextureSubtarget.ASTC;
            KeepFogVariants();
            SetPlayerSetting("activeInputHandler", 0);   // classic touch input (Input Manager)
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

        static void SetPlayerSetting(string name, int value)
        {
            try
            {
                UnityEngine.Object[] objs = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
                if (objs == null || objs.Length == 0) return;
                var so = new SerializedObject(objs[0]);
                SerializedProperty p = so.FindProperty(name);
                if (p == null) { Debug.LogWarning("[RF-BUILD] player setting not found: " + name); return; }
                p.intValue = value;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            catch (Exception e)
            {
                Debug.LogWarning("[RF-BUILD] Could not set " + name + ": " + e.Message);
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
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, AppId);
            PlayerSettings.bundleVersion = "1.0." + buildNumber;
            PlayerSettings.Android.bundleVersionCode = buildNumber;

            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel23;
            PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevelAuto;
            PlayerSettings.Android.applicationEntry = AndroidApplicationEntry.Activity;
            PlayerSettings.stripEngineCode = false;
            PlayerSettings.SetManagedStrippingLevel(NamedBuildTarget.Android, ManagedStrippingLevel.Low);
            PlayerSettings.SetIl2CppCompilerConfiguration(NamedBuildTarget.Android, Il2CppCompilerConfiguration.Release);
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
            PlayerSettings.SplashScreen.show = false;

            EditorUserBuildSettings.buildAppBundle = false;
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
            PlayerSettings.SetIcons(NamedBuildTarget.Unknown, new[] { icon }, IconKind.Any);
            Log("app icon set");
        }
    }
}
