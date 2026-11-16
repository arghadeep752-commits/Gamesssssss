using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace Moulika.EditorTools
{
    /// <summary>
    /// Project settings, asset preparation and the Android build. Used by the cloud build:
    ///   Unity -batchmode -buildTarget Android -executeMethod Moulika.EditorTools.MoulikaBuild.BuildAndroid -buildNumber N [-testApk path]
    /// and by the "Moulika" menu when the project is opened in the Unity editor.
    /// </summary>
    public static class MoulikaBuild
    {
        public const string ApplicationId = "com.anomynousdevs.moulika";
        const string DefaultApk = "Build/Moulika.apk";
        const string ScenePath = "Assets/Scenes/Main.unity";

        [MenuItem("Moulika/Rebuild Game Assets And Scene")]
        public static void RebuildMenu()
        {
            ConfigureProject(1);
            ConfigureQuality();
            PrepareAssets();
            string scene = BuildScene();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scene, true) };
        }

        [MenuItem("Moulika/Build Android APK")]
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
                Debug.LogError("[MOULIKA-ERR] build script crashed: " + e);
                exitCode = 1;
            }
            EditorApplication.Exit(exitCode);
        }

        static bool Build(int buildNumber, string output, string testApk)
        {
            Debug.Log("[MOULIKA] Unity " + Application.unityVersion + ", build " + buildNumber);
            ConfigureProject(buildNumber);
            ConfigureQuality();
            PrepareAssets();
            string scene = BuildScene();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scene, true) };
            AssetDatabase.SaveAssets();

            bool ok = BuildApk(scene, output, false);
            if (ok && !string.IsNullOrEmpty(testApk))
            {
                // extra x86_64 APK with the build check compiled in, only for the emulator (never published)
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.X86_64;
                bool testOk = BuildApk(scene, testApk, true);
                if (!testOk) Debug.LogWarning("[MOULIKA] emulator test APK failed to build (the phone APK is fine)");
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            }
            return ok;
        }

        static void ConfigureProject(int buildNumber)
        {
            PlayerSettings.companyName = "MXYAN GAMES";
            PlayerSettings.productName = "Moulika";
            PlayerSettings.bundleVersion = "2.0." + buildNumber;
            PlayerSettings.Android.bundleVersionCode = 1000 + Mathf.Max(1, buildNumber);
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, ApplicationId);
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.colorSpace = ColorSpace.Linear;
            // OpenGL ES 3 everywhere: the safest choice on older phones' GPUs (and what the emulator runs)
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            PlayerSettings.gpuSkinning = true;

            // landscape only, either way round
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.useAnimatedAutorotation = true;

            // full screen edge to edge, rendered at the screen's own resolution
            PlayerSettings.Android.renderOutsideSafeArea = true;
            PlayerSettings.Android.startInFullscreen = true;
            PlayerSettings.SplashScreen.show = false;
            PlayerSettings.SplashScreen.showUnityLogo = false;
            EditorUserBuildSettings.buildAppBundle = false;

            UseLegacyInputManager();

            var icon = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Game/Icons/icon_192.png");
            if (icon != null)
            {
                PlayerSettings.SetIcons(NamedBuildTarget.Unknown, new[] { icon }, IconKind.Any);
                Debug.Log("[MOULIKA] app icon set");
            }

            string keystore = System.Environment.GetEnvironmentVariable("MOULIKA_KEYSTORE");
            if (!string.IsNullOrEmpty(keystore) && File.Exists(keystore))
            {
                string pass = System.Environment.GetEnvironmentVariable("MOULIKA_KEYSTORE_PASS");
                PlayerSettings.Android.useCustomKeystore = true;
                PlayerSettings.Android.keystoreName = keystore;
                PlayerSettings.Android.keystorePass = pass;
                PlayerSettings.Android.keyaliasName = System.Environment.GetEnvironmentVariable("MOULIKA_KEY_ALIAS");
                PlayerSettings.Android.keyaliasPass = pass;
                Debug.Log("[MOULIKA] signing with the project keystore");
            }
            else
            {
                PlayerSettings.Android.useCustomKeystore = false;
                Debug.Log("[MOULIKA] signing with a debug key");
            }
        }

        // the touch controls read UnityEngine.Input, so make sure the classic input manager is active
        static void UseLegacyInputManager()
        {
            Object[] assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
            if (assets == null || assets.Length == 0) return;
            var settings = new SerializedObject(assets[0]);
            SerializedProperty handler = settings.FindProperty("activeInputHandler");
            if (handler == null) return;
            if (handler.intValue != 0)
            {
                handler.intValue = 0;
                settings.ApplyModifiedPropertiesWithoutUndo();
                Debug.Log("[MOULIKA] switched to the classic input manager");
            }
        }

        // every quality level: sharp (4x anti-aliasing, full-size textures) but light (no real-time shadows or lights,
        // the school is lit by its baked lightmaps)
        static void ConfigureQuality()
        {
            int current = QualitySettings.GetQualityLevel();
            string[] names = QualitySettings.names;
            for (int i = 0; i < names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.antiAliasing = 4;
                QualitySettings.shadows = UnityEngine.ShadowQuality.Disable;
                QualitySettings.pixelLightCount = 0;
                QualitySettings.anisotropicFiltering = AnisotropicFiltering.ForceEnable;
                QualitySettings.globalTextureMipmapLimit = 0;
                QualitySettings.realtimeReflectionProbes = false;
                QualitySettings.vSyncCount = 0;
                QualitySettings.lodBias = 2f;
                QualitySettings.softParticles = false;
                QualitySettings.skinWeights = SkinWeights.FourBones;
                QualitySettings.billboardsFaceCameraPosition = false;
            }
            QualitySettings.SetQualityLevel(current, false);
        }

        static void PrepareAssets()
        {
            AssetDatabase.Refresh();
            // fonts: characters the chalk font lacks come from Oswald, as in the Godot version
            var oswald = AssetDatabase.LoadAssetAtPath<Font>("Assets/Resources/Fonts/Oswald.ttf");
            var creepster = AssetDatabase.LoadAssetAtPath<Font>("Assets/Resources/Fonts/Creepster-Regular.ttf");
            SetFallback("Assets/Resources/Fonts/dk_midnight_chalker.otf", oswald);
            SetFallback("Assets/Resources/Fonts/baby_doll.ttf", creepster);
            // UI images
            foreach (string f in Directory.GetFiles("Assets/Resources/UI", "*.png"))
            {
                var imp = AssetImporter.GetAtPath(f.Replace('\\', '/')) as TextureImporter;
                if (imp == null) continue;
                imp.textureType = TextureImporterType.Default;
                imp.sRGBTexture = true;
                imp.alphaIsTransparency = true;
                imp.mipmapEnabled = true;
                imp.wrapMode = TextureWrapMode.Clamp;
                imp.filterMode = FilterMode.Trilinear;
                imp.textureCompression = TextureImporterCompression.Uncompressed;
                imp.SaveAndReimport();
            }
            // long recordings stream from storage instead of sitting decompressed in memory
            foreach (string f in Directory.GetFiles("Assets/Resources/Sounds", "*.ogg"))
            {
                string p = f.Replace('\\', '/');
                var imp = AssetImporter.GetAtPath(p) as AudioImporter;
                if (imp == null) continue;
                string n = Path.GetFileNameWithoutExtension(p);
                AudioImporterSampleSettings s = imp.defaultSampleSettings;
                bool longOne = n.Contains("music") || n.Contains("raga") || n == "night" || n == "wind" || n == "drone" || n == "heartbeat";
                s.loadType = longOne ? AudioClipLoadType.Streaming : AudioClipLoadType.DecompressOnLoad;
                s.compressionFormat = AudioCompressionFormat.Vorbis;
                s.quality = 0.8f;
                imp.defaultSampleSettings = s;
                imp.forceToMono = false;
                imp.SaveAndReimport();
            }
            SchoolBuilder.Build();
            MoulikaBuilder.Build();
            AssetDatabase.SaveAssets();
        }

        static void SetFallback(string path, Font fallback)
        {
            var imp = AssetImporter.GetAtPath(path) as TrueTypeFontImporter;
            if (imp == null || fallback == null) return;
            imp.fontTextureCase = FontTextureCase.Dynamic;
            imp.includeFontData = true;
            imp.fontReferences = new[] { fallback };
            imp.SaveAndReimport();
        }

        static string BuildScene()
        {
            if (!AssetDatabase.IsValidFolder("Assets/Scenes")) AssetDatabase.CreateFolder("Assets", "Scenes");
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.fog = false;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = Color.black;
            RenderSettings.skybox = null;
            var go = new GameObject("Game");
            go.AddComponent<Game>();
            EditorSceneManager.SaveScene(scene, ScenePath);
            Debug.Log("[MOULIKA] scene saved: " + ScenePath);
            return ScenePath;
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
            if (autoTest) options.extraScriptingDefines = new[] { "MOULIKA_AUTOTEST" };

            BuildReport report = BuildPipeline.BuildPlayer(options);
            BuildSummary summary = report.summary;
            Debug.Log("[MOULIKA] " + output + ": " + summary.result + ", " + (summary.totalSize / 1048576UL) + " MB, "
                      + summary.totalErrors + " errors, " + summary.totalTime);
            if (summary.result != BuildResult.Succeeded)
            {
                foreach (BuildStep step in report.steps)
                    foreach (BuildStepMessage message in step.messages)
                        if (message.type == LogType.Error || message.type == LogType.Exception)
                            Debug.Log("[MOULIKA-ERR] " + message.content);
            }
            return summary.result == BuildResult.Succeeded;
        }
    }
}
