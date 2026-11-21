using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace TradersMadness.EditorTools
{
    /// <summary>
    /// Project settings, asset preparation and the Android build. Used by the cloud build:
    ///   Unity -batchmode -buildTarget Android -executeMethod TradersMadness.EditorTools.TMBuild.BuildAndroid -buildNumber N [-testApk path]
    /// and by the "Trader's Madness" menu when the project is opened in the Unity editor.
    /// </summary>
    public static class TMBuild
    {
        public const string ApplicationId = "com.anomynousdevs.tradersmadness";
        const string DefaultApk = "Build/TradersMadness.apk";
        const string ScenePath = "Assets/Scenes/Main.unity";

        [MenuItem("Trader's Madness/Rebuild Game Assets And Scene")]
        public static void RebuildMenu()
        {
            ConfigureProject(1);
            ConfigureQuality();
            PrepareAssets();
            string scene = BuildScene();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scene, true) };
        }

        [MenuItem("Trader's Madness/Build Android APK")]
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
                Debug.LogError("[TM-ERR] build script crashed: " + e);
                exitCode = 1;
            }
            EditorApplication.Exit(exitCode);
        }

        static bool Build(int buildNumber, string output, string testApk)
        {
            Debug.Log("[TM] Unity " + Application.unityVersion + ", build " + buildNumber);
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
                if (!testOk) Debug.LogWarning("[TM] emulator test APK failed to build (the phone APK is fine)");
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            }
            return ok;
        }

        static void ConfigureProject(int buildNumber)
        {
            PlayerSettings.companyName = "MXYAN GAMES";
            PlayerSettings.productName = "Trader's Madness";
            PlayerSettings.bundleVersion = "1.0." + buildNumber;
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
            EditorUserBuildSettings.buildAppBundle = false;

            // the Unity splash: white Unity logo on black, before the game's own black menu
            PlayerSettings.SplashScreen.show = true;
            PlayerSettings.SplashScreen.showUnityLogo = true;
            PlayerSettings.SplashScreen.unityLogoStyle = PlayerSettings.SplashScreen.UnityLogoStyle.LightOnDark;
            PlayerSettings.SplashScreen.backgroundColor = Color.black;
            PlayerSettings.SplashScreen.animationMode = PlayerSettings.SplashScreen.AnimationMode.Dolly;
            PlayerSettings.SplashScreen.drawMode = PlayerSettings.SplashScreen.DrawMode.UnityLogoBelow;
            PlayerSettings.SplashScreen.overlayOpacity = 1f;

            UseLegacyInputManager();
            SetIcons();

            string keystore = System.Environment.GetEnvironmentVariable("TM_KEYSTORE");
            if (!string.IsNullOrEmpty(keystore) && File.Exists(keystore))
            {
                string pass = System.Environment.GetEnvironmentVariable("TM_KEYSTORE_PASS");
                PlayerSettings.Android.useCustomKeystore = true;
                PlayerSettings.Android.keystoreName = keystore;
                PlayerSettings.Android.keystorePass = pass;
                PlayerSettings.Android.keyaliasName = System.Environment.GetEnvironmentVariable("TM_KEY_ALIAS");
                PlayerSettings.Android.keyaliasPass = pass;
                Debug.Log("[TM] signing with the project keystore");
            }
            else
            {
                PlayerSettings.Android.useCustomKeystore = false;
                Debug.Log("[TM] signing with a debug key");
            }
        }

        /// <summary>
        /// The Trader's Madness icon (tools/ui/make_ui.py): the square icon for older launchers, an adaptive icon
        /// (background and foreground) for Android 8+, and a round one for Android 7.1.
        /// </summary>
        static void SetIcons()
        {
            const string dir = "Assets/Branding/";
            Texture2D legacy = IconTex(dir + "tm_icon_1024.png");
            Texture2D bg = IconTex(dir + "tm_icon_bg.png");
            Texture2D fg = IconTex(dir + "tm_icon_fg.png");
            Texture2D round = IconTex(dir + "tm_icon_round.png");
            if (legacy == null)
            {
                Debug.LogWarning("[TM] app icon missing in " + dir);
                return;
            }
            PlayerSettings.SetIcons(NamedBuildTarget.Unknown, new[] { legacy }, IconKind.Any);
            foreach (PlatformIconKind kind in PlayerSettings.GetSupportedIconKinds(NamedBuildTarget.Android))
            {
                string name = kind.ToString();
                PlatformIcon[] icons = PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android, kind);
                foreach (PlatformIcon icon in icons)
                {
                    if (name.Contains("Adaptive") && bg != null && fg != null) icon.SetTextures(bg, fg);   // background, foreground
                    else if (name.Contains("Round") && round != null) icon.SetTexture(round);
                    else icon.SetTexture(legacy);
                }
                PlayerSettings.SetPlatformIcons(NamedBuildTarget.Android, kind, icons);
                Debug.Log("[TM] icon " + name + ": " + icons.Length + " sizes");
            }
        }

        static Texture2D IconTex(string path)
        {
            AssetRules.Ensure(path);
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
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
                Debug.Log("[TM] switched to the classic input manager");
            }
        }

        // every quality level: sharp (anti-aliasing, full-size textures) but light (no real-time shadows or lights,
        // the house is lit by its baked lightmaps); the game itself picks 0/2/4x MSAA and the render size
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
            foreach (string f in Directory.GetFiles("Assets/Resources/Fonts", "*.ttf"))
            {
                var imp = AssetImporter.GetAtPath(f.Replace('\\', '/')) as TrueTypeFontImporter;
                if (imp == null || (imp.fontTextureCase == FontTextureCase.Dynamic && imp.includeFontData)) continue;
                imp.fontTextureCase = FontTextureCase.Dynamic;
                imp.includeFontData = true;
                imp.SaveAndReimport();
            }
            // UI images and sounds (normally already right: AssetRulesImporter sets them on the first import)
            if (Directory.Exists("Assets/Resources/UI"))
                foreach (string f in Directory.GetFiles("Assets/Resources/UI", "*.png")) AssetRules.Ensure(f.Replace('\\', '/'));
            if (Directory.Exists("Assets/Resources/Sounds"))
                foreach (string f in Directory.GetFiles("Assets/Resources/Sounds", "*.ogg"))
                {
                    string p = f.Replace('\\', '/');
                    var imp = AssetImporter.GetAtPath(p) as AudioImporter;
                    if (imp == null) continue;
                    AudioClipLoadType want = AssetRules.LongSound(Path.GetFileNameWithoutExtension(p)) ? AudioClipLoadType.Streaming : AudioClipLoadType.DecompressOnLoad;
                    if (imp.defaultSampleSettings.loadType == want) continue;
                    AudioImporterSampleSettings s = imp.defaultSampleSettings;
                    s.loadType = want;
                    s.compressionFormat = AudioCompressionFormat.Vorbis;
                    s.quality = 0.75f;
                    imp.defaultSampleSettings = s;
                    imp.SaveAndReimport();
                }
            HouseBuilder.Build();
            try
            {
                TraderBuilder.Build();
            }
            catch (System.Exception e)
            {
                Debug.LogWarning("[TM] trader prefab not built: " + e.Message);
            }
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
            // a photographed night sky (Poly Haven HDRI, converted to a picture by convert_assets.py)
            RenderSettings.skybox = null;
            const string skyTex = "Assets/Game/Sky/night_sky.png";
            AssetRules.Ensure(skyTex);
            var sky = AssetDatabase.LoadAssetAtPath<Texture2D>(skyTex);
            Shader pano = Shader.Find("Skybox/Panoramic");
            if (sky != null && pano != null)
            {
                var mat = new Material(pano) { name = "Night sky" };
                mat.SetTexture("_MainTex", sky);
                mat.SetFloat("_Mapping", 1f);       // latitude-longitude layout
                mat.SetFloat("_ImageType", 0f);     // 360 degrees
                mat.SetFloat("_Exposure", 1f);
                mat.SetColor("_Tint", new Color(0.42f, 0.44f, 0.5f, 0.5f));
                AssetDatabase.DeleteAsset("Assets/Generated/Night sky.mat");
                AssetDatabase.CreateAsset(mat, "Assets/Generated/Night sky.mat");
                RenderSettings.skybox = mat;
                Debug.Log("[TM] night sky set");
            }
            var go = new GameObject("Game");
            go.AddComponent<Game>();
            EditorSceneManager.SaveScene(scene, ScenePath);
            Debug.Log("[TM] scene saved: " + ScenePath);
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
            if (autoTest) options.extraScriptingDefines = new[] { "TM_AUTOTEST" };

            BuildReport report = BuildPipeline.BuildPlayer(options);
            BuildSummary summary = report.summary;
            Debug.Log("[TM] " + output + ": " + summary.result + ", " + (summary.totalSize / 1048576UL) + " MB, "
                      + summary.totalErrors + " errors, " + summary.totalTime);
            if (summary.result != BuildResult.Succeeded)
            {
                foreach (BuildStep step in report.steps)
                    foreach (BuildStepMessage message in step.messages)
                        if (message.type == LogType.Error || message.type == LogType.Exception)
                            Debug.Log("[TM-ERR] " + message.content);
            }
            return summary.result == BuildResult.Succeeded;
        }
    }
}
