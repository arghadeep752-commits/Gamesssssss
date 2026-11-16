#if MOULIKA_AUTOTEST
using System.Collections;
using UnityEngine;

namespace Moulika
{
    /// <summary>
    /// Only compiled into the emulator check build (never into the phone APK). Walks through the game the way the
    /// Godot build check did: menus, the school from many viewpoints, Moulika walking and striking, picking up the
    /// hammer, the joystick, a chase and being caught, and the pause menu. At each moment it writes
    /// "[MOULIKA-TEST] SNAP name" and holds the picture for three seconds so the cloud test can take a screenshot.
    /// </summary>
    public class AutoTest : MonoBehaviour
    {
        Game game;

        static void Log(string s) { Debug.Log("[MOULIKA-TEST] " + s); }

        IEnumerator Snap(string name)
        {
            float ts = Time.timeScale;
            Time.timeScale = 0f;
            // the emulator draws in software: make sure the new view has really been drawn before the screenshot
            for (int i = 0; i < 3; i++) yield return null;
            Log("SNAP " + name);
            yield return new WaitForSecondsRealtime(3.2f);
            Time.timeScale = ts;
        }

        static Vector3 G(float x, float y, float z) { return Game.G(x, y, z); }

        void View(Vector3 pos, Vector3 look)
        {
            Player p = game.player;
            p.Teleport(pos + new Vector3(0f, 0.05f, 0f));
            p.Face(look);
            p.pitch = Mathf.Atan2(look.y - 1.6f, new Vector2(look.x - pos.x, look.z - pos.z).magnitude) * Mathf.Rad2Deg;
            p.Apply();
        }

