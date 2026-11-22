using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace Danga.EditorTools
{
    /// <summary>
    /// Project settings, asset preparation and the Android build. Used by the cloud build:
    ///   Unity -batchmode -buildTarget Android -executeMethod Danga.EditorTools.DGBuild.BuildAndroid -buildNumber N [-testApk path]
    /// and by the "Danga" menu when the project is opened in the Unity editor.
    /// </summary>
    public static class DGBuild
    {
        public const string ApplicationId = "com.mxyangames.danga";
        const string DefaultApk = "Build/Danga.apk";
        const string ScenePath = "Assets/Scenes/Main.unity";

        [MenuItem("Danga/Rebuild Game Assets And Scene")]
        public static void RebuildMenu()
        {
            ConfigureProject(1);
            ConfigureQuality();
            PrepareAssets();
            string scene = BuildScene();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scene, true) };
        }

        [MenuItem("Danga/Build Android APK")]
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
                Debug.LogError("[DG-ERR] build script crashed: " + e);
                exitCode = 1;
            }
            EditorApplication.Exit(exitCode);
        }

        static bool Build(int buildNumber, string output, string testApk)
        {
            Debug.Log("[DG] Unity " + Application.unityVersion + ", build " + buildNumber);
            ImportEverything();
            ConfigureProject(buildNumber);
            ConfigureQuality();
            PrepareAssets();
            string scene = BuildScene();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scene, true) };
            AssetDatabase.SaveAssets();

            bool ok = BuildApk(scene, output, false);
            if (!ok)
            {
                // Gradle sometimes cannot reach Maven for a moment: one more try before giving up
                Debug.Log("[DG] the build failed; trying once more");
                ok = BuildApk(scene, output, false);
            }
            if (ok && !string.IsNullOrEmpty(testApk))
            {
                // extra x86_64 APK with the build check compiled in, only for the emulator (never published)
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.X86_64;
                AssetRules.EmulatorTextures();
                bool testOk = BuildApk(scene, testApk, true);
                if (!testOk) Debug.LogWarning("[DG] emulator test APK failed to build (the phone APK is fine)");
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            }
            return ok;
        }

        /// <summary>
        /// Makes sure every file in Assets/ is imported before the builders look for them (the converted house, the
        /// icons, the sounds), and says what the asset database can see.
        /// </summary>
        static void ImportEverything()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            string[] probes = { "Assets/Resources/city_meta.json", "Assets/Resources/models.json", "Assets/Resources/Gen/City/chunks.bytes",
                                "Assets/Resources/Gen/City/layers.png", "Assets/Branding/dg_icon_1024.png", "Assets/Resources/UI/btn_round.png",
                                "Assets/Resources/Sounds/engine_car.ogg", "Assets/Resources/Fonts/UIFont.ttf" };
            int missing = 0;
            foreach (string p in probes)
            {
                bool onDisk = File.Exists(p);
                bool known = !string.IsNullOrEmpty(AssetDatabase.AssetPathToGUID(p, AssetPathToGUIDOptions.OnlyExistingAssets));
                if (onDisk && !known)
                {
                    missing++;
                    AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                    known = !string.IsNullOrEmpty(AssetDatabase.AssetPathToGUID(p, AssetPathToGUIDOptions.OnlyExistingAssets));
                }
                Debug.Log("[DG] asset " + p + ": on disk " + onDisk + ", imported " + known);
            }
            if (missing > 0)
            {
                // the first import skipped files: import the folders again, one by one
                foreach (string dir in new[] { "Assets/Branding", "Assets/Resources" })
                    if (Directory.Exists(dir))
                        AssetDatabase.ImportAsset(dir, ImportAssetOptions.ImportRecursive | ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            }
            int n = 0;
            foreach (string dir in new[] { "Assets/Resources", "Assets/Branding" })
                if (AssetDatabase.IsValidFolder(dir)) n += AssetDatabase.FindAssets("", new[] { dir }).Length;
            Debug.Log("[DG] asset database: " + n + " assets in Assets/Resources and Assets/Branding");
        }

        static void ConfigureProject(int buildNumber)
        {
            PlayerSettings.companyName = "MXYAN GAMES";
            PlayerSettings.productName = "Danga";
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

            string keystore = System.Environment.GetEnvironmentVariable("DG_KEYSTORE");
            if (!string.IsNullOrEmpty(keystore) && File.Exists(keystore))
            {
                string pass = System.Environment.GetEnvironmentVariable("DG_KEYSTORE_PASS");
                PlayerSettings.Android.useCustomKeystore = true;
                PlayerSettings.Android.keystoreName = keystore;
                PlayerSettings.Android.keystorePass = pass;
                PlayerSettings.Android.keyaliasName = System.Environment.GetEnvironmentVariable("DG_KEY_ALIAS");
                PlayerSettings.Android.keyaliasPass = pass;
                Debug.Log("[DG] signing with the project keystore");
            }
            else
            {
                PlayerSettings.Android.useCustomKeystore = false;
                Debug.Log("[DG] signing with a debug key");
            }
        }

        /// <summary>
        /// The Danga icon (tools/ui/make_ui.py): the square icon for older launchers, an adaptive icon
        /// (background and foreground) for Android 8+, and a round one for Android 7.1.
        /// </summary>
        static void SetIcons()
        {
            const string dir = "Assets/Branding/";
            Texture2D legacy = IconTex(dir + "dg_icon_1024.png");
            Texture2D bg = IconTex(dir + "dg_icon_bg.png");
            Texture2D fg = IconTex(dir + "dg_icon_fg.png");
            Texture2D round = IconTex(dir + "dg_icon_round.png");
            if (legacy == null)
            {
                Debug.LogWarning("[DG] app icon missing in " + dir);
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
                Debug.Log("[DG] icon " + name + ": " + icons.Length + " sizes");
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
                Debug.Log("[DG] switched to the classic input manager");
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
                QualitySettings.antiAliasing = 2;
                QualitySettings.shadows = UnityEngine.ShadowQuality.Disable;
                QualitySettings.pixelLightCount = 0;
                QualitySettings.anisotropicFiltering = AnisotropicFiltering.ForceEnable;
                QualitySettings.globalTextureMipmapLimit = 0;
                QualitySettings.realtimeReflectionProbes = false;
                QualitySettings.vSyncCount = 0;
                QualitySettings.lodBias = 2f;
                QualitySettings.softParticles = false;
                QualitySettings.skinWeights = SkinWeights.FourBones;
                QualitySettings.asyncUploadTimeSlice = 4;
                QualitySettings.billboardsFaceCameraPosition = false;
            }
            QualitySettings.SetQualityLevel(current, false);
        }

        static void PrepareAssets()
        {
            AssetDatabase.Refresh();
            if (Directory.Exists("Assets/Resources/Fonts"))
                foreach (string f in Directory.GetFiles("Assets/Resources/Fonts", "*.ttf"))
                {
                    var imp = AssetImporter.GetAtPath(f.Replace('\\', '/')) as TrueTypeFontImporter;
                    if (imp == null || (imp.fontTextureCase == FontTextureCase.Dynamic && imp.includeFontData)) continue;
                    imp.fontTextureCase = FontTextureCase.Dynamic;
                    imp.includeFontData = true;
                    imp.SaveAndReimport();
                }
            int n = 0;
            foreach (string dir in new[] { "Assets/Resources/UI", "Assets/Resources/Gen", "Assets/Branding" })
                if (Directory.Exists(dir))
                    foreach (string f in Directory.GetFiles(dir, "*.png", SearchOption.AllDirectories)) { AssetRules.Ensure(f.Replace('\\', '/')); n++; }
            Debug.Log("[DG] textures checked: " + n);
            var arr = AssetDatabase.LoadAssetAtPath<Texture2DArray>("Assets/Resources/Gen/City/layers.png");
            Debug.Log("[DG] city texture array: " + (arr != null ? arr.width + "x" + arr.height + " x" + arr.depth + " " + arr.format : "MISSING"));
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
            RenderSettings.ambientLight = Color.gray;
            RenderSettings.skybox = null;
            var go = new GameObject("Game");
            go.AddComponent<Game>();
            EditorSceneManager.SaveScene(scene, ScenePath);
            Debug.Log("[DG] scene saved: " + ScenePath);
            return ScenePath;
        }

        static bool BuildApk(string scene, string output, bool autoTest)
        {
            string dir = System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(output));
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            var options = new BuildPlayerOptions
            {
                scenes = new[] { scene },
                locationPathName = output,
                target = BuildTarget.Android,
                targetGroup = BuildTargetGroup.Android,
                options = BuildOptions.None,
            };
            if (autoTest) options.extraScriptingDefines = new[] { "DG_AUTOTEST" };

            BuildReport report = BuildPipeline.BuildPlayer(options);
            BuildSummary summary = report.summary;
            Debug.Log("[DG] " + output + ": " + summary.result + ", " + (summary.totalSize / 1048576UL) + " MB, "
                      + summary.totalErrors + " errors, " + summary.totalTime);
            if (summary.result != BuildResult.Succeeded)
            {
                foreach (BuildStep step in report.steps)
                    foreach (BuildStepMessage message in step.messages)
                        if (message.type == LogType.Error || message.type == LogType.Exception)
                            Debug.Log("[DG-ERR] " + message.content);
            }
            return summary.result == BuildResult.Succeeded;
        }
    }
}
