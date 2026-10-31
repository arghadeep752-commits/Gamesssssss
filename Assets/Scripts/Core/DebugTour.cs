using System.Collections;
using UnityEngine;

namespace RealFPS
{
    /// <summary>
    /// Automated screenshot tour for the cloud emulator test. Only runs when the
    /// app is started with the intent extra "rf_tour" (adb shell am start ... -e rf_tour 1).
    /// It plays the game, visits a list of viewpoints and logs "[RF] TOUR shot n name"
    /// when each view is ready to be captured.
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

        IEnumerator WaitFrames(int frames, float seconds)
        {
            float t0 = Time.realtimeSinceStartup;
            int f0 = Time.frameCount;
            while (Time.frameCount - f0 < frames || Time.realtimeSinceStartup - t0 < seconds) yield return null;
        }

        IEnumerator Shot(string name)
        {
            yield return WaitFrames(6, 2.5f);
            float fps = 0f;
            float t0 = Time.realtimeSinceStartup;
            int f0 = Time.frameCount;
            yield return WaitFrames(4, 1.0f);
            fps = (Time.frameCount - f0) / Mathf.Max(0.001f, Time.realtimeSinceStartup - t0);
            shot++;
            Debug.Log("[RF] TOUR shot " + shot + " " + name + " fps=" + fps.ToString("0.0"));
            yield return new WaitForSecondsRealtime(4.5f);  // time for the screenshot
        }

        IEnumerator Start()
        {
            Debug.Log("[RF] TOUR start");
            yield return WaitFrames(20, 8f);
            yield return Shot("menu");
            Game g = Game.I;
            g.StartGame();
            yield return WaitFrames(10, 4f);
            yield return Shot("spawn");

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
            // walk forward a bit from the spawn and look around
            g.player.Spawn(g.spawnPoint.position, g.spawnPoint.eulerAngles.y);
            TouchControls.I.SimulatedMove = new Vector2(0f, 1f);
            yield return WaitFrames(30, 6f);
            TouchControls.I.SimulatedMove = Vector2.zero;
            yield return Shot("walked");
            g.Pause();
            yield return Shot("pause");
            Debug.Log("[RF] TOUR done");
        }
    }
}
