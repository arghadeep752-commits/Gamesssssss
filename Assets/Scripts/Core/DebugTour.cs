using System.Collections;
using System.Text;
using UnityEngine;

namespace RealFPS
{
    /// <summary>
    /// Automated screenshot tour for the cloud emulator test. Only runs when the
    /// app is started with the intent extra "rf_tour" (adb shell am start ... -e rf_tour 1).
    /// It plays the game, visits a list of viewpoints and logs "[RF] TOUR shot n name"
    /// when each view is ready to be captured. Waits are capped in wall-clock time so a
    /// very slow software-rendered emulator cannot stall the tour.
    /// </summary>
    public class DebugTour : MonoBehaviour
    {
        public static bool Requested()
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            try
            {
                using (var player = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
                using (var activity = player.GetStatic<AndroidJavaObject>("currentActivity"))
                using (var intent = activity.Call<AndroidJavaObject>("getIntent"))
                {
                    string v = intent.Call<string>("getStringExtra", "rf_tour");
                    return !string.IsNullOrEmpty(v);
                }
            }
            catch (System.Exception e)
            {
                Debug.Log("[RF] tour check failed: " + e.Message);
                return false;
            }
#else
            return false;
#endif
        }

        int shot;
        int exceptions;
        float lastFrameMs;

        void OnEnable()
        {
            Application.logMessageReceived += OnLog;
        }

        void OnDisable()
        {
            Application.logMessageReceived -= OnLog;
        }

        void OnLog(string condition, string stackTrace, LogType type)
        {
            if (type != LogType.Exception && type != LogType.Error) return;
            exceptions++;
            if (exceptions <= 20)
            {
                string st = stackTrace ?? "";
                Debug.Log("[RF] EXC " + condition + " @ " + st.Replace("\n", " | ").Substring(0, Mathf.Min(300, st.Length)));
            }
        }

        void Update()
        {
            lastFrameMs = Time.unscaledDeltaTime * 1000f;
        }

        IEnumerator WaitFrames(int frames, float seconds, float maxSeconds = 25f)
        {
            float t0 = Time.realtimeSinceStartup;
            int f0 = Time.frameCount;
            while ((Time.frameCount - f0 < frames || Time.realtimeSinceStartup - t0 < seconds) && Time.realtimeSinceStartup - t0 < maxSeconds)
                yield return null;
        }

        IEnumerator Shot(string name)
        {
            yield return WaitFrames(3, 1.5f);
            float t0 = Time.realtimeSinceStartup;
            int f0 = Time.frameCount;
            yield return WaitFrames(2, 0.5f, 15f);
            float fps = (Time.frameCount - f0) / Mathf.Max(0.001f, Time.realtimeSinceStartup - t0);
            shot++;
            Camera c = Camera.main;
            string pos = c != null ? c.transform.position.ToString("F1") + " fwd " + c.transform.forward.ToString("F2") : "no camera";
            TreeRenderer tr = Game.I != null && Game.I.quality != null ? Game.I.quality.trees : null;
            string trees = tr != null ? " trees=" + tr.DrawnLastFrame + "/" + tr.DrawCallsLastFrame + "calls" : "";
            Debug.Log("[RF] TOUR shot " + shot + " " + name + " fps=" + fps.ToString("0.0") + " frameMs=" + lastFrameMs.ToString("0") +
                      " cam " + pos + trees + " exc=" + exceptions);
            yield return new WaitForSecondsRealtime(3.5f);  // time for the screenshot
        }

