using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace Dimnight.EditorTools
{
    /// <summary>
    /// Granny Dimnight cloud build:
    ///   Unity -batchmode -buildTarget Android -executeMethod Dimnight.EditorTools.DimnightBuild.BuildAndroid -buildNumber N
    /// The project is Granny 4 EndGame's own scenes, models, menus and sounds (exported by AssetRipper, pointed at the
    /// real Unity 6 packages by tools/unity/remap_packages.py), with the rewritten game scripts and real textures.
    /// </summary>
    public static class DimnightBuild
    {
        public const string ProductName = "Granny Dimnight";
        public const string CompanyName = "MXYAN GAMES";
        public const string ApplicationId = "com.anomynousdevs.grannydimnight";
        const string DefaultApk = "Build/GrannyDimnight.apk";

        static void Log(string message) { Debug.Log("[DIMNIGHT] " + message); }

        [MenuItem("Granny Dimnight/Build Android APK")]
        public static void BuildMenu() { Build(1, DefaultApk, null); }

        [MenuItem("Granny Dimnight/Prepare Project (materials, titles, house)")]
        public static void PrepareMenu() { Prepare(1); }

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
                Debug.LogError("[DIMNIGHT-ERR] build script crashed: " + e);
                exitCode = 1;
            }
            EditorApplication.Exit(exitCode);
        }

        static bool Build(int buildNumber, string output, string testApk)
        {
            Log("Unity " + Application.unityVersion + ", build " + buildNumber);
            string[] scenes = Prepare(buildNumber);
            bool ok = BuildApk(scenes, output, false);
            if (ok && !string.IsNullOrEmpty(testApk))
            {
                // x86_64 copy with the automatic play-through compiled in, only for the emulator check. The emulator's
                // software GPU draws URP's HDR / MSAA intermediate image as pure black, so that copy renders straight
                // to the screen (the phone APK above keeps the game's own settings).
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.X86_64;
                var restore = EmulatorFriendlyRendering();
                if (!BuildApk(scenes, testApk, true)) Log("emulator test APK failed to build (the phone APK is fine)");
                restore();
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            }
            return ok;
        }

        static string[] Prepare(int buildNumber)
        {
            ConfigureProject(buildNumber);
            ConfigureQuality();
            int fixedMats = MaterialFixer.FixAll();
            Log("materials moved to URP shaders: " + fixedMats);
            FixRendererData();
            string[] scenes = EditorBuildSettings.scenes.Where(s => s.enabled && File.Exists(s.path)).Select(s => s.path).ToArray();
            if (scenes.Length == 0)
                scenes = AssetDatabase.FindAssets("t:Scene", new[] { "Assets" }).Select(AssetDatabase.GUIDToAssetPath).ToArray();
            Log("scenes: " + string.Join(", ", scenes));
            foreach (string scene in scenes) SceneTweaks.Apply(scene);
            AssetDatabase.SaveAssets();
            return scenes;
        }

        static void ConfigureProject(int buildNumber)
        {
            PlayerSettings.companyName = CompanyName;
            PlayerSettings.productName = ProductName;
            PlayerSettings.bundleVersion = "1.0." + buildNumber;
            PlayerSettings.Android.bundleVersionCode = Mathf.Max(1, buildNumber);
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, ApplicationId);
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel23;
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            PlayerSettings.gpuSkinning = true;
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.Android.renderOutsideSafeArea = true;
            PlayerSettings.Android.startInFullscreen = true;
            EditorUserBuildSettings.buildAppBundle = false;
            PlayerSettings.SplashScreen.show = true;
            PlayerSettings.SplashScreen.showUnityLogo = true;
            PlayerSettings.SplashScreen.unityLogoStyle = PlayerSettings.SplashScreen.UnityLogoStyle.LightOnDark;
            PlayerSettings.SplashScreen.backgroundColor = Color.black;
            UseLegacyInputManager();
            SetIcon();

            string keystore = System.Environment.GetEnvironmentVariable("DIMNIGHT_KEYSTORE");
            if (!string.IsNullOrEmpty(keystore) && File.Exists(keystore))
            {
                string pass = System.Environment.GetEnvironmentVariable("DIMNIGHT_KEYSTORE_PASS");
                PlayerSettings.Android.useCustomKeystore = true;
                PlayerSettings.Android.keystoreName = keystore;
                PlayerSettings.Android.keystorePass = pass;
                PlayerSettings.Android.keyaliasName = System.Environment.GetEnvironmentVariable("DIMNIGHT_KEY_ALIAS");
                PlayerSettings.Android.keyaliasPass = pass;
                Log("signing with the project keystore");
            }
            else
            {
                PlayerSettings.Android.useCustomKeystore = false;
                Log("signing with a debug key");
            }
        }

        static void SetIcon()
        {
            const string path = "Assets/Dimnight/Branding/icon_1024.png";
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null) { Log("no app icon at " + path); return; }
            if (importer.textureType != TextureImporterType.Default || importer.isReadable || importer.mipmapEnabled)
            {
                importer.textureType = TextureImporterType.Default;
                importer.mipmapEnabled = false;
                importer.isReadable = false;
                importer.SaveAndReimport();
            }
            var icon = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            PlayerSettings.SetIcons(NamedBuildTarget.Unknown, new[] { icon }, IconKind.Any);
            foreach (PlatformIconKind kind in PlayerSettings.GetSupportedIconKinds(NamedBuildTarget.Android))
            {
                PlatformIcon[] icons = PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android, kind);
                foreach (PlatformIcon i in icons)
                {
                    if (kind.ToString().Contains("Adaptive")) i.SetTextures(icon, icon);
                    else i.SetTexture(icon);
                }
                PlayerSettings.SetPlatformIcons(NamedBuildTarget.Android, kind, icons);
            }
            Log("app icon set");
        }

        static void UseLegacyInputManager()
        {
            Object[] assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
            if (assets == null || assets.Length == 0) return;
            var settings = new SerializedObject(assets[0]);
            SerializedProperty handler = settings.FindProperty("activeInputHandler");
            if (handler != null && handler.intValue != 0)
            {
                handler.intValue = 0;
                settings.ApplyModifiedPropertiesWithoutUndo();
                Log("classic input manager on (the game's touch controls use it)");
            }
        }

        /// <summary>
        /// The game's renderer still points at the old URP 14 post-processing resources, which miss shaders URP 17 needs
        /// ("Missing shader. PostProcessing render passes will not execute"): point it at the package's own set so the
        /// game's colour grading and vignette show again.
        /// </summary>
        static void FixRendererData()
        {
            const string ppPath = "Packages/com.unity.render-pipelines.universal/Runtime/Data/PostProcessData.asset";
            var pp = AssetDatabase.LoadAssetAtPath<ScriptableObject>(ppPath);
            if (pp == null) { Log("package PostProcessData not found at " + ppPath); return; }
            int n = 0;
            foreach (string guid in AssetDatabase.FindAssets("t:UniversalRendererData"))
            {
                var data = AssetDatabase.LoadAssetAtPath<ScriptableObject>(AssetDatabase.GUIDToAssetPath(guid));
                if (data == null) continue;
                var so = new SerializedObject(data);
                SerializedProperty prop = so.FindProperty("postProcessData") ?? so.FindProperty("m_PostProcessData");
                if (prop == null) { Log("no postProcessData field on " + data.name); continue; }
                prop.objectReferenceValue = pp;
                so.ApplyModifiedPropertiesWithoutUndo();
                EditorUtility.SetDirty(data);
                n++;
            }
            AssetDatabase.SaveAssets();
            Log("renderers pointed at the URP 17 post-processing resources: " + n);
        }

        static System.Action EmulatorFriendlyRendering()
        {
            var undo = new List<System.Action>();
            foreach (string guid in AssetDatabase.FindAssets("t:UniversalRenderPipelineAsset"))
            {
                var asset = AssetDatabase.LoadAssetAtPath<ScriptableObject>(AssetDatabase.GUIDToAssetPath(guid));
                if (asset == null) continue;
                var so = new SerializedObject(asset);
                foreach (var (name, value) in new (string, object)[] {
                    ("m_SupportsHDR", false), ("m_MSAA", 1), ("m_RenderScale", 1f),
                    ("m_RequireDepthTexture", false), ("m_RequireOpaqueTexture", false) })
                {
                    SerializedProperty prop = so.FindProperty(name);
                    if (prop == null) continue;
                    if (prop.propertyType == SerializedPropertyType.Boolean) { bool old = prop.boolValue; prop.boolValue = (bool)value; undo.Add(() => SetAndSave(asset, name, old)); }
                    else if (prop.propertyType == SerializedPropertyType.Integer) { int old = prop.intValue; prop.intValue = (int)value; undo.Add(() => SetAndSave(asset, name, old)); }
                    else if (prop.propertyType == SerializedPropertyType.Float) { float old = prop.floatValue; prop.floatValue = (float)value; undo.Add(() => SetAndSave(asset, name, old)); }
                }
                so.ApplyModifiedPropertiesWithoutUndo();
                EditorUtility.SetDirty(asset);
            }
            AssetDatabase.SaveAssets();
            Log("emulator copy: URP HDR, MSAA and intermediate textures off");
            return () => { foreach (var u in undo) u(); AssetDatabase.SaveAssets(); };
        }

        static void SetAndSave(ScriptableObject asset, string name, object value)
        {
            var so = new SerializedObject(asset);
            SerializedProperty prop = so.FindProperty(name);
            if (prop == null) return;
            if (value is bool b) prop.boolValue = b;
            else if (value is int i) prop.intValue = i;
            else if (value is float f) prop.floatValue = f;
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(asset);
        }

        static void ConfigureQuality()
        {
            int current = QualitySettings.GetQualityLevel();
            for (int i = 0; i < QualitySettings.names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.vSyncCount = 0;
                QualitySettings.anisotropicFiltering = AnisotropicFiltering.ForceEnable;
                QualitySettings.globalTextureMipmapLimit = 0;
            }
            QualitySettings.SetQualityLevel(current, false);
        }

        static bool IsToolCrash(BuildReport report)
        {
            foreach (BuildStep step in report.steps)
                foreach (BuildStepMessage message in step.messages)
                {
                    if (message.type != LogType.Error && message.type != LogType.Exception) continue;
                    string m = message.content ?? "";
                    if (m.Contains("il2cpp") || m.Contains("Segmentation fault") || m.Contains("core dumped")) return true;
                }
            return false;
        }

        static bool BuildApk(string[] scenes, string output, bool autoTest)
        {
            string dir = Path.GetDirectoryName(Path.GetFullPath(output));
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            var options = new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = output,
                target = BuildTarget.Android,
                targetGroup = BuildTargetGroup.Android,
                options = BuildOptions.None,
            };
            if (autoTest) options.extraScriptingDefines = new[] { "DIMNIGHT_AUTOTEST" };
            BuildReport report = BuildPipeline.BuildPlayer(options);
            BuildSummary summary = report.summary;
            if (summary.result != BuildResult.Succeeded && IsToolCrash(report))
            {
                // il2cpp now and then dies with a segmentation fault on the cloud machine: one more try, not a full rerun
                Log(output + ": the il2cpp tool crashed, building once more");
                report = BuildPipeline.BuildPlayer(options);
                summary = report.summary;
            }
            Log(output + ": " + summary.result + ", " + (summary.totalSize / 1048576UL) + " MB, "
                + summary.totalErrors + " errors, " + summary.totalTime);
            if (summary.result != BuildResult.Succeeded)
            {
                foreach (BuildStep step in report.steps)
                    foreach (BuildStepMessage message in step.messages)
                        if (message.type == LogType.Error || message.type == LogType.Exception)
                            Debug.Log("[DIMNIGHT-ERR] " + message.content);
            }
            return summary.result == BuildResult.Succeeded;
        }
    }
}
