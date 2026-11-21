#if TM_AUTOTEST
using System.Collections;
using UnityEngine;

namespace TradersMadness
{
    /// <summary>
    /// Only compiled into the emulator check build (never into the phone APK). Walks through the game: menus, the
    /// intro, the house room by room (both floors), the trading room before and after the power comes back, the
    /// PC screen, the door keypad, the trader up close, being caught, and the pause menu. At each moment it writes
    /// "[TM-TEST] SNAP name" and holds the picture so the cloud test can take a screenshot.
    /// </summary>
    public class AutoTest : MonoBehaviour
    {
        Game game;

        static void Log(string s) { Debug.Log("[TM-TEST] " + s); }

        IEnumerator Snap(string name, bool freeze = true)
        {
            float ts = Time.timeScale;
            if (freeze) Time.timeScale = 0f;
            for (int i = 0; i < 3; i++) yield return null;
            ScreenCapture.CaptureScreenshot("shot_" + name + ".png");
            yield return null;
            yield return null;
            Log("SNAP " + name);
            yield return new WaitForSecondsRealtime(4f);
            Time.timeScale = ts;
        }

        void View(Vector3 pos, Vector3 look)
        {
            Player p = game.player;
            p.Teleport(pos + new Vector3(0f, 0.05f, 0f));
            p.Face(look);
            p.pitch = Mathf.Atan2(look.y - (pos.y + 1.6f), new Vector2(look.x - pos.x, look.z - pos.z).magnitude) * Mathf.Rad2Deg;
            p.Apply();
        }

        IEnumerator Start()
        {
            game = GetComponent<Game>();
            QualitySettings.antiAliasing = 0;
            yield return new WaitForSecondsRealtime(2f);
            Log("files go to " + Application.persistentDataPath);
            Log("start " + Screen.width + "x" + Screen.height + " gpu=" + SystemInfo.graphicsDeviceName + " api=" + SystemInfo.graphicsDeviceType);
            yield return Snap("01-menu", false);
            game.TestShowSettings();
            yield return new WaitForSecondsRealtime(1f);
            yield return Snap("02-settings", false);
            game.TestShowModes();
            yield return new WaitForSecondsRealtime(1f);
            yield return Snap("03-risk", false);
            game.StartGame(1);
            float t = 0f;
            while (game.state != Game.S.Cut && t < 60f) { t += Time.unscaledDeltaTime; yield return null; }
            yield return new WaitForSecondsRealtime(2.5f);
            yield return Snap("04-intro-outside", false);
            game.TestBeginDay();
            t = 0f;
            while (game.state != Game.S.Play && t < 30f) { t += Time.unscaledDeltaTime; yield return null; }
            yield return new WaitForSecondsRealtime(3f);
            Log("playing: day " + game.day);
            if (game.trader != null) game.trader.Freeze(true);
            yield return Snap("05-wake-up-guest-room");
            // a tour of the house
            View(new Vector3(8.4f, 0f, 0.9f), new Vector3(15.5f, 0.9f, 5.0f));
            yield return Snap("06-living-room");
            View(new Vector3(9.8f, 0f, 6.9f), new Vector3(15.2f, 1.0f, 11.0f));
            yield return Snap("07-kitchen");
            View(new Vector3(8.3f, 0f, 1.2f), new Vector3(5.8f, 2.2f, 9.0f));
            yield return Snap("08-hall-stair");
            View(new Vector3(7.4f, 0f, 3.2f), new Vector3(7.0f, 1.2f, 0f));
            yield return Snap("09-main-door");
            View(new Vector3(4.4f, 0f, 0.8f), new Vector3(0.6f, 0.9f, 6.5f));
            yield return Snap("10-garage");
            View(new Vector3(7.6f, 3.3f, 1.4f), new Vector3(6.0f, 3.6f, 11.0f));
            yield return Snap("11-upstairs-hall");
            View(new Vector3(9.9f, 3.3f, 0.8f), new Vector3(13.5f, 4.2f, 6.0f));
            yield return Snap("12-trading-room-no-power");
            game.TestPower();
            yield return new WaitForSecondsRealtime(1.5f);
            yield return Snap("13-trading-room-power-on", false);
            View(new Vector3(10.0f, 3.3f, 7.0f), new Vector3(14.5f, 3.9f, 11.5f));
            yield return Snap("14-master-bedroom");
            View(new Vector3(13.5f, 3.3f, 4.2f), new Vector3(13.5f, 4.4f, 6.2f));
            game.TestOpenTerminal();
            yield return new WaitForSecondsRealtime(1.5f);
            yield return Snap("15-trading-pc", false);
            game.CloseOverlay();
            View(new Vector3(7.6f, 0f, 1.2f), new Vector3(7.9f, 1.35f, 0.1f));
            game.TestOpenKeypad();
            yield return new WaitForSecondsRealtime(1f);
            yield return Snap("16-door-keypad", false);
            game.CloseOverlay();
            // the trader, close up
            if (game.trader != null)
            {
                Vector3 tp = game.trader.transform.position;
                Vector3 fwd = game.trader.transform.forward;
                View(tp + fwd * 2.4f - new Vector3(0f, tp.y > 1.9f ? 0f : 0f, 0f), tp + new Vector3(0f, 1.5f, 0f));
                yield return Snap("17-trader");
                game.trader.Play("walk");
                yield return new WaitForSecondsRealtime(0.6f);
                yield return Snap("18-trader-walking");
                // let him catch us
                game.trader.Freeze(false);
                game.trader.transform.position = game.player.transform.position + game.player.transform.forward * 1.0f;
                game.trader.Hear(game.player.transform.position, 30f);
                t = 0f;
                while (game.state == Game.S.Play && t < 20f) { t += Time.unscaledDeltaTime; yield return null; }
                yield return new WaitForSecondsRealtime(0.5f);
                yield return Snap("19-caught", false);
                t = 0f;
                while (game.state != Game.S.Play && t < 20f) { t += Time.unscaledDeltaTime; yield return null; }
                yield return new WaitForSecondsRealtime(2f);
                yield return Snap("20-day-2", false);
            }
            game.Pause();
            yield return new WaitForSecondsRealtime(1f);
            yield return Snap("21-pause", false);
            game.Resume();
            Log("DONE");
        }
    }
}
#endif
