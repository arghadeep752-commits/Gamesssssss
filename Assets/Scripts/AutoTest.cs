#if DG_AUTOTEST
using System.Collections;
using UnityEngine;

namespace Danga
{
    /// <summary>
    /// Only in the emulator check build (never in the phone APK): plays through the game - menu, settings, the
    /// house, walking, the phone and a cheat, shooting, the bike, a car, the palace, the map, the gun shop, the
    /// boat, the helicopter, night and the police - and writes "[DG-TEST] SNAP name" so the cloud test takes a
    /// screenshot at each moment.
    /// </summary>
    public class AutoTest : MonoBehaviour
    {
        static void Log(string s) { Debug.Log("[DG-TEST] " + s); }

        IEnumerator Snap(string name)
        {
            for (int i = 0; i < 3; i++) yield return null;
            ScreenCapture.CaptureScreenshot("shot_" + name + ".png");
            yield return null;
            yield return null;
            Log("SNAP " + name + " fps=" + Mathf.RoundToInt(1f / Mathf.Max(1e-3f, Time.smoothDeltaTime)) + " chunks=" + City.I.loadedChunks +
                " cars=" + Traffic.I.cars.Count + " peds=" + Traffic.I.peds.Count);
            yield return new WaitForSecondsRealtime(5f);
        }

        IEnumerator Wait(float t) { yield return new WaitForSecondsRealtime(t); }

        IEnumerator Start()
        {
            Game g = Game.I;
            QualitySettings.antiAliasing = 0;
            yield return Wait(3f);
            Log("files go to " + Application.persistentDataPath);
            Log("start " + Screen.width + "x" + Screen.height + " gpu=" + SystemInfo.graphicsDeviceName + " api=" + SystemInfo.graphicsDeviceType);
            yield return Snap("01-menu");
            Menus.I.Settings(Menus.I.MainMenu);
            yield return Wait(1f);
            yield return Snap("02-settings");
            Menus.I.MainMenu();
            yield return Wait(0.5f);
            g.Play(false);
            yield return Wait(4f);
            Player p = Player.I;
            Hud.scripted = true;
            Wanted.never = true;          // the check shoots in the street; the police part sets the stars itself
            yield return Snap("03-home");
            Hud.sMove = new Vector2(0f, 1f);
            yield return Wait(2.5f);
            Hud.sMove = Vector2.zero;
            yield return Snap("04-walk");
            Menus.I.Phone();
            yield return Wait(1f);
            yield return Snap("05-phone");
            Menus.I.Close();
            g.Cheat("4545");
            g.Cheat("1122");
            p.Equip(Wpn.Pistol);
            yield return Wait(0.5f);
            Hud.sFire = true;
            yield return Wait(1.2f);
            yield return Snap("06-shoot");
            Hud.sFire = false;
            p.Equip(Wpn.Fist);
            // the motorbike outside the house
            Vehicle bike = null;
            foreach (var v in Vehicle.all) if (v.owned) bike = v;
            Log("house bike: " + (bike != null ? bike.spec.name + " at " + bike.transform.position : "none"));
            if (bike != null)
            {
                p.EnterVehicle(bike);
                yield return Wait(1f);
                Hud.sGas = true;
                yield return Wait(1.6f);
                Log("bike speed " + Mathf.RoundToInt(bike.Speed * 3.6f) + " km/h, riding " + (p.vehicle == bike));
                yield return Snap("07-bike");
                Hud.sGas = false;
                yield return Wait(1.5f);
                p.ExitVehicle();
            }
            yield return Wait(1f);
            g.Cheat("8080");
            yield return Wait(1f);
            // the car the cheat just put on the street next to us (not some other sports car in town)
            Vehicle car = null;
            float cd = 40f * 40f;
            foreach (var v in Vehicle.all)
                if (v.spec.name == "sports_car" && v.driver == null && (v.transform.position - p.transform.position).sqrMagnitude < cd)
                { cd = (v.transform.position - p.transform.position).sqrMagnitude; car = v; }
            if (car != null)
            {
                Log("cheat car at " + car.transform.position + " yaw " + Mathf.RoundToInt(car.transform.eulerAngles.y));
                p.EnterVehicle(car);
            }
            Hud.sGas = true;
            yield return Wait(3f);
            Log("car: " + (p.vehicle != null ? p.vehicle.spec.name + " " + Mathf.RoundToInt(p.vehicle.Speed * 3.6f) + " km/h, grounded " + p.vehicle.Grounded : "not in a car"));
            yield return Snap("08-car");
            Hud.sGas = false;
            yield return Wait(1f);
            if (p.vehicle != null) p.ExitVehicle();
            var palace = City.I.points.Find(x => x.name.Contains("Ujjayanta"));
            if (palace != null)
            {
                g.TestTeleport(palace.p + new Vector3(0f, 0.3f, -60f), 0f);
                Cam.I.yaw = 0f;
                Cam.I.pitch = 8f;
                yield return Wait(4f);
                yield return Snap("09-palace");
            }
            Menus.I.BigMap();
            yield return Wait(1f);
            yield return Snap("10-map");
            Menus.I.Close();
            Menus.I.GunShop();
            yield return Wait(1f);
            yield return Snap("11-gunshop");
            Menus.I.Close();
            var jetty = City.I.Point("boat");
            if (jetty != null)
            {
                g.TestTeleport(jetty.p + Vector3.up * 1.2f, jetty.yaw);
                yield return Wait(3f);
                g.Cheat("5050");
                yield return Wait(1f);
                Vehicle boat = null;
                float bd = 1e9f;
                foreach (var v in Vehicle.all)
                    if (v.spec.IsBoat && (v.transform.position - p.transform.position).sqrMagnitude < bd) { bd = (v.transform.position - p.transform.position).sqrMagnitude; boat = v; }
                if (boat != null)
                {
                    p.EnterVehicle(boat);
                    Hud.sGas = true;
                    yield return Wait(4f);
                    yield return Snap("12-boat");
                    Hud.sGas = false;
                    p.ExitVehicle(true);
                }
            }
            var helipad = City.I.points.Find(x => x.kind == "helipad");
            Vector3 hp = helipad != null ? helipad.p : g.SpawnPoint();
            g.TestTeleport(hp + new Vector3(8f, 0.5f, 0f), 0f);
            yield return Wait(2f);
            g.Cheat("9090");
            yield return Wait(1f);
            foreach (var v in Vehicle.all) if (v.spec.IsHeli && v.driver == null && (v.transform.position - p.transform.position).sqrMagnitude < 900f) { p.EnterVehicle(v); break; }
            yield return Wait(3f);
            Hud.sUp = true;
            yield return Wait(5f);
            Hud.sUp = false;
            Hud.sMove = new Vector2(0f, 0.6f);
            yield return Wait(2f);
            yield return Snap("13-heli");
            Hud.sMove = Vector2.zero;
            if (p.vehicle != null) p.ExitVehicle(true);
            g.TestTeleport(g.SpawnPoint(), 0f);
            Env.hour = 21f;
            yield return Wait(3f);
            yield return Snap("14-night");
            Env.hour = 10f;
            Wanted.Set(3);
            yield return Wait(8f);
            yield return Snap("15-police");
            Wanted.Set(0);
            Hud.scripted = false;
            Log("DONE");
        }
    }
}
#endif