        IEnumerator Start()
        {
            game = GetComponent<Game>();
            QualitySettings.antiAliasing = 0;      // the emulator's software GPU is slow enough without it
            yield return new WaitForSecondsRealtime(2f);
            Log("start " + Screen.width + "x" + Screen.height + " gpu=" + SystemInfo.graphicsDeviceName + " api=" + SystemInfo.graphicsDeviceType
                + " msaa=" + QualitySettings.antiAliasing);
            yield return Snap("01-menu");
            game.TestShowSettings();
            yield return new WaitForSecondsRealtime(1f);
            yield return Snap("02-settings");
            game.TestShowModes();
            yield return new WaitForSecondsRealtime(1f);
            yield return Snap("03-modes");

            float t0 = Time.realtimeSinceStartup;
            bool ok = game.TestBuildWorld(1);
            Log("world built: " + ok + " in " + (Time.realtimeSinceStartup - t0).ToString("0.0") + " s");
            if (!ok) { Log("DONE"); yield break; }
            game.TestBeginDay();
            game.moulika.Freeze(true);
            game.moulika.transform.position = G(0f, 0f, -8f);
            Level lv = game.level;
            int bad = 0;
            foreach (object p in Json.A(lv.meta, "patrol"))
                if (lv.FindPath(G(0f, 0f, -8f), Json.GV(p)).Count == 0) bad++;
            Log("items " + lv.items.Count + ", doors " + lv.doors.Count + ", hides " + lv.hides.Count + ", planks " + lv.planks.Count
                + ", lamps " + lv.lamps.Count + ", patrol points unreachable " + bad + ", moves " + (game.moulika.anim != null ? game.moulika.anim.GetClipCount() : 0));
            yield return new WaitForSecondsRealtime(1.5f);

            object[][] views =
            {
                new object[] { "04-spawn", G(-10.5f, 0f, 2.6f), G(-14f, 1.3f, 2.6f) },
                new object[] { "05-class-back", G(-13.2f, 0f, 0.6f), G(-8f, 1.0f, 4.5f) },
                new object[] { "06-main-door", G(0f, 0f, 1.6f), G(0f, 1.3f, 6f) },
                new object[] { "07-veranda", G(-7.8f, 0f, -2.2f), G(8f, 1.3f, -2.2f) },
                new object[] { "08-courtyard", G(6.2f, 0f, -13.6f), G(-3f, 1.6f, -7f) },
                new object[] { "09-principal", G(-3.1f, 0f, 0.4f), G(-5.4f, 0.9f, 4.6f) },
                new object[] { "10-store", G(9.7f, 0f, -9.7f), G(13.2f, 0.5f, -9.3f) },
                new object[] { "11-hall", G(2f, 0f, -16f), G(-6f, 1.4f, -21f) },
                new object[] { "12-library", G(-9.6f, 0f, -11.5f), G(-14f, 1.3f, -11.5f) },
                new object[] { "13-kitchen", G(6.2f, 0f, -16f), G(12.5f, 1.0f, -21f) },
                new object[] { "14-staff", G(3.1f, 0f, 0.4f), G(5.5f, 0.9f, 4f) },
            };
            foreach (object[] v in views)
            {
                View((Vector3)v[1], (Vector3)v[2]);
                yield return new WaitForSecondsRealtime(0.6f);
                if ((string)v[0] == "07-veranda")
                {
                    int frames = 0;
                    float a = Time.realtimeSinceStartup;
                    while (Time.realtimeSinceStartup - a < 2f) { frames++; yield return null; }
                    Log("emulator frame rate in the veranda: " + (frames / 2f).ToString("0.0") + " fps (software GPU)");
                }
                yield return Snap((string)v[0]);
            }

            // Moulika in the veranda, walking towards you, then striking
            Enemy m = game.moulika;
            View(G(-2.5f, 0f, -2.2f), G(3f, 1.6f, -2.2f));
            m.transform.position = G(1.0f, 0f, -2.2f);
            m.Yaw = -90f;
            m.Play("walk", 0f);
            yield return new WaitForSecondsRealtime(0.8f);
            yield return Snap("15-moulika");
            m.transform.position = G(-1.3f, 0f, -2.2f);
            m.Play("attack", 0f);
            yield return new WaitForSecondsRealtime(0.45f);
            yield return Snap("16-moulika-close");
            m.transform.position = G(0f, 0f, -8f);
            m.Play("idle", 0f);

            // an item, its highlight circle and prompt, then the hammer in hand at the planked main door
            Level.Item it = lv.items["hammer"];
            Vector3 ip = it.node.position;
            game.player.Teleport(new Vector3(ip.x - 1.2f, 0.05f, ip.z - 0.3f));
            game.player.Face(ip);
            game.player.pitch = Mathf.Atan2(ip.y - 1.6f, 1.25f) * Mathf.Rad2Deg;
            game.player.Apply();
            yield return new WaitForSecondsRealtime(0.8f);
            Log("looking at: '" + game.hud.labelText + "', can interact " + game.hud.canInteract);
            yield return Snap("17-item-prompt");
            game.Interact();
            Log("holding: " + game.held);
            game.player.Teleport(G(0f, 0.05f, 3.9f));
            game.player.Face(G(0f, 1.6f, 6f));
            game.player.pitch = -6f;
            game.player.Apply();
            yield return new WaitForSecondsRealtime(0.8f);
            yield return Snap("18-planks-hammer");

            // the joystick, pushed forward the way a thumb would
            Vector3 p0 = game.player.transform.position;
            game.player.Face(game.player.transform.position + G(0f, 0f, -5f));
            Vector2 jc = game.hud.TestJoyCenter();
            game.hud.TestJoy(true, jc);
            game.hud.TestJoy(true, jc + new Vector2(0f, -80f));
            yield return new WaitForSeconds(1.2f);
            game.hud.TestJoy(false, jc);
            Log("joystick moved the player " + Vector3.Distance(p0, game.player.transform.position).ToString("0.00") + " m");

            // a chase in the veranda: she sees you and runs at you
            game.Drop(true);
            View(G(-6f, 0f, -2.2f), G(3f, 1.6f, -2.2f));
            m.transform.position = G(3f, 0f, -2.2f);
            m.Yaw = -90f;
            m.Freeze(false);
            float w = 0f;
            while (m.state != Enemy.State.Chase && w < 4f) { w += Time.deltaTime; yield return null; }
            Log("Moulika state after seeing the player: " + m.state);
            yield return new WaitForSeconds(0.7f);
            yield return Snap("19-chase");
            w = 0f;
            while (game.state != Game.S.Cut && w < 8f) { w += Time.deltaTime; yield return null; }
            Log("caught: " + (game.state == Game.S.Cut));
            yield return new WaitForSeconds(0.65f);
            yield return Snap("20-caught");
            w = 0f;
            while (game.state != Game.S.Play && w < 12f) { w += Time.deltaTime; yield return null; }
            Log("after being caught: day " + game.day + ", state " + game.state);
            yield return new WaitForSecondsRealtime(0.5f);
            yield return Snap("21-day2");
            game.Pause();
            yield return new WaitForSecondsRealtime(0.8f);
            Log("paused: " + (game.state == Game.S.Pause));
            Log("SNAP 22-pause");
            yield return new WaitForSecondsRealtime(3.2f);
            game.Resume();
            Log("DONE");
        }
    }
}
#endif
