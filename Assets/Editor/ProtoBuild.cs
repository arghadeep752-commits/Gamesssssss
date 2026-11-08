using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace GridProto.EditorTools
{
    /// <summary>
    /// Project settings + Android build. Used by the cloud build:
    ///   Unity -batchmode -buildTarget Android -executeMethod GridProto.EditorTools.ProtoBuild.BuildAndroid -buildNumber N [-testApk path]
    /// and by the "Grid Prototype" menu when the project is opened in the Unity editor.
    /// </summary>
    public static class ProtoBuild
    {
        public const string ApplicationId = "com.gridprototype.fps";
        const string DefaultApk = "Build/GridPrototype.apk";

        [MenuItem("Grid Prototype/Rebuild Scene")]
        public static void RebuildSceneMenu()
        {
            ConfigureProject(1);
            string scene = ProtoSceneBuilder.Build();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scene, true) };
        }

        [MenuItem("Grid Prototype/Build Android APK")]
        public static void BuildMenu()
        {
            Build(1, DefaultApk, null);
        }

        /// <summary>Command-line entry point for the cloud build.</summary>
        public static void BuildAndroid()
        {
            int exitCode = 1;
            try
            {
                Application.SetStackTraceLogType(LogType.Log, StackTraceLogType.None);
                string[] args = System.Environment.GetCommandLineArgs();
                int buildNumber = 1;
                string output = DefaultApk;
                string testApk = null;
                for (int i = 0; i < args.Length - 1; i++)
                {
                    if (args[i] == "-buildNumber") int.TryParse(args[i + 1], out buildNumber);
                    else if (args[i] == "-outputApk") output = args[i + 1];
                    else if (args[i] == "-testApk") testApk = args[i + 1];
                }
                exitCode = Build(buildNumber, output, testApk) ? 0 : 1;
            }
            catch (System.Exception e)
            {
                Debug.LogError("[PROTO-ERR] build script crashed: " + e);
                exitCode = 1;
            }
            EditorApplication.Exit(exitCode);
        }

        static bool Build(int buildNumber, string output, string testApk)
        {
            Debug.Log("[PROTO] Unity " + Application.unityVersion + ", build " + buildNumber);
            ConfigureProject(buildNumber);
            ConfigureQuality();
            string scene = ProtoSceneBuilder.Build();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scene, true) };
            AssetDatabase.SaveAssets();

            bool ok = BuildApk(scene, output, false);
            if (ok && !string.IsNullOrEmpty(testApk))
            {
                // extra x86_64 APK with the auto-test compiled in, only for the emulator check (never published)
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.X86_64;
                bool testOk = BuildApk(scene, testApk, true);
                if (!testOk) Debug.LogWarning("[PROTO] emulator test APK failed to build (the phone APK is fine)");
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            }
            return ok;
        }

        static void ConfigureProject(int buildNumber)
        {
            PlayerSettings.companyName = "Grid Prototype";
            PlayerSettings.productName = "Grid Prototype";
            PlayerSettings.bundleVersion = "0.1." + buildNumber;
            PlayerSettings.Android.bundleVersionCode = Mathf.Max(1, buildNumber);
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, ApplicationId);
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.colorSpace = ColorSpace.Linear;

            // landscape only, either way round
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.useAnimatedAutorotation = true;

            // full screen edge to edge (around the camera hole too); the game renders at native resolution
            PlayerSettings.Android.renderOutsideSafeArea = true;
            PlayerSettings.SplashScreen.show = false;
            PlayerSettings.SplashScreen.showUnityLogo = false;
            EditorUserBuildSettings.buildAppBundle = false;

            UseLegacyInputManager();

            string keystore = System.Environment.GetEnvironmentVariable("PROTO_KEYSTORE");
            if (!string.IsNullOrEmpty(keystore) && File.Exists(keystore))
            {
                string pass = System.Environment.GetEnvironmentVariable("PROTO_KEYSTORE_PASS");
                PlayerSettings.Android.useCustomKeystore = true;
                PlayerSettings.Android.keystoreName = keystore;
                PlayerSettings.Android.keystorePass = pass;
                PlayerSettings.Android.keyaliasName = System.Environment.GetEnvironmentVariable("PROTO_KEY_ALIAS");
                PlayerSettings.Android.keyaliasPass = pass;
                Debug.Log("[PROTO] signing with the project keystore");
            }
            else
            {
                PlayerSettings.Android.useCustomKeystore = false;
                Debug.Log("[PROTO] signing with a debug key");
            }
        }

        // the touch controls read UnityEngine.Input, so make sure the classic input manager is active
        static void UseLegacyInputManager()
        {
            Object[] assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
            if (assets == null || assets.Length == 0) return;
            var settings = new SerializedObject(assets[0]);
            SerializedProperty handler = settings.FindProperty("activeInputHandler");
            if (handler == null)
            {
                Debug.Log("[PROTO] activeInputHandler setting not found");
                return;
            }
            Debug.Log("[PROTO] active input handler: " + handler.intValue);
            if (handler.intValue != 0)
            {
                handler.intValue = 0;
                settings.ApplyModifiedPropertiesWithoutUndo();
                Debug.Log("[PROTO] switched to the classic input manager");
            }
        }

        // every quality level gets the same phone-friendly but sharp settings (the game fine-tunes them at runtime)
        static void ConfigureQuality()
        {
            int current = QualitySettings.GetQualityLevel();
            string[] names = QualitySettings.names;
            for (int i = 0; i < names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.antiAliasing = 4;
                QualitySettings.shadows = UnityEngine.ShadowQuality.All;
                QualitySettings.shadowResolution = UnityEngine.ShadowResolution.High;
                QualitySettings.shadowDistance = 45f;
                QualitySettings.shadowCascades = 1;
                QualitySettings.shadowProjection = ShadowProjection.StableFit;
                QualitySettings.pixelLightCount = 2;
                QualitySettings.anisotropicFiltering = AnisotropicFiltering.ForceEnable;
                QualitySettings.realtimeReflectionProbes = true;
                QualitySettings.vSyncCount = 0;
                QualitySettings.lodBias = 2f;
                QualitySettings.softParticles = false;
                QualitySettings.skinWeights = SkinWeights.FourBones;
            }
            QualitySettings.SetQualityLevel(current, false);
            Debug.Log("[PROTO] quality levels: " + string.Join(", ", names) + " (current " + current + ")");
        }

        static bool BuildApk(string scene, string output, bool autoTest)
        {
            string dir = Path.GetDirectoryName(Path.GetFullPath(output));
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            var options = new BuildPlayerOptions
            {
                scenes = new[] { scene },
                locationPathName = output,
                target = BuildTarget.Android,
                targetGroup = BuildTargetGroup.Android,
                options = BuildOptions.None,
            };
            if (autoTest) options.extraScriptingDefines = new[] { "PROTO_AUTOTEST" };

            BuildReport report = BuildPipeline.BuildPlayer(options);
            BuildSummary summary = report.summary;
            Debug.Log("[PROTO] " + output + ": " + summary.result + ", " + (summary.totalSize / 1048576UL) + " MB, "
                      + summary.totalErrors + " errors, " + summary.totalTime);
            if (summary.result != BuildResult.Succeeded)
            {
                foreach (BuildStep step in report.steps)
                {
                    foreach (BuildStepMessage message in step.messages)
                    {
                        if (message.type == LogType.Error || message.type == LogType.Exception)
                            Debug.Log("[PROTO-ERR] " + message.content);
                    }
                }
            }
            return summary.result == BuildResult.Succeeded;
        }
    }
}
