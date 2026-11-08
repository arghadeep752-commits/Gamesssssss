#if PROTO_AUTOTEST
using System.Collections;
using System.IO;
using UnityEngine;

namespace GridProto
{
    /// <summary>
    /// Only compiled into the emulator test build (never into the phone APK): walks through the level,
    /// opens the door and saves screenshots so the cloud build can check the game really works.
    /// </summary>
    public class AutoTest : MonoBehaviour
    {
        string folder;

        IEnumerator Start()
        {
            GameRoot root = GetComponent<GameRoot>();
            folder = Path.Combine(Application.persistentDataPath, "autotest");
            Directory.CreateDirectory(folder);
            Debug.Log("[PROTO-TEST] start " + Screen.width + "x" + Screen.height
                      + " gpu=" + SystemInfo.graphicsDeviceName + " api=" + SystemInfo.graphicsDeviceType
                      + " msaa=" + QualitySettings.antiAliasing + " dir=" + folder);

            yield return new WaitForSeconds(4f);
            yield return Shot("01-start");

            PlayerController p = root.player;
            p.Teleport(new Vector3(12f, 0.05f, -12f), -34f, 4f);
            yield return new WaitForSeconds(1.5f);
            yield return Shot("02-cubes");

            p.Teleport(new Vector3(-18f, 0.05f, -2f), 24f, 0f);
            yield return new WaitForSeconds(1.5f);
            yield return Shot("03-stairs-side");

            p.Teleport(new Vector3(0f, 0.05f, 6.7f), 0f, 3f);
            yield return new WaitForSeconds(1.5f);
            bool buttonShown = root.player.GetComponent<PlayerInteractor>().Current != null;
            Debug.Log("[PROTO-TEST] interact button near door: " + (buttonShown ? "SHOWN" : "MISSING"));
            yield return Shot("04-near-door");

            TouchState.InteractPressed = true;
            yield return new WaitForSeconds(2f);
            Debug.Log("[PROTO-TEST] door open after interact: " + (root.door != null && root.door.IsOpen));
            yield return Shot("05-door-open");

            p.Teleport(new Vector3(0.6f, 0.1f, 9.4f), 20f, -2f);
            yield return new WaitForSeconds(1.5f);
            yield return Shot("06-inside");

            p.Teleport(new Vector3(1.2f, 0.1f, 14.2f), 195f, 2f);
            yield return new WaitForSeconds(1.5f);
            yield return Shot("07-doorway-from-inside");

            root.hud.SetPaused(true);
            yield return new WaitForSecondsRealtime(1f);
            yield return Shot("08-pause-menu");
            root.hud.SetPaused(false);

            Debug.Log("[PROTO-TEST] DONE");
        }

        IEnumerator Shot(string name)
        {
            yield return new WaitForEndOfFrame();
            Texture2D tex = ScreenCapture.CaptureScreenshotAsTexture();
            if (tex == null)
            {
                Debug.Log("[PROTO-TEST] shot " + name + " failed");
                yield break;
            }
            byte[] png = tex.EncodeToPNG();
            Destroy(tex);
            File.WriteAllBytes(Path.Combine(folder, name + ".png"), png);
            Debug.Log("[PROTO-TEST] shot " + name + " " + png.Length + " bytes");
        }
    }
}
#endif