        static void Diagnostics()
        {
            var sb = new StringBuilder();
            sb.Append("[RF] DIAG ").Append(RenderCompat.Describe());
            sb.Append(" | quality ").Append(QualitySettings.GetQualityLevel()).Append('/').Append(QualitySettings.names.Length);
            sb.Append(" | pipeline ").Append(UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null ? UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline.name : "BUILT-IN");
            sb.Append(" | fog ").Append(RenderSettings.fog).Append(' ').Append(RenderSettings.fogDensity).Append(' ').Append(RenderSettings.fogColor);
            Debug.Log(sb.ToString());
            Terrain t = Terrain.activeTerrain;
            if (t != null)
            {
                Material m = t.materialTemplate;
                Debug.Log("[RF] DIAG terrain " + t.terrainData.size + " at " + t.transform.position + " shader=" + (m != null ? m.shader.name + " supported=" + m.shader.isSupported : "none") +
                          " instanced=" + t.drawInstanced + " pixelError=" + t.heightmapPixelError + " basemap=" + t.basemapDistance +
                          " details=" + t.detailObjectDistance + "m x" + t.detailObjectDensity + " layers=" + t.terrainData.terrainLayers.Length +
                          " detailProtos=" + t.terrainData.detailPrototypes.Length);
            }
            foreach (Renderer r in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
            {
                Vector3 s = r.bounds.size;
                if (s.x < 60f && s.z < 60f) continue;
                Material m = r.sharedMaterial;
                Debug.Log("[RF] DIAG big renderer " + r.name + " bounds " + r.bounds.center.ToString("F0") + " size " + s.ToString("F0") +
                          " shader=" + (m != null ? m.shader.name + " supported=" + m.shader.isSupported : "none") + " enabled=" + r.enabled);
            }
        }

        IEnumerator Start()
        {
            Debug.Log("[RF] TOUR start");
            Diagnostics();
            // the emulator renders in software: keep the look but render fewer pixels
            if (QualityManager.I != null) QualityManager.I.ForceScale(0.5f);
            yield return WaitFrames(6, 6f);
            yield return Shot("menu");

            Game g = Game.I;
            g.StartGame();
            yield return WaitFrames(6, 3f);
            yield return Shot("spawn");

            // an aerial view of the whole valley
            Camera cam = g.mainCamera;
            g.player.SetActive(false);
            cam.transform.SetParent(null, true);
            cam.transform.position = new Vector3(-40f, 230f, -150f);
            cam.transform.rotation = Quaternion.LookRotation(new Vector3(30f, 0f, 70f) - cam.transform.position, Vector3.up);
            cam.nearClipPlane = 0.5f;
            yield return Shot("aerial");
            cam.transform.position = new Vector3(-10f, 45f, -95f);
            cam.transform.rotation = Quaternion.LookRotation(new Vector3(10f, 22f, 60f) - cam.transform.position, Vector3.up);
            yield return Shot("lowaerial");
            g.player.AttachCamera(cam.transform);
            g.player.SetActive(true);

            Transform[] views = g.tourPoints;
            if (views != null)
            {
                foreach (Transform v in views)
                {
                    if (v == null) continue;
                    g.player.Spawn(v.position, v.eulerAngles.y);
                    float pitch = v.eulerAngles.x;
                    if (pitch > 180f) pitch -= 360f;
                    g.player.Pitch = pitch;
                    yield return Shot(v.name);
                }
            }

            // walk forward a bit from the spawn
            g.player.Spawn(g.spawnPoint.position, g.spawnPoint.eulerAngles.y);
            g.player.Pitch = 0f;
            TouchControls.I.SimulatedMove = new Vector2(0f, 1f);
            yield return WaitFrames(12, 4f);
            TouchControls.I.SimulatedMove = Vector2.zero;
            yield return Shot("walked");

            // the same view on each graphics profile (not saved to the player's settings)
            GraphicsLevel original = GameSettings.Graphics;
            foreach (GraphicsLevel level in new[] { GraphicsLevel.Low, GraphicsLevel.Medium, GraphicsLevel.High })
            {
                GameSettings.Graphics = level;
                if (QualityManager.I != null) QualityManager.I.Apply();
                yield return Shot("profile_" + level);
            }
            GameSettings.Graphics = original;
            if (QualityManager.I != null) QualityManager.I.Apply();

            g.Pause();
            yield return Shot("pause");
            Debug.Log("[RF] TOUR done exc=" + exceptions);
        }
    }
}
