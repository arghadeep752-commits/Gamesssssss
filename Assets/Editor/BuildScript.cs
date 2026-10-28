using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace ZombieStrike.EditorTools
{
    /// <summary>
    /// Command-line entry point used by CI:
    /// Unity -batchmode -quit -buildTarget Android -executeMethod ZombieStrike.EditorTools.BuildScript.BuildAndroid
    /// It creates the shared materials and the scene, configures the Android player and builds the APK.
    /// </summary>
    public static class BuildScript
    {
        const string ScenePath = "Assets/Scenes/Main.unity";
        const string MaterialsDir = "Assets/Resources/Materials";
        const string IconPath = "Assets/Icons/AppIcon.png";

        [MenuItem("Zombie Strike/Build Android APK")]
        public static void BuildAndroid()
        {
            try
            {
                int buildNumber = Math.Max(1, ReadIntArg("-buildNumber", 1));
                string output = ReadArg("-outputPath", "Build/ZombieStrike.apk");
                Log("Preparing build " + buildNumber + " -> " + output);

                CreateMaterials();
                CreateScene();
                ConfigurePlayer(buildNumber);
                ConfigureIcon();
                AssetDatabase.SaveAssets();

                string dir = Path.GetDirectoryName(output);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);

                var options = new BuildPlayerOptions
                {
                    scenes = new[] { ScenePath },
                    locationPathName = output,
                    target = BuildTarget.Android,
                    targetGroup = BuildTargetGroup.Android,
                    options = BuildOptions.None
                };

                BuildReport report = BuildPipeline.BuildPlayer(options);
                BuildSummary s = report.summary;
                Log("result=" + s.result + " size=" + s.totalSize + " errors=" + s.totalErrors +
                    " warnings=" + s.totalWarnings + " time=" + s.totalTime);

                if (s.result != BuildResult.Succeeded)
                {
                    foreach (BuildStep step in report.steps)
                    {
                        foreach (BuildStepMessage m in step.messages)
                        {
                            if (m.type == LogType.Error || m.type == LogType.Exception)
                                Debug.Log("[ZS-ERR] " + step.name + ": " + m.content);
                        }
                    }
                    EditorApplication.Exit(2);
                }
            }
            catch (Exception e)
            {
                Debug.LogError("[ZS-BUILD] Build script failed: " + e);
                EditorApplication.Exit(3);
            }
        }

        static void Log(string msg)
        {
            Debug.Log("[ZS-BUILD] " + msg);
        }

        static string ReadArg(string name, string fallback)
        {
            string[] args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
            {
                if (args[i] == name) return args[i + 1];
            }
            return fallback;
        }

        static int ReadIntArg(string name, int fallback)
        {
            int v;
            return int.TryParse(ReadArg(name, ""), out v) ? v : fallback;
        }

        // ------------------------------------------------------------------ materials

        static void CreateMaterials()
        {
            EnsureFolder("Assets/Resources");
            EnsureFolder(MaterialsDir);
            MakeMaterial("Lit", "Legacy Shaders/Diffuse", "Mobile/Diffuse", "Standard");
            MakeMaterial("Unlit", "Unlit/Color");
            MakeMaterial("UnlitTex", "Unlit/Texture");
            MakeMaterial("UnlitTransparent", "Unlit/Transparent", "Legacy Shaders/Transparent/Diffuse");
            MakeMaterial("Additive", "Mobile/Particles/Additive", "Legacy Shaders/Particles/Additive", "Particles/Standard Unlit");
            MakeMaterial("AlphaBlend", "Mobile/Particles/Alpha Blended", "Legacy Shaders/Particles/Alpha Blended", "Particles/Standard Unlit");
        }

        static void MakeMaterial(string name, params string[] shaderNames)
        {
            Shader shader = null;
            foreach (string n in shaderNames)
            {
                shader = Shader.Find(n);
                if (shader != null) break;
            }
            if (shader == null) throw new Exception("No shader found for material " + name + " (" + string.Join(", ", shaderNames) + ")");

            string path = MaterialsDir + "/" + name + ".mat";
            if (AssetDatabase.LoadAssetAtPath<Material>(path) != null) AssetDatabase.DeleteAsset(path);
            var mat = new Material(shader) { name = name };
            AssetDatabase.CreateAsset(mat, path);
            Log("material " + name + " uses " + shader.name);
        }

        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            string leaf = Path.GetFileName(path);
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, leaf);
        }

        // ------------------------------------------------------------------ scene

        static void CreateScene()
        {
            EnsureFolder("Assets/Scenes");
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // Fog and ambient light live in the scene, so the fog shader variants are kept in the build.
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = 0.045f;
            RenderSettings.fogColor = new Color(0.07f, 0.09f, 0.11f);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.25f, 0.27f, 0.33f);
            RenderSettings.skybox = null;

            var game = new GameObject("Game");
            game.AddComponent<ZombieStrike.GameManager>();

            if (!EditorSceneManager.SaveScene(scene, ScenePath)) throw new Exception("Could not save the scene");
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            Log("scene saved");
        }

        // ------------------------------------------------------------------ player settings

        static void ConfigurePlayer(int buildNumber)
        {
            PlayerSettings.companyName = "ZombieStrike";
            PlayerSettings.productName = "Zombie Strike";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, "com.zombiestrike.fps");
            PlayerSettings.bundleVersion = "1.0." + buildNumber;
            PlayerSettings.Android.bundleVersionCode = buildNumber;

            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel22;
            PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevelAuto;
            PlayerSettings.stripEngineCode = false;
            PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Android, ManagedStrippingLevel.Low);

            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            PlayerSettings.colorSpace = ColorSpace.Gamma;
            PlayerSettings.MTRendering = true;

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

            string keystore = Environment.GetEnvironmentVariable("ZS_KEYSTORE");
            if (!string.IsNullOrEmpty(keystore) && File.Exists(keystore))
            {
                string pass = Environment.GetEnvironmentVariable("ZS_KEYSTORE_PASS") ?? "";
                PlayerSettings.Android.useCustomKeystore = true;
                PlayerSettings.Android.keystoreName = keystore;
                PlayerSettings.Android.keystorePass = pass;
                PlayerSettings.Android.keyaliasName = Environment.GetEnvironmentVariable("ZS_KEY_ALIAS") ?? "zombiestrike";
                PlayerSettings.Android.keyaliasPass = pass;
                Log("signing with the project keystore");
            }
            else
            {
                PlayerSettings.Android.useCustomKeystore = false;
                Log("signing with the debug keystore");
            }

            KeepFogVariants();
        }

        static void KeepFogVariants()
        {
            try
            {
                UnityEngine.Object[] objs = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/GraphicsSettings.asset");
                if (objs == null || objs.Length == 0) return;
                var so = new SerializedObject(objs[0]);
                SetBool(so, "m_FogKeepLinear", true);
                SetBool(so, "m_FogKeepExp", true);
                SetBool(so, "m_FogKeepExp2", true);
                SerializedProperty strip = so.FindProperty("m_FogStripping");
                if (strip != null) strip.intValue = 1; // custom: keep the modes above
                so.ApplyModifiedPropertiesWithoutUndo();
                Log("fog variants kept");
            }
            catch (Exception e)
            {
                Debug.LogWarning("[ZS-BUILD] Could not change fog stripping: " + e.Message);
            }
        }

        static void SetBool(SerializedObject so, string name, bool value)
        {
            SerializedProperty p = so.FindProperty(name);
            if (p != null) p.boolValue = value;
        }

        static void ConfigureIcon()
        {
            var icon = AssetDatabase.LoadAssetAtPath<Texture2D>(IconPath);
            if (icon == null)
            {
                Debug.LogWarning("[ZS-BUILD] App icon not found at " + IconPath);
                return;
            }
            PlayerSettings.SetIconsForTargetGroup(BuildTargetGroup.Unknown, new[] { icon });
            Log("app icon set");
        }
    }
}
