using System.Collections;
using UnityEngine;

namespace NightClass
{
    /// <summary>
    /// Automated screenshot tour for the cloud emulator test (started with the intent extra nc_tour).
    /// Logs "[RF] TOUR shot n name" whenever the view is ready; the CI script takes the screenshot.
    /// </summary>
    public class DebugTour : MonoBehaviour
    {
        static bool checkedIntent;
        int shot;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (checkedIntent) return;
            checkedIntent = true;
            if (!Requested()) return;
            var go = new GameObject("DebugTour");
            DontDestroyOnLoad(go);
            go.AddComponent<DebugTour>();
            Debug.Log("[RF] TOUR start");
        }

        static bool Requested()
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            try
            {
                using (var up = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
                using (var act = up.GetStatic<AndroidJavaObject>("currentActivity"))
                using (var intent = act.Call<AndroidJavaObject>("getIntent"))
                    return intent.Call<bool>("hasExtra", "nc_tour");
            }
            catch (System.Exception e)
            {
                Debug.Log("[RF] tour intent check failed: " + e.Message);
                return false;
            }
#else
            return false;
#endif
        }

        void Shot(string name)
        {
            shot++;
            Debug.Log("[RF] TOUR shot " + shot + " " + name + " fps=" + (1f / Mathf.Max(0.0001f, Time.smoothDeltaTime)).ToString("0"));
            try { Capture(shot.ToString("00") + "-" + name); }
            catch (System.Exception e) { Debug.Log("[RF] capture failed: " + e.Message); }
        }

        /// <summary>
        /// Renders the main camera into an offscreen sRGB texture and saves it as PNG. The emulator's
        /// software GPU washes out the on-screen image; this copy shows what a real phone renders.
        /// </summary>
        void Capture(string file)
        {
            Camera cam = Camera.main;
            if (cam == null) return;
            int w = 960;
            int h = Mathf.RoundToInt(w * (float)Screen.height / Mathf.Max(1, Screen.width));
            RenderTexture rt = RenderTexture.GetTemporary(w, h, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            RenderTexture prevTarget = cam.targetTexture;
            cam.targetTexture = rt;
            cam.Render();
            cam.targetTexture = prevTarget;
            RenderTexture prevActive = RenderTexture.active;
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            RenderTexture.active = prevActive;
            RenderTexture.ReleaseTemporary(rt);
            // Android blocks reading the app's files from adb, so the JPEG travels through the log
            string b64 = System.Convert.ToBase64String(tex.EncodeToJPG(80));
            Destroy(tex);
            const int chunk = 3000;
            int n = (b64.Length + chunk - 1) / chunk;
            StackTraceLogType prev = Application.GetStackTraceLogType(LogType.Log);
            Application.SetStackTraceLogType(LogType.Log, StackTraceLogType.None);
            for (int i = 0; i < n; i++)
                Debug.Log("NCIMG " + file + " " + i + "/" + n + " " + b64.Substring(i * chunk, Mathf.Min(chunk, b64.Length - i * chunk)));
            Application.SetStackTraceLogType(LogType.Log, prev);
        }

        IEnumerator Start()
        {
            GameSettings.Load();
            yield return new WaitForSecondsRealtime(6f);
            while (NCGame.I == null || NCGame.I.State != GameState.Menu) yield return new WaitForSecondsRealtime(0.5f);
            yield return new WaitForSecondsRealtime(4f);
            Shot("menu");
            yield return new WaitForSecondsRealtime(4f);
            NCGame.I.StartGame(Difficulty.Normal);
            yield return new WaitForSecondsRealtime(2f);
            while (NCGame.I == null || NCGame.I.State != GameState.Intro) yield return new WaitForSecondsRealtime(0.25f);
            yield return new WaitForSecondsRealtime(4f);
            Shot("intro");
            yield return new WaitForSecondsRealtime(3f);
            NCGame.I.SkipIntro();
            while (NCGame.I.State != GameState.Playing) yield return new WaitForSecondsRealtime(0.25f);
            yield return new WaitForSecondsRealtime(5f);
            Shot("start_classroom");
            yield return new WaitForSecondsRealtime(4f);

            string[] spots = { "corridor", "lounge", "toilets", "fire", "entrance", "gym", "cafeteria", "janitor", "garage", "office", "basement", "boiler" };
            foreach (string s in spots)
            {
                GameObject p = GameObject.Find("Tour_" + s);
                if (p == null) continue;
                if (s == "basement") GiveTorch();
                Place(p.transform);
                yield return new WaitForSecondsRealtime(3f);
                Shot(s);
                yield return new WaitForSecondsRealtime(4f);
            }

            // look at the teacher
            TeacherAI t = TeacherAI.I;
            if (t != null)
            {
                t.Freeze();
                Vector3 fwd = t.transform.forward;
                Vector3 pos = t.transform.position + fwd * 3.2f;
                FPController.I.Spawn(pos, Quaternion.LookRotation(-fwd).eulerAngles.y);
                yield return new WaitForSecondsRealtime(3f);
                Shot("teacher");
                yield return new WaitForSecondsRealtime(3f);
                FPController.I.Spawn(t.transform.position + fwd * 1.5f, Quaternion.LookRotation(-fwd).eulerAngles.y);
                if (TouchControls.I != null) TouchControls.I.AddLook(new Vector2(0f, 8f));
                yield return new WaitForSecondsRealtime(3f);
                Shot("teacher_close");
                yield return new WaitForSecondsRealtime(3f);
                NCGame.I.OnCaught();
                yield return new WaitForSecondsRealtime(0.7f);
                Shot("jumpscare");
                yield return new WaitForSecondsRealtime(3.5f);
                Shot("lesson_card");
                yield return new WaitForSecondsRealtime(5f);
                Shot("after_catch");
                yield return new WaitForSecondsRealtime(4f);
            }
            NCGame.I.Pause();
            yield return new WaitForSecondsRealtime(2f);
            Shot("pause");
            yield return new WaitForSecondsRealtime(4f);
            Debug.Log("[RF] TOUR done");
        }

        void Place(Transform p)
        {
            FPController.I.Spawn(p.position, p.eulerAngles.y);
            if (TouchControls.I != null) TouchControls.I.AddLook(new Vector2(0f, -Mathf.DeltaAngle(0f, p.eulerAngles.x)));
        }

        void GiveTorch()
        {
            Inventory inv = Inventory.I;
            if (inv == null || inv.Held != ItemType.None || inv.templates[(int)ItemType.Torch] == null) return;
            GameObject go = Instantiate(inv.templates[(int)ItemType.Torch].gameObject);
            go.SetActive(true);
            PickupItem pi = go.GetComponent<PickupItem>();
            pi.isTemplate = false;
            inv.Take(pi);
            go.SetActive(false);
        }
    }
}
